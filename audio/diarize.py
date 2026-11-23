#!/usr/bin/env python3
"""Диаризация дорожки: кто и когда говорит. sherpa-onnx, CPU.

Модели: pyannote segmentation-3.0 (режет речь на реплики) + 3D-Speaker CAM++
(считает эмбеддинг говорящего), кластеризация быстрая, порог 0.5, число
говорящих заранее не задаётся. Язык эмбеддингам почти безразличен.

Зачем в конвейере: проверить каст. В книге 17 ролей, а родных русских голосов
у edge-tts два (Dmitry, Svetlana); остальные роли различаются сдвигом темпа и
тона. Диаризация показывает, сколько РАЗНЫХ голосов слышит независимый
слушатель. Два применения:

  * дорожка главы — сколько голосов на самом деле слышно и где они меняются;
  * каталог пробных реплик (cache/probe, по файлу на роль) — сколько ролей
    каста реально различимы. Это честный ответ на «у каждого свой голос»:
    если 23 роли сели на 7 кластеров, значит 16 ролей звучат одинаково.

Интерпретатор: /srv/apps/toolchains/venv-asr/bin/python (sherpa_onnx, numpy)

Примеры:
    python diarize.py out/ch01.mp3 --cast cast/ch01.cast.txt -o diar-ch01.json
    python diarize.py --probe cache/probe
    python diarize.py ../audio/s1.mp3 --start 30 --duration 120
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np

SR = 16000
SEG = os.environ.get(
    "DIAR_SEG", "/srv/apps/models/sherpa-diar/sherpa-onnx-pyannote-segmentation-3-0/model.onnx")
EMB = os.environ.get(
    "DIAR_EMB", "/srv/apps/models/sherpa-diar/3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx")


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def decode(path, start=0.0, duration=None):
    """Любой файл → моно 16 кГц float32 в [-1, 1]."""
    if not shutil.which("ffmpeg"):
        sys.exit("нет ffmpeg")
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-ac", "1", "-ar", str(SR), wav]
    subprocess.run(cmd, check=True)
    with wave.open(wav) as w:
        n, rate = w.getnframes(), w.getframerate()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    os.unlink(wav)
    if rate != SR:
        sys.exit(f"ffmpeg отдал {rate} Гц вместо {SR}")
    return x


def parse_cast(path):
    """cast-файл → {роль: число реплик} (колонки: номер, тип, роль, текст)."""
    roles = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        kind, role = parts[1], parts[2]
        if kind == "dialogue":
            roles[role] = roles.get(role, 0) + 1
    return roles


def make_diarizer(threshold, num_speakers):
    import sherpa_onnx
    for p in (SEG, EMB):
        if not os.path.exists(p):
            sys.exit(f"нет модели: {p}\n  каталог models/sherpa-diar/ (см. README)")
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=SEG)),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=EMB, num_threads=4),
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=num_speakers, threshold=threshold),
        min_duration_on=0.3, min_duration_off=0.5)
    return sherpa_onnx.OfflineSpeakerDiarization(cfg)


def diarize(x, threshold, num_speakers):
    t0 = time.time()
    res = make_diarizer(threshold, num_speakers).process(x)
    segs = sorted(res.sort_by_start_time(), key=lambda s: s.start)
    return segs, res.num_speakers, time.time() - t0


def run_probe(dirpath, threshold, num_speakers, out):
    """Каталог пробных реплик (роль.mp3) → сколько ролей диаризация различает."""
    files = sorted(glob.glob(os.path.join(dirpath, "*.mp3"))
                   + glob.glob(os.path.join(dirpath, "*.wav")))
    if not files:
        sys.exit(f"в {dirpath} нет проб: нужны mp3 или wav с репликами ролей")
    parts, spans, t = [], [], 0.0
    gap = np.zeros(int(0.5 * SR), dtype=np.float32)
    for f in files:
        x = decode(f)
        role = os.path.splitext(os.path.basename(f))[0]
        spans.append((role, t, t + len(x) / SR))
        parts.extend([x, gap])
        t += len(x) / SR + 0.5
    x = np.concatenate(parts)
    segs, nsp, dt = diarize(x, threshold, num_speakers)
    print(f"проб {len(files)} · {t:.0f} с · кластеров {nsp} · диаризация {dt:.1f} с")

    mapping = []
    for role, s, e in spans:
        ov = {}
        for sg in segs:
            d = min(e, sg.end) - max(s, sg.start)
            if d > 0:
                ov[sg.speaker] = ov.get(sg.speaker, 0) + d
        best = max(ov, key=ov.get) if ov else -1
        mapping.append((role, best))
        print(f"  {role:12s} → spk{best}  (пересечение {ov.get(best, 0):.1f} с)")

    groups = {}
    for role, spk in mapping:
        groups.setdefault(spk, []).append(role)
    merged = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"\nитог: {len(mapping)} ролей → {len(groups)} кластеров; "
          f"слиты {sum(len(v) for v in merged.values())} ролей в {len(merged)} голос(ов)")
    for k, v in sorted(merged.items(), key=lambda kv: -len(kv[1])):
        print(f"  spk{k}: {', '.join(v)}")
    if out:
        json.dump({"probe_dir": os.path.abspath(dirpath), "num_clusters": nsp,
                   "mapping": [{"role": r, "speaker": s} for r, s in mapping]},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"→ {out}")


def run_track(args):
    x = decode(args.audio, args.start, args.duration)
    dur = len(x) / SR
    segs, nsp, dt = diarize(x, args.threshold, args.num_speakers)
    speech = {}
    for s in segs:
        speech[s.speaker] = speech.get(s.speaker, 0.0) + (s.end - s.start)
    print(f"{os.path.basename(args.audio)} · {mmss(dur)} · говорящих {nsp} · "
          f"сегментов {len(segs)} · диаризация {dt:.1f} с (×{dur / dt:.1f} к реальному)")
    if not args.quiet:
        for s in segs:
            print(f"  {mmss(s.start)}–{mmss(s.end)}  spk{s.speaker}  {s.end - s.start:5.2f} с")
    print("  по говорящим: " + ", ".join(
        f"spk{k} {v:.0f} с ({100 * v / dur:.0f} %)"
        for k, v in sorted(speech.items(), key=lambda kv: -kv[1])))

    if args.cast:
        roles = parse_cast(args.cast)
        print(f"  каст: ролей {len(roles)}, реплик {sum(roles.values())} — "
              + ", ".join(f"{r} {n}" for r, n in sorted(roles.items(), key=lambda kv: -kv[1])))
        print(f"  вердикт: диаризация слышит {nsp} голос(а) на {len(roles)} ролей")

    if args.out:
        doc = {
            "file": os.path.abspath(args.audio), "duration": round(dur, 2),
            "diarization_sec": round(dt, 2), "num_speakers": nsp,
            "segments": [{"start": round(s.start, 2), "end": round(s.end, 2),
                          "speaker": s.speaker} for s in segs],
            "speech_by_speaker": {str(k): round(v, 1) for k, v in speech.items()},
        }
        if args.cast:
            doc["cast"] = parse_cast(args.cast)
        json.dump(doc, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  → {args.out}")


def selftest():
    assert mmss(0) == "00:00.00" and mmss(75.5) == "01:15.50"
    import tempfile as tf
    p = tf.mktemp(suffix=".cast.txt")
    open(p, "w").write("# x\n1\tdialogue\thero\tПривет!\n2\tnarration\thero\tОн ушёл.\n"
                       "3\tdialogue\tbabka\tА?\n4\tdialogue\thero\tНу.\n")
    r = parse_cast(p)
    os.unlink(p)
    assert r == {"hero": 2, "babka": 1}, r
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", nargs="?", help="дорожка: mp3, wav, m4a, видео")
    ap.add_argument("--probe", metavar="DIR",
                    help="вместо дорожки: каталог пробных реплик (по файлу на роль)")
    ap.add_argument("-o", "--out", help="записать результат в JSON")
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="порог кластеризации: меньше — больше говорящих (0.5)")
    ap.add_argument("--num-speakers", type=int, default=-1,
                    help="задать число говорящих вместо кластеризации (-1 = авто)")
    ap.add_argument("--start", type=float, default=0.0, help="с какой секунды резать")
    ap.add_argument("--duration", type=float, help="сколько секунд брать")
    ap.add_argument("--cast", help="cast-файл главы: сравнить роли с кластерами")
    ap.add_argument("--quiet", action="store_true", help="не печатать сегменты")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    if args.probe:
        run_probe(args.probe, args.threshold, args.num_speakers, args.out)
        return
    if not args.audio:
        ap.error("нужен файл дорожки или --probe DIR")
    run_track(args)


if __name__ == "__main__":
    main()
