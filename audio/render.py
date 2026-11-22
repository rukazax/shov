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
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BEDS = os.path.join(HERE, "beds")
CACHE = os.path.join(HERE, "cache")
OUTDIR = os.path.join(HERE, "out")
SR = 44100

# --- голоса ---------------------------------------------------------------

# role -> базовый тембр и манера. rate/pitch/volume — строки edge-tts,
# поверх них ложится просодия от эмоции (см. prosody()).
VOICES = {
    "narrator":   {"voice": "ru-RU-DmitryNeural",              "rate": "-3%",  "pitch": "-3Hz",  "volume": "+0%"},
    "hero":       {"voice": "ru-RU-DmitryNeural",              "rate": "+1%",  "pitch": "+1Hz",  "volume": "+2%"},
    "bocman":     {"voice": "en-AU-WilliamMultilingualNeural", "rate": "-10%", "pitch": "-16Hz", "volume": "+2%"},
    "vitya":      {"voice": "en-US-BrianMultilingualNeural",   "rate": "+5%",  "pitch": "+6Hz",  "volume": "+1%"},
    "muhin":      {"voice": "fr-FR-RemyMultilingualNeural",    "rate": "-4%",  "pitch": "-8Hz",  "volume": "+0%"},
    "grisha":     {"voice": "it-IT-GiuseppeMultilingualNeural","rate": "-2%",  "pitch": "-3Hz",  "volume": "+0%"},
    "mihalych":   {"voice": "en-US-AndrewMultilingualNeural",  "rate": "-7%",  "pitch": "-10Hz", "volume": "+0%"},
    "leytenant":  {"voice": "en-US-AndrewMultilingualNeural",  "rate": "+2%",  "pitch": "+5Hz",  "volume": "+1%"},
    "tehnik":     {"voice": "en-US-BrianMultilingualNeural",   "rate": "+2%",  "pitch": "+2Hz",  "volume": "-1%"},
    "ganna":      {"voice": "ru-RU-SvetlanaNeural",            "rate": "-8%",  "pitch": "-6Hz",  "volume": "+0%"},
    "dasha":      {"voice": "en-US-AvaMultilingualNeural",     "rate": "+6%",  "pitch": "+14Hz", "volume": "+1%"},
    "lida":       {"voice": "en-US-EmmaMultilingualNeural",    "rate": "+0%",  "pitch": "+2Hz",  "volume": "+0%"},
    "pozharskaya":{"voice": "fr-FR-VivienneMultilingualNeural","rate": "-3%",  "pitch": "-4Hz",  "volume": "+0%"},
    "agrafena":   {"voice": "ru-RU-SvetlanaNeural",            "rate": "-16%", "pitch": "-12Hz", "volume": "+0%"},
    "female":     {"voice": "pt-BR-ThalitaMultilingualNeural", "rate": "-2%",  "pitch": "+0Hz",  "volume": "+0%"},
    "babka":      {"voice": "pt-BR-ThalitaMultilingualNeural", "rate": "-12%", "pitch": "-10Hz", "volume": "+2%"},
    "system":     {"voice": "ru-RU-DmitryNeural",              "rate": "-12%", "pitch": "-8Hz",  "volume": "+0%"},
}

FEMALE_ROLES = {"ganna", "dasha", "lida", "pozharskaya", "agrafena", "female", "babka"}
MALE_ROLES = {"hero", "bocman", "vitya", "muhin", "grisha", "mihalych", "leytenant", "tehnik"}

# Стем имени -> роль. Стем, а не полная форма: «Боцману», «Боцманом»,
# «Боцман» ловятся одним куском, падежные таблицы не нужны.
CAST = [
    (r"Боцман", "bocman"),
    (r"Вит(?:я|ю|и|е|ей)\b", "vitya"),
    (r"Мухин", "muhin"),
    (r"Гриш(?:а|у|и|е|ей)\b", "grisha"),
    (r"Кожин", "grisha"),
    (r"(?:Геннадий Михалыч|Михалыч)", "mihalych"),
    (r"лейтенант", "leytenant"),
    (r"техник", "tehnik"),
    (r"(?:Ганна|Ганн)\b", "ganna"),
    (r"Ткач\b", "ganna"),
    (r"Даш(?:а|у|и|е|ей)\b", "dasha"),
    (r"девчонк", "dasha"),
    (r"Лид(?:а|у|ы|е|ой)\b", "lida"),
    (r"Пожарск", "pozharskaya"),
    (r"(?:Аграфен|Тихоновн)", "agrafena"),
    (r"Юл(?:я|ю|и|е|ей)\b", "female"),
    (r"(?:Нина Петровна|Ольга Тимуровна)", "female"),
    (r"\bмам[аыуе]\b|\bмать\b|\bматер", "female"),
    (r"(?:вахтёрш|старух|бабк)", "babka"),
    (r"\bженщин", "female"),
]

