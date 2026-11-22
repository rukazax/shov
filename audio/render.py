#!/usr/bin/env python3
"""Аудиоверсия «Шова» в духе записей 1С-Паблишинг: явные голоса, подложка, эффекты.

Читает размеченный markdown главы, озвучивает по абзацам разными голосами,
кладет музыкальную подложку с дакингом, ставит звуковые эффекты на сценарные
разрывы и системные строки, нормализует громкость и пишет mp3.

python3 render.py BOOK01/ch01.md [-o out/ch01.mp3] [--only-text]
"""
import argparse
import asyncio
import hashlib
import os
import re
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BEDS = os.path.join(HERE, "beds")
CACHE = os.path.join(HERE, "cache")
OUTDIR = os.path.join(HERE, "out")
SR = 44100

# --- голоса ---------------------------------------------------------------

VOICES = {
    "hero":   {"voice": "ru-RU-DmitryNeural", "rate": "-4%", "pitch": "-2Hz"},
    "male2":  {"voice": "en-US-BrianMultilingualNeural", "rate": "+2%", "pitch": "-4Hz"},
    "male3":  {"voice": "en-AU-WilliamMultilingualNeural", "rate": "+4%", "pitch": "+2Hz"},
    "female": {"voice": "ru-RU-SvetlanaNeural", "rate": "+2%", "pitch": "+2Hz"},
    "system": {"voice": "ru-RU-DmitryNeural", "rate": "-12%", "pitch": "-8Hz"},
}

MALE_NAMES = ["техник", "Витя", "Кожин", "Боцман", "Михалыч", "Геннадий", "Мухин", "Аркадий"]
MALE2_NAMES = ["Семён-2", "лейтенант", "Семёна-2", "Семёну-2"]
FEMALE_NAMES = [
    "Даша", "Юля", "бабушка", "Нина Петровна", "Аграфена", "Аграфена Тихоновна",
    "Пожарская", "Ольга Тимуровна", "Лида", "Ганна", "Ткач", "мама", "мать",
    "вахтёрша", "старуха", "девчонка", "женщина",
]

SYSTEM_RE = re.compile(
    r"^(Согласование|Метка|Допуск|Ранг|Протечка|Сдвиг|Приказ|Пост|Край|Регистрация|Носитель|"
    r"Отметка|Сшивка|Узел|Проверка|Результат|Внимание)\s*[:.]",
)

