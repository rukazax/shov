#!/usr/bin/env python3
"""TeraTTSv2 как движок озвучки «Шова»: четыре родных русских тембра на CPU.

Зачем: у edge-tts родных русских голосов два (Dmitry, Svetlana), и двадцать
ролей различались только темпом и тоном — диаризация показала 23 роли в пяти
кластерах. TeraTTSv2 даёт четыре тембра (108, 134, 210, 265 Гц), автоударения
(RUAccent), 44,1 кГц, RTF 0,3 на этом хосте и коммерческую лицензию
(OpenRAIL-M + атрибуция). Проверка WER по 9 фразам — 1,8 %.

Сдвиг по полутонам расширяет четыре тембра до восьми различимых: ±2,5
полутона — предел, за которым голос становится «мультяшным».

    from teratts_engine import synth
    synth("Сгодится.", role="hero", rate=1, pitch=2, emotion="calm", out="x.wav")

Ударения: словарь stress.txt (по строке «слово<TAB>сл+ово») перекрывает
автоударение модели — она ошибается на именах («Сен+я», «Гущ+ин»).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.environ.get("TERATTS_MODEL", "/srv/apps/models/terattsv2")
CACHE = os.path.join(HERE, "cache", "teratts")
STRESS_FILE = os.path.join(HERE, "stress.txt")
SR = 44100

# role -> (тембр TeraTTS, сдвиг в полутонах). Мужские: ru_m5 — низкий и
# ровный (рассказчик, тяжёлые мужики), ru_m1 — светлее и моложе (Витя,
# Костя, техник). Женские: ru_f2 — взрослая (бабка, Пожарская, Ганна),
# ru_f1 — молодая (Даша, Лида, Нина).
ROLES = {
    # рассказчик и герой — один человек, разница в манере: герой чуть выше
    "narrator": ("ru_m5", -1.0), "hero": ("ru_m5", 0.0),
    # тяжёлые мужские
    "bocman": ("ru_m5", -2.0), "mihalych": ("ru_m5", -1.5),
    "vetrov": ("ru_m5", -2.5), "veretennikov": ("ru_m5", -2.5),
    "skolkov": ("ru_m5", -2.0), "kabanov": ("ru_m5", -1.0),
    "gushchin": ("ru_m5", -1.5), "kerzhak": ("ru_m5", -1.5),
    "somov": ("ru_m5", +0.5), "dorohov": ("ru_m5", +0.5),
    # светлые мужские
    "vitya": ("ru_m1", +1.0), "kostya": ("ru_m1", +1.5),
    "tehnik": ("ru_m1", +2.0), "leytenant": ("ru_m1", +0.5),
    "grisha": ("ru_m1", 0.0), "muhin": ("ru_m1", -0.5),
    "tarasov": ("ru_m1", +1.5), "dyakov": ("ru_m1", 0.0),
    "pankratov": ("ru_m1", -1.5), "semyon2": ("ru_m5", -0.5),
    # взрослые женские
    "babka": ("ru_f2", -2.0), "agrafena": ("ru_f2", -2.5),
    "ganna": ("ru_f2", -1.0), "pozharskaya": ("ru_f2", 0.0),
    "female": ("ru_f2", +0.5), "kovaleva": ("ru_f2", +1.0),
    "tkachuk": ("ru_f2", -0.5), "kac": ("ru_f2", +0.0),
    "teacher": ("ru_f2", +1.0),
    # молодые женские
    "dasha": ("ru_f1", 0.0), "lida": ("ru_f1", -1.0), "nina": ("ru_f1", +1.5),
    "system": ("ru_m5", -5.0),
}
# медиана основного тона тембра по замеру (probe, 2026-11-23): нужна, чтобы
# переводить «+6 Гц» старой просодии в полутоны, а не в попугайский сдвиг
BASE_F0 = {"ru_m5": 109.0, "ru_m1": 139.0, "ru_f2": 210.0, "ru_f1": 265.0}

# Состояния реплики. duration_scale: >1 — медленнее, <1 — быстрее (так его
# понимает TeraTTS). Полутоны и дБ поверх. Значения подобраны так, чтобы
# разница была слышна: крик +7 дБ и −8 % длительности, шёпот −8 дБ,
# усталость +10 % длительности и ниже на полтора полутона.
EMOTIONS = {
    "calm":    (1.00, 0.0, 0.0, None),
    "tense":   (0.97, 0.6, 1.0, None),
    "angry":   (0.94, 1.5, 2.0, "shout"),
    "joy":     (0.96, 1.2, 1.5, None),
    "tired":   (1.10, -1.2, -1.5, None),
    "sad":     (1.13, -1.5, -1.0, None),
    "whisper": (1.06, 0.3, -6.0, "whisper"),
    "shout":   (0.92, 1.8, 4.0, "shout"),
}

# Темп чтения. При PACE=1 TeraTTS читает на пятую часть быстрее вышедших
# томов: введение тома 1 — 8,9 мин против 11,1 у edge-tts. 1,2 выравнивает
# темп с книгой (замер: введение тома 1 — 10,7 мин против 11,1 у старой).
# Дальше 1,3 растягивать не надо: модель начинает глотать слова (ASR терял
# целые фразы). Точная цифра — на слух владельца против тома 1.
PACE = float(os.environ.get("TERATTS_PACE", "1.2"))

_loaded = None
_stress = None


def load_stress():
    """Словарь ударений: «Сеня	С+еня». Файла нет — словарь пустой."""
    global _stress
    if _stress is not None:
        return _stress
    _stress = {}
    try:
        with open(STRESS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.split("#")[0].strip()
                if not line or "\t" not in line:
                    continue
                word, marked = line.split("\t")[:2]
                _stress[word.strip().lower()] = marked.strip()
    except FileNotFoundError:
        pass
    return _stress


def mark_stress(text):
    """Подставить явные ударения. Модель сохраняет «+» и не трогает их."""
    table = load_stress()
    if not table:
        return text
    def repl(m):
        w = m.group(0)
        marked = table.get(w.lower())
        if not marked:
            return w
        if w[:1].isupper():
            return marked[:1].upper() + marked[1:]
        return marked
    return re.sub(r"[А-Яа-яЁё]+", repl, text)


def _model():
    global _loaded
    if _loaded is None:
        t0 = time.time()
        from transformers import AutoModel
        _loaded = AutoModel.from_pretrained(
            RELEASE, trust_remote_code=True, provider="CPUExecutionProvider",
            threads=int(os.environ.get("TERATTS_THREADS", "4")))
        print(f"  teratts: модель за {time.time() - t0:.1f} с", file=sys.stderr)
    return _loaded


def _shift(src, dst, semitones):
    """Сдвиг тембра без смены длительности: ресемплинг + обратный atempo."""
    k = 2.0 ** (semitones / 12.0)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-af", f"asetrate={SR}*{k:.6f},aresample={SR},atempo={1 / k:.6f}",
                    "-ar", str(SR), "-ac", "1", dst], check=True)


def _post(path, fx, gains):
    """Пост-эффект состояния. Крик — мягкая сатурация, шёпот — ближе и глуше."""
    x = np.frombuffer(subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", path, "-f", "f32le", "-ac", "1",
         "-ar", str(SR), "-"], capture_output=True).stdout, dtype=np.float32)
    if fx == "shout":
        x = np.tanh(x * 1.35).astype(np.float32)
    elif fx == "whisper":
        x = x - _movavg(x, int(SR / 180))       # срез низа
        x = _movavg(x, 3).astype(np.float32)     # шёпот без «шипящей» резкости
    x = x * np.float32(10.0 ** (gains / 20.0))
    peak = float(np.max(np.abs(x))) or 1.0
    if peak > 0.98:
        x *= 0.98 / peak
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR),
                    "-ac", "1", "-i", "-", path], input=x.astype("<f4").tobytes(),
                   check=True)


def _movavg(x, w):
    if w < 1 or len(x) < w:
        return x
    c = np.cumsum(np.insert(x, 0, 0))
    y = (c[w:] - c[:-w]) / w
    pad = len(x) - len(y)
    return np.concatenate([y, np.repeat(y[-1], pad)]).astype(np.float32)


def plan(role, rate=0, pitch=0, emotion=None, kind="dialogue"):
    """Просодия старой схемы (rate %, pitch Гц) → параметры TeraTTS."""
    voice, st = ROLES.get(role, ROLES["narrator"])
    emo = EMOTIONS.get(emotion or "calm", EMOTIONS["calm"])
    ds, est, egain, fx = emo
    f0 = BASE_F0[voice]
    st += est + 12.0 * np.log2(max(f0 + pitch, 40.0) / f0)
    tempo = ds * PACE / (1.0 + rate / 100.0)
    gain = egain + (1.0 if kind == "dialogue" else 0.0)
    return {"voice": voice, "st": round(float(st), 2), "tempo": round(float(tempo), 3),
            "gain": round(float(gain), 1), "fx": fx}


def synth(text, role, rate=0, pitch=0, emotion=None, kind="dialogue", out=None,
          force=False):
    """Синтезировать блок. Кэш по тексту и всем параметрам, как в render.py."""
    p = plan(role, rate, pitch, emotion, kind)
    clean = re.sub(r"\s+", " ", text.replace("«", "").replace("»", "")
                   .replace("…", "...")).strip()
    body = mark_stress(clean)
    key = hashlib.sha1(f"{p['voice']}|{p['st']}|{p['tempo']}|{p['gain']}|"
                       f"{p['fx']}|{body}".encode()).hexdigest()[:20]
    os.makedirs(CACHE, exist_ok=True)
    path = out or os.path.join(CACHE, key + ".wav")
    if os.path.exists(path) and os.path.getsize(path) > 2000 and not force:
        return path
    tts = _model()
    w = tts.generate_speech(f"<ru>{body}</ru>", voice=p["voice"],
                            duration_scale=p["tempo"])
    raw = path + ".raw.wav"
    tts.save_wav(raw, w)
    if abs(p["st"]) >= 0.3:
        _shift(raw, path, p["st"])
        os.remove(raw)
    else:
        os.replace(raw, path)
    _post(path, p["fx"], p["gain"])
    return path


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                          "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


if __name__ == "__main__":
    # проверка на месте: четыре тембра, по одной фразе
    for role in ("hero", "vitya", "babka", "dasha"):
        t0 = time.time()
        p = synth("Проверка голоса. Сейчас будет короткая фраза.", role, out=None,
                  force="--force" in sys.argv)
        d = duration(p)
        print(f"{role:8s} {ROLES[role][0]} {plan(role)['st']:+.1f} пт "
              f"{d:.2f} с  синтез {time.time() - t0:.1f} с  {p}")