SPEAK_VERB = (r"(?:сказал|сказала|спросил|спросила|ответил|ответила|проговорил|проговорила|"
              r"произнёс|произнесла|добавил|добавила|крикнул|крикнула|буркнул|буркнула|"
              r"повторил|повторила|заметил|заметила|уточнил|уточнила|позвал|позвала|"
              r"шепнул|шепнула|рявкнул|рявкнула|хмыкнул|хмыкнула|усмехнулся|усмехнулась|"
              r"вздохнул|вздохнула|кивнул|кивнула|продолжил|продолжила|перебил|перебила|"
              r"согласился|согласилась|возразил|возразила|поинтересовался|поинтересовалась|"
              r"объявил|объявила|приказал|приказала|пробормотал|пробормотала)")
MANNER = (r"(?:тихо|громко|негромко|быстро|медленно|упрямо|устало|резко|спокойно|снова|опять|"
          r"тут же|же|не оборачиваясь|за её спиной|за его спиной|в спину|в трубку)?")
ATTR_RE = re.compile(SPEAK_VERB + r"\s*" + MANNER + r"\s+(\S+)")

BED_GAIN = 0.05          # подложка под голосом: было 0.11 — гул в паузах
BED_HP_HZ = 110          # срез низа подложки: он и звучал «фоновым шумом»

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


def cast_hit(text):
    for pat, role in CAST:
        if re.search(pat, text, re.I):
            return role
    return None


def tag_cast(text):
    """Имя в ремарке: «– Ганна Фёдоровна, – лейтенант подошёл ровно, – разрешите вопрос»."""
    for seg in re.split(r"\s[–—]\s", text)[1:]:
        hit = cast_hit(seg)
        if hit:
            return hit
    return None


def attribution_role(text):
    """Кто говорит по атрибуции внутри реплики: «– сказала бабка», «– сказал техник»."""
    hit = tag_cast(text)
    if hit:
        return hit
    m = ATTR_RE.search(text)
    if not m:
        return None
    first = (m.group(1) or "").strip(",.!?…–—»").lower()
    if first == "я":
        return "hero"
    if first in ("она", "её", "ей", "ее"):
        return "female_recent"
    if first in ("он", "его", "ему"):
        return "male_recent"
    window = text[m.start(): m.end() + 45] + " " + text[max(0, m.start() - 30): m.start()]
    return cast_hit(window)


def scene_participants(blocks, idx, span=6):
    """Кто есть в сцене рядом: имена из ремарок и соседних абзацев, свежие впереди."""
    seen = []
    for j in range(max(0, idx - span), min(len(blocks), idx + span + 1)):
        hit = cast_hit(blocks[j][1])
        if hit and hit not in seen:
            seen.append(hit)
    return seen


def resolve_dialogue(idx, blocks, recent, prev_role, narr_role="narrator", adjacent=False,
                     last_spoken=None):
    """Говорящий реплики: ремарка, оклик, ответ второго участника сцены."""
    text = blocks[idx][1]
    r = attribution_role(text)
    if r in ("male_recent", "female_recent"):
        pool = MALE_ROLES if r == "male_recent" else FEMALE_ROLES
        r = next((x for x in recent if x in pool), None)
    if r:
        return r
    # оклик — «– Техник! Сюда!»: имя в реплике означает адресата, а не говорящего
    called = cast_hit(text)
    if called and len(text) < 30:
        for pool in (recent, scene_participants(blocks, idx)):
            others = [x for x in pool if x != called and x != "system"]
            if others:
                return others[0]
        return prev_role or (list(MALE_ROLES - {called})[0] if called in FEMALE_ROLES else "hero")
    # после абзаца без ремарки обычно продолжает тот же, кто говорил
    if prev_role and not adjacent:
        return prev_role
    # ответ второго участника: сперва те, кто уже говорил, потом просто упомянутые
    mentioned = list(scene_participants(blocks, idx))
    if narr_role == "hero" and "hero" not in mentioned:
        mentioned.append("hero")
    if prev_role:
        for pool in (recent, mentioned):
            others = [x for x in pool if x != prev_role and x != "system"]
            if others:
                if last_spoken:
                    others.sort(key=lambda x: last_spoken.get(x, -1), reverse=True)
                return others[0]
    pool = list(recent)
    for x in mentioned:
        if x not in pool:
            pool.append(x)
    return pool[0] if pool else "hero"


