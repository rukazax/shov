#!/usr/bin/env python3
"""Приёмка фрагмента: разборчивость (WER), разница голосов (f0), интонации.

    /srv/apps/toolchains/venv-asr/bin/python verify_demo.py out-demo/blocks

Что проверяет:
  * WER по каждому блоку — GigaAM на CPU, сверка с текстом сценария;
  * медиана основного тона по роли — голоса должны расходиться, а не «сдвиг
    на пару герц»;
  * шесть состояний одной реплики — темп, высота и громкость должны двигаться
    согласованно (злость выше и громче, усталость медленнее и тише).
"""
import glob
import os
import re
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from demo_cast import SCRIPT  # noqa: E402

SR = 44100


def f0_of(a, sr):
    win, hop = int(sr * 0.04), int(sr * 0.02)
    lo, hi = int(sr / 400), int(sr / 60)
    vals = []
    for st in range(0, len(a) - win, hop):
        fr = a[st:st + win]
        if np.sqrt((fr ** 2).mean()) < 0.02:
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, "full")[win - 1:]
        if ac[0] <= 0 or ac[lo:hi].size == 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.3:
            vals.append(sr / lag)
    return float(np.median(vals)) if vals else 0.0


def read(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return a.astype(np.float32) / 32768.0, sr


def norm(s):
    s = re.sub(r"[^\w\s]", " ", s.lower().replace("ё", "е"))
    return s.split()


def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
    return d[len(hyp)]


def asr(rec, path):
    x, sr = read(path)
    st = rec.create_stream()
    st.accept_waveform(sr, x.tolist())
    rec.decode_stream(st)
    return st.result.text


def main():
    blocks = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out-demo", "blocks")
    files = sorted(glob.glob(os.path.join(blocks, "*.wav")))
    if not files:
        sys.exit(f"нет блоков в {blocks}")

    import sherpa_onnx
    rec = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
        model="/srv/apps/models/gigaam/model.int8.onnx",
        tokens="/srv/apps/models/gigaam/tokens.txt", num_threads=4)

    tot_err = tot_words = 0
    bad = []
    print("=== WER по блокам (GigaAM) ===")
    for i, path in enumerate(files):
        role, kind, emo, text = SCRIPT[i]
        hyp = asr(rec, path)
        r, h = norm(text), norm(hyp)
        e = wer(r, h)
        tot_err += e
        tot_words += len(r)
        if e and len(r) >= 3:
            bad.append((i, role, text, hyp, e, len(r)))
    print(f"итого WER = {tot_err}/{tot_words} = {tot_err / max(tot_words, 1):.3f}")
    for i, role, text, hyp, e, n in bad[:12]:
        print(f"  #{i:2d} {role:8s} ошибок {e}/{n}")
        print(f"     ждали: {text[:80]}")
        print(f"     услышали: {hyp[:80]}")

    print("\n=== голос: медиана основного тона по роли (спокойные блоки) ===")
    by_role = {}
    for i, path in enumerate(files):
        role, kind, emo, text = SCRIPT[i]
        if emo not in ("calm", "tense"):
            continue
        a, sr = read(path)
        by_role.setdefault(role, []).append(f0_of(a, sr))
    for role, vals in sorted(by_role.items(), key=lambda kv: -np.median(kv[1])):
        print(f"  {role:9s} {np.median(vals):6.1f} Гц   (блоков {len(vals)})")

    print("\n=== интонации: одна реплика, шесть состояний ===")
    base = None
    for i, path in enumerate(files):
        role, kind, emo, text = SCRIPT[i]
        if role != "babka" or not text.startswith("Он мяукает") or len(text) > 60:
            continue
        a, sr = read(path)
        rms = float(np.sqrt((a ** 2).mean()))
        dur = len(a) / sr
        if base is None:
            base = (dur, rms)
        print(f"  {emo:8s} {dur:5.2f} с  f0 {f0_of(a, sr):6.1f} Гц  "
              f"громкость {20 * np.log10(max(rms, 1e-9)):6.1f} dBFS  "
              f"темп ×{base[0] / dur:4.2f}")


if __name__ == "__main__":
    main()