ACTION_WORDS = ["бег", "погон", "стрел", "кров", "драл", "удар", "взрыв", "крич", "падал", "упал", "прорыв"]
TENSE_WORDS = ["стык", "допуск", "ведом", "приказ", "протечк", "согласован", "метк", "допрос", "нарушен"]
SEAM_WORDS = ["шов", "край", "геометри", "плёнк", "стена дышит", "полоса"]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def wav_read(path):
    with wave.open(path, "rb") as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        x = np.interp(np.linspace(0, len(x), int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    return x


def decode_any(path):
    """mp3/wav -> float32 mono 44.1k через ffmpeg."""
    p = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-f", "s16le", "-acodec", "pcm_s16le",
                        "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    return np.frombuffer(p.stdout, dtype="<i2").astype(np.float32) / 32768.0


def sess(name):
    p = os.path.join(BEDS, name)
    return wav_read(p) if os.path.exists(p) else np.zeros(1, dtype=np.float32)


def movavg(x, w):
    """Скользящее среднее за O(n): cumsum вместо convolve с длинным окном."""
    w = max(1, int(w))
    c = np.cumsum(np.concatenate(([0.0], x.astype(np.float64))))
    out = (c[w:] - c[:-w]) / w
    pad = np.full(len(x) - len(out), out[-1] if len(out) else 0.0)
    return np.concatenate((out, pad)).astype(np.float32) if len(out) else np.zeros_like(x)


def norm(x, peak=0.9):
    m = float(np.max(np.abs(x))) or 1.0
    return x / m * peak


def robotize(x):
    """Железный голос системной строки: кольцевая модуляция + эхо."""
    t = np.arange(len(x), dtype=np.float32) / SR
    ring = 0.65 + 0.35 * np.sin(2 * np.pi * 61.0 * t)
    y = x * ring
    d = int(0.11 * SR)
    echo = np.zeros_like(y)
    echo[d:] = y[:-d] * 0.28
    d2 = int(0.23 * SR)
    echo2 = np.zeros_like(y)
    echo2[d2:] = y[:-d2] * 0.15
    return (y + echo + echo2).astype(np.float32)


# --- разбор текста --------------------------------------------------------

def parse_chapter(path):
    """Возвращает список блоков: (kind, text) где kind in {title, scenebreak, system, dialogue, narration}."""
    blocks = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n").strip()
            if not line:
                continue
            if line.startswith("# "):
                blocks.append(("title", line[2:].strip()))
                continue
            if re.fullmatch(r"\*\s*\*\s*\*", line):
                blocks.append(("scenebreak", ""))
                continue
            if SYSTEM_RE.match(line) or (line.endswith(".") and SYSTEM_RE.match(line) is None and _is_system(line)):
                blocks.append(("system", line))
                continue
            if line.startswith("– ") or line.startswith("— "):
                blocks.append(("dialogue", line[2:].strip()))
                continue
            blocks.append(("narration", line))
    return blocks


def _is_system(line):
    """Короткая сухая справка: до 130 знаков, есть проценты/точка с запятой, нет глаголов первого лица."""
    if len(line) > 130:
        return False
    if "%" in line and ("Допуск" in line or "Ранг" in line or "Согласование" in line):
        return True
    return False


def pick_voice(kind, text, prev_speaker):
    if kind == "system":
        return "system"
    if kind != "dialogue":
        return "hero"
    for n in MALE2_NAMES:
        if n in text:
            return "male3"
    for n in MALE_NAMES:
        if n in text:
            return "male2"
    for n in FEMALE_NAMES:
        if n in text:
            return "female"
    # без имени: чередуем героя и «собеседника»
    if prev_speaker in (None, "male2", "male3", "female"):
        return "hero"
    return "male2"


def pick_bed(blocks):
    text = " ".join(t for _, t in blocks).lower()
    a = sum(text.count(w) for w in ACTION_WORDS)
    t = sum(text.count(w) for w in TENSE_WORDS)
    s = sum(text.count(w) for w in SEAM_WORDS)
    if a >= max(t, s) and a > 1:
        return "action.wav"
    if s > t and s > 1:
        return "seam.wav"
    if t > 1:
        return "tense.wav"
    return "calm.wav"


# --- синтез ---------------------------------------------------------------

async def synth_one(text, spec, path):
    import edge_tts
    kwargs = {"rate": spec["rate"], "pitch": spec["pitch"]}
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, spec["voice"], **kwargs).save(path)
            if os.path.getsize(path) > 500:
                return True
        except Exception as e:  # noqa: BLE001
            print(f"  ! {type(e).__name__}: {e} (попытка {attempt+1})", file=sys.stderr)
            await asyncio.sleep(1.5 * (attempt + 1))
    return False


async def synth_all(items, jobs=4):
    sem = asyncio.Semaphore(jobs)

    async def worker(text, spec, path):
        async with sem:
            return await synth_one(text, spec, path)

    return await asyncio.gather(*(worker(*it) for it in items))


def cleanup_for_tts(text):
    t = text
    t = re.sub(r"[«»]", "", t)
    t = t.replace("…", "...")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--only-text", action="store_true", help="не синтезировать, только разбор")
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

    blocks = parse_chapter(args.chapter)
    stem = os.path.splitext(os.path.basename(args.chapter))[0]
    out_path = args.out or os.path.join(OUTDIR, stem + ".mp3")

    # назначение голосов
    jobs, prev = [], None
    for i, (kind, text) in enumerate(blocks):
        if kind in ("title", "scenebreak"):
            continue
        v = pick_voice(kind, text, prev)
        if kind == "dialogue":
            prev = v
        elif kind != "system":
            prev = None
        jobs.append((i, kind, text, v))

    if args.only_text:
        for i, kind, text, v in jobs[:20]:
            print(f"{i:3d} {kind:9s} {v:7s} {text[:60]}")
        print(f"... всего {len(jobs)} блоков")
        return

    tasks = []
    for i, kind, text, v in jobs:
        clean = cleanup_for_tts(text)
        key = hashlib.sha1((v + "|" + clean).encode()).hexdigest()[:20]
        path = os.path.join(CACHE, key + ".mp3")
        if os.path.exists(path) and os.path.getsize(path) > 500:
            continue
        tasks.append((clean, VOICES[v], path))
    print(f"{stem}: блоков {len(jobs)}, синтез новых {len(tasks)}")
    if tasks:
        ok = asyncio.run(synth_all(tasks, args.jobs))
        failed = [t for t, r in zip(tasks, ok) if not r]
        if failed:
            print(f"  не синтезировано: {len(failed)}", file=sys.stderr)

    # сборка
    bed = sess(pick_bed(blocks))
    seam = sess("seam.wav")
    chime = sess("chime.wav")
    whoosh = sess("whoosh.wav")
    static = sess("static.wav")
    door = sess("door.wav")

    total = 0
    pieces = []
    for i, kind, text, v in jobs:
        clean = cleanup_for_tts(text)
        key = hashlib.sha1((v + "|" + clean).encode()).hexdigest()[:20]
        path = os.path.join(CACHE, key + ".mp3")
        if not os.path.exists(path):
            continue
        x = decode_any(path)
        if len(x) == 0:
            continue
        if kind == "system":
            x = robotize(x)
        pieces.append((i, kind, x))
        total = sum(len(p[2]) for p in pieces) + int(0.35 * SR) * len(pieces)

    if not pieces:
        print("нечего собирать", file=sys.stderr)
        sys.exit(1)

    scene_after = {i for i, (kind, _) in enumerate(blocks)
                   if i + 1 < len(blocks) and blocks[i + 1][0] == "scenebreak"}

    # раскладка на таймлайн
    gap_n = int(0.34 * SR)
    gap_d = int(0.22 * SR)
    cur = int(0.7 * SR)
    voice = np.zeros(total + int(6 * SR), dtype=np.float32)
    marks = []  # (pos, kind)
    samples = []
    for i, kind, x in pieces:
        if kind == "system":
            voice[cur:cur + len(chime)] += chime[: len(voice) - cur] * 0.35
            marks.append((cur, "system"))
            cur += int(0.55 * SR)
        voice[cur:cur + len(x)] += x
        samples.append((cur, cur + len(x)))
        marks.append((cur + len(x) + gap_n, "after_scene" if i in scene_after else kind))
        cur += len(x) + (gap_d if kind == "dialogue" else gap_n)

    n = cur + int(3.0 * SR)
    voice = voice[:n]

    # подложка: один цикл на всю главу с дакингом по огибающей голоса
    bed_len = n
    reps = int(np.ceil(bed_len / max(1, len(bed))))
    bedfull = np.tile(bed, reps)[:bed_len]
    # огибающая голоса
    env = movavg(np.abs(voice), int(0.05 * SR))
    env = movavg(env, int(0.35 * SR))
    peak = float(np.max(env)) or 1.0
    duck = 1.0 - 0.78 * np.clip(env / peak, 0, 1)
    bed_track = bedfull * duck * 0.11

    # эффекты
    fx = np.zeros(n, dtype=np.float32)

    def place(buf, pos, amp=1.0):
        if pos < 0 or pos >= len(fx):
            return
        e = min(len(fx), pos + len(buf))
        fx[pos:e] += buf[: e - pos] * amp

    # вход: скрип клети, тишина, нарастание
    place(door, int(0.05 * SR), 0.5)
    # на каждый разрыв сцены — whoosh + короткий шум
    for pos, kind in marks:
        if kind == "after_scene":
            place(whoosh, pos, 0.35)
            place(static, pos + int(0.15 * SR), 0.12)
    # финальный аккорд
    place(whoosh, n - int(2.2 * SR), 0.3)

    mix = voice * 1.0 + bed_track + fx * 0.8
    mix = np.tanh(mix * 1.1).astype(np.float32)  # мягкий лимитер
    mix = norm(mix, 0.92)

    tmp = os.path.join(OUTDIR, stem + ".wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    r = run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-ar", str(SR), "-ac", "1", "-b:a", "128k", out_path])
    if r.returncode != 0:
        print(r.stderr[-800:], file=sys.stderr)
        sys.exit(1)
    os.remove(tmp)
    dur = len(mix) / SR
    print(f"готово: {out_path}  {dur/60:.1f} мин")


if __name__ == "__main__":
    main()