def prosody(kind, text, role):
    """Характер реплики поверх тембра: крик, шёпот, вопрос, оборванная фраза."""
    base = VOICES[role]
    rate = int(base["rate"].rstrip("%"))
    pitch = int(base["pitch"].rstrip("Hz"))
    vol = int(base["volume"].rstrip("%"))
    fx = None
    t = text
    if re.search(r"[А-ЯЁ]{4,}", t) or re.search(
            r"(?:крикн|рявкн|заорал|орёт|орал|гаркнул|завопил|взвыл|завопила)", t):
        rate += 7; pitch += 6; vol += 9; fx = "shout"
    if re.search(r"(?:шёпот|шепот|прошептал|вполголоса|тихо сказал|тихо сказала)", t):
        rate -= 5; vol -= 14; fx = "whisper"
    tail = t.rstrip()
    if tail.endswith("?"):
        pitch += 6; rate += 3; vol += 2
    if tail.endswith("!"):
        pitch += 5; rate += 5; vol += 6
    if tail.endswith("?" ) and len(t) < 40:      # короткий переспрос — резче
        pitch += 4; rate += 3
    if t.count("…") + t.count("...") >= 2:       # оборванная, тянущаяся фраза
        rate -= 8; pitch -= 3
    if kind == "narration" and len(t) > 380:     # длинный абзац — ровнее и медленнее
        rate -= 4
    if kind == "dialogue" and len(t) < 18 and tail.endswith("."):  # сухая рубленая реплика
        rate -= 3; pitch -= 2
    return {"voice": base["voice"], "rate": f"{rate:+d}%", "pitch": f"{pitch:+d}Hz",
            "volume": f"{vol:+d}%", "fx": fx}


def cache_key(spec, text):
    sig = "|".join((spec["voice"], spec["rate"], spec["pitch"], spec["volume"], text))
    return hashlib.sha1(sig.encode()).hexdigest()[:20]


def highpass(x, hz=BED_HP_HZ):
    """Однополюсный срез низа — чтобы подложка не гудела в паузах."""
    return (x - movavg(x, int(SR / hz))).astype(np.float32)


def tail_gap(text, kind):
    g = int(0.22 * SR) if kind == "dialogue" else int(0.34 * SR)
    e = text.rstrip()
    if e.endswith("!"):
        g += int(0.12 * SR)
    if e.endswith("?"):
        g += int(0.06 * SR)
    if e.endswith("…") or e.endswith("..."):
        g += int(0.28 * SR)
    return g


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
    kwargs = {"rate": spec["rate"], "pitch": spec["pitch"], "volume": spec.get("volume", "+0%")}
    for attempt in range(6):
        try:
            await edge_tts.Communicate(text, spec["voice"], **kwargs).save(path)
            if os.path.getsize(path) > 500:
                return True
        except Exception as e:  # noqa: BLE001
            print(f"  ! {type(e).__name__}: {e} (попытка {attempt+1})", file=sys.stderr)
            await asyncio.sleep(0.4 * (attempt + 1))
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
    ap.add_argument("--jobs", type=int, default=7)
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

    blocks = parse_chapter(args.chapter)
    stem = os.path.splitext(os.path.basename(args.chapter))[0]
    out_path = args.out or os.path.join(OUTDIR, stem + ".mp3")

    # назначение голосов: рассказчик — всегда один (narrator), персонажи —
    # по атрибуции «– сказал Боцман» и по имени в соседнем абзаце
    narration_text = " ".join(t for k, t in blocks if k == "narration")
    first_person = len(re.findall(r"(?:^|\s)(?:я|меня|мне|мной|мой|моя|моё)(?:\s|[,.!?…]|$)", narration_text, re.I))
    narr_role = "hero" if first_person > max(3, len(narration_text) // 900) else "narrator"

    jobs, prev_role, recent, prev_dialogue, last_spoken = [], None, [], False, {}
    for i, (kind, text) in enumerate(blocks):
        if kind in ("title", "scenebreak"):
            continue
        if kind == "scenebreak":
            prev_role, prev_dialogue = None, False
            continue
        if kind == "system":
            role = "system"
        elif kind == "dialogue":
            role = resolve_dialogue(i, blocks, recent, prev_role, narr_role, prev_dialogue, last_spoken)
            recent = [role] + [r for r in recent if r != role]
            hit = cast_hit(text)
            if hit and (hit == role or len(text) < 60):
                recent = [hit] + [x for x in recent if x != hit]
        else:
            role = narr_role
            hit = cast_hit(text)
            if hit:
                recent = [hit] + [r for r in recent if r != hit]
        prev_dialogue = kind == "dialogue"
        if kind == "dialogue":
            prev_role = role
            last_spoken[role] = i
        jobs.append((i, kind, text, role))

    if args.only_text:
        for i, kind, text, v in jobs[:20]:
            print(f"{i:3d} {kind:9s} {v:7s} {text[:60]}")
        print(f"... всего {len(jobs)} блоков")
        return

    tasks, specs = [], {}
    for i, kind, text, role in jobs:
        clean = cleanup_for_tts(text)
        spec = prosody(kind, text, role)
        key = cache_key(spec, clean)
        specs[i] = (spec, key)
        path = os.path.join(CACHE, key + ".mp3")
        if os.path.exists(path) and os.path.getsize(path) > 500:
            continue
        tasks.append((clean, spec, path))
    print(f"{stem}: блоков {len(jobs)}, синтез новых {len(tasks)}")
    if tasks:
        ok = asyncio.run(synth_all(tasks, args.jobs))
        failed = [t for t, r in zip(tasks, ok) if not r]
        # сервис синтеза регулярно отбивает часть запросов: добиваем пачками,
        # а недобор до конца — это дырка в дорожке, её нельзя молча оставить
        for attempt in range(1, 4):
            if not failed:
                break
            print(f"  не синтезировано: {len(failed)}, пауза и заход {attempt}/3", file=sys.stderr)
            time.sleep(3 * attempt)
            ok = asyncio.run(synth_all(failed, max(2, args.jobs // 2)))
            failed = [t for t, r in zip(failed, ok) if not r]
        if failed:
            print(f"  ОТКАЗ: {len(failed)} блоков не синтезировано, дорожка не собрана", file=sys.stderr)
            sys.exit(1)

    # сборка
    bed = highpass(sess(pick_bed(blocks)), BED_HP_HZ)
    seam = sess("seam.wav")
    chime = sess("chime.wav")
    whoosh = sess("whoosh.wav")
    static = sess("static.wav")
    door = sess("door.wav")

    total = 0
    pieces = []
    for i, kind, text, role in jobs:
        spec, key = specs[i]
        path = os.path.join(CACHE, key + ".mp3")
        if not os.path.exists(path):
            continue
        x = decode_any(path)
        if len(x) == 0:
            continue
        if kind == "system":
            x = robotize(x)
        elif spec["fx"] == "shout":
            x = np.tanh(x * 1.45).astype(np.float32)   # крик: поджатый, резкий
        elif spec["fx"] == "whisper":
            x = (highpass(x, 200) * 0.72).astype(np.float32)  # шёпот: ближе, глуше
        pieces.append((i, kind, x, text))
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
    for i, kind, x, text in pieces:
        if kind == "system":
            voice[cur:cur + len(chime)] += chime[: len(voice) - cur] * 0.35
            marks.append((cur, "system"))
            cur += int(0.55 * SR)
        voice[cur:cur + len(x)] += x
        samples.append((cur, cur + len(x)))
        g = tail_gap(text, kind)
        marks.append((cur + len(x) + g, "after_scene" if i in scene_after else kind))
        cur += len(x) + g

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
    bed_track = bedfull * duck * BED_GAIN

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
    mix = np.tanh(mix * 1.05).astype(np.float32)  # мягкий лимитер
    mix = norm(mix, 0.92)

    tmp = os.path.join(OUTDIR, stem + ".wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    r = run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-ar", str(SR), "-ac", "1", "-b:a", "96k", out_path])
    if r.returncode != 0:
        print(r.stderr[-800:], file=sys.stderr)
        sys.exit(1)
    os.remove(tmp)
    dur = len(mix) / SR
    print(f"готово: {out_path}  {dur/60:.1f} мин")


if __name__ == "__main__":
    main()
