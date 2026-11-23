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
import json
import os
import random
import re
import subprocess
import sys
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BEDS = os.path.join(HERE, "beds")
CACHE = os.path.join(HERE, "cache")
# Тома пишутся в разные каталоги: имена глав совпадают (ch01.md есть в каждом
# томе), и без разделения разметка и дорожки второго тома затёрли бы первый.
OUTDIR = os.path.join(HERE, os.environ.get("AUDIO_OUT", "out"))
CASTDIR = os.path.join(HERE, os.environ.get("AUDIO_CAST", "cast"))
SR = 44100

# --- голоса ---------------------------------------------------------------

# role -> базовый тембр и манера. rate/pitch/volume — строки edge-tts,
# поверх них ложится просодия от эмоции (см. prosody()).
VOICES = {
    # Только родные русские голоса: их ровно два — Dmitry (муж) и Svetlana
    # (жен). Мультиязычные голоса каталога читают по-русски с акцентом — на
    # слух это слышно сразу, поэтому в карте их нет. Персонажей различает
    # согласованный сдвиг темпа и тона: мужские 106–138 Гц с шагом 3–5 Гц,
    # женские 157–181 Гц с шагом 4–5 Гц. Проверка — voice_probe.py: он печатает
    # медиану основного тона по роли, а не «на глаз».
    # Женская база female (+3 % / +2 Гц) — принятый владельцем вариант.
    "narrator":   {"voice": "ru-RU-DmitryNeural",   "rate": "-2%",  "pitch": "-2Hz",  "volume": "+0%"},
    "hero":       {"voice": "ru-RU-DmitryNeural",   "rate": "+1%",  "pitch": "+2Hz",  "volume": "+1%"},
    "bocman":     {"voice": "ru-RU-DmitryNeural",   "rate": "-15%", "pitch": "-16Hz", "volume": "+1%"},
    "vitya":      {"voice": "ru-RU-DmitryNeural",   "rate": "+14%", "pitch": "+14Hz", "volume": "+1%"},
    "muhin":      {"voice": "ru-RU-DmitryNeural",   "rate": "-5%",  "pitch": "-5Hz",  "volume": "+0%"},
    "grisha":     {"voice": "ru-RU-DmitryNeural",   "rate": "-8%",  "pitch": "-8Hz",  "volume": "+0%"},
    "mihalych":   {"voice": "ru-RU-DmitryNeural",   "rate": "-11%", "pitch": "-11Hz", "volume": "+0%"},
    "leytenant":  {"voice": "ru-RU-DmitryNeural",   "rate": "+5%",  "pitch": "+4Hz",  "volume": "+1%"},
    "tehnik":     {"voice": "ru-RU-DmitryNeural",   "rate": "+9%",  "pitch": "+9Hz",  "volume": "-1%"},
    "system":     {"voice": "ru-RU-DmitryNeural",   "rate": "-25%", "pitch": "-18Hz", "volume": "+0%"},
    "ganna":      {"voice": "ru-RU-SvetlanaNeural", "rate": "-4%",  "pitch": "-5Hz",  "volume": "+0%"},
    "dasha":      {"voice": "ru-RU-SvetlanaNeural", "rate": "+12%", "pitch": "+11Hz", "volume": "+1%"},
    "lida":       {"voice": "ru-RU-SvetlanaNeural", "rate": "+8%",  "pitch": "+7Hz",  "volume": "+0%"},
    "pozharskaya":{"voice": "ru-RU-SvetlanaNeural", "rate": "+0%",  "pitch": "-1Hz",  "volume": "+0%"},
    "agrafena":   {"voice": "ru-RU-SvetlanaNeural", "rate": "-13%", "pitch": "-13Hz", "volume": "+0%"},
    "female":     {"voice": "ru-RU-SvetlanaNeural", "rate": "+3%",  "pitch": "+2Hz",  "volume": "+0%"},
    "babka":      {"voice": "ru-RU-SvetlanaNeural", "rate": "-8%",  "pitch": "-9Hz",  "volume": "+1%"},

    # --- том 2 «Ходок» ---------------------------------------------------
    # Новый состав Стыка и Второй Земли. Тембры те же два, различает манера:
    # Гущин — медленный и низкий, Сомов — быстрый и ровный (он всегда прав
    # по бумаге, и голос у него как протокол), Ветров — самый медленный в
    # книге, Костя — молодой и торопливый, Ковалёва — чёткая, Нина — ребёнок.
    "gushchin":   {"voice": "ru-RU-DmitryNeural",   "rate": "-10%", "pitch": "-7Hz",  "volume": "+1%"},
    "somov":      {"voice": "ru-RU-DmitryNeural",   "rate": "+4%",  "pitch": "-4Hz",  "volume": "+0%"},
    "vetrov":     {"voice": "ru-RU-DmitryNeural",   "rate": "-14%", "pitch": "-14Hz", "volume": "+0%"},
    "kostya":     {"voice": "ru-RU-DmitryNeural",   "rate": "+12%", "pitch": "+12Hz", "volume": "+1%"},
    "kovaleva":   {"voice": "ru-RU-SvetlanaNeural", "rate": "+6%",  "pitch": "+6Hz",  "volume": "+0%"},
    "nina":       {"voice": "ru-RU-SvetlanaNeural", "rate": "+16%", "pitch": "+15Hz", "volume": "+1%"},

    # --- том 3 «Мост» ----------------------------------------------------
    # Управление и дорога. Кац — процедура в человеческом лице: ровно, без
    # подъёма. Веретенников — самый медленный и низкий мужской тембр в книге
    # (он решает судьбы фразами из трёх слов). Кержак — обычный темп, но
    # низкая посадка: человек, который говорит мало и по делу. Семён-2 —
    # на четыре герца ниже героя и медленнее: тот же голос, другая жизнь.
    "kac":          {"voice": "ru-RU-SvetlanaNeural", "rate": "+2%",  "pitch": "-3Hz",  "volume": "+0%"},
    "veretennikov": {"voice": "ru-RU-DmitryNeural",   "rate": "-20%", "pitch": "-13Hz", "volume": "+0%"},
    "kerzhak":      {"voice": "ru-RU-DmitryNeural",   "rate": "+2%",  "pitch": "-12Hz", "volume": "+0%"},
    "semyon2":      {"voice": "ru-RU-DmitryNeural",   "rate": "-4%",  "pitch": "-2Hz",  "volume": "+0%"},
    "dorohov":      {"voice": "ru-RU-DmitryNeural",   "rate": "+6%",  "pitch": "-8Hz",  "volume": "+0%"},
    "tarasov":      {"voice": "ru-RU-DmitryNeural",   "rate": "+11%", "pitch": "-1Hz",  "volume": "+1%"},
    "teacher":      {"voice": "ru-RU-SvetlanaNeural", "rate": "+7%",  "pitch": "-6Hz",  "volume": "+0%"},
}

FEMALE_ROLES = {"ganna", "dasha", "lida", "pozharskaya", "agrafena", "female", "babka",
                "kovaleva", "nina"}
MALE_ROLES = {"hero", "bocman", "vitya", "muhin", "grisha", "mihalych", "leytenant", "tehnik",
              "gushchin", "somov", "vetrov", "kostya"}

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
    (r"Нин[аыуео][йя]?\s+Петровн|Ольга Тимуровна", "babka"),
    (r"Нин[аыуео][йя]?\b", "nina"),
    (r"Гущин", "gushchin"),
    (r"Ковал[её]в", "kovaleva"),
    (r"Сомов", "somov"),
    (r"(?:Ветров|Пётр Ильич|Петр Ильич)", "vetrov"),
    (r"Кост(?:я|ю|е|и|ей)\b|Шмел[её]в|Константин", "kostya"),
    (r"Семён|Семен\b|Лоскутов", "hero"),
    (r"смотрител", "vetrov"),
    (r"\bмам[аыуе]\b|\bмать\b|\bматер", "female"),
    (r"(?:вахтёрш|старух|бабк|бабушк|бабул)", "babka"),
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

BED_GAIN = 0.0           # 1С читает БЕЗ подложки: у эталона пол тишины −84,9 dBFS,
                         # то есть в паузах почти цифровой ноль. Музыка у них
                         # только в шапке. Проверено замером — подложку не включать.
BED_HP_HZ = 80           # срез низа: ниже него подложка гудит

# --- XTTS v2 на Windows-боксе -------------------------------------------
# Тембры — живые эталоны 1С-Паблишинг (11 с монозаписи). Управление эмоцией
# идёт через эталон: движок клонирует не только тембр, но и манеру отрывка,
# поэтому у одного голоса может быть несколько отрывков под разные состояния.
XTTS_URL = os.environ.get("XTTS_URL", "")
XTTS_REFS = {
    "narrator": "hero", "hero": "hero", "system": "hero",
    "babka": "female2", "agrafena": "female2", "ganna": "female2",
    "dasha": "female1", "lida": "female1", "pozharskaya": "female1", "female": "female1",
    "bocman": "male_poteryaev", "muhin": "male_poteryaev", "mihalych": "male_poteryaev",
    "vitya": "male_petrov", "grisha": "male_petrov", "tehnik": "male_petrov",
    "leytenant": "male_petrov",
}
# октавный сдвиг тембра, когда роль делит эталон с другой ролью
REF_PITCH = {"babka": -3, "agrafena": -5, "ganna": -1, "dasha": +2, "lida": 0,
             "pozharskaya": -2, "bocman": -4, "muhin": -2, "mihalych": -3,
             "vitya": +3, "grisha": 0, "tehnik": +1, "leytenant": +1}

# Смягчение тембра и комната. Проверяется замером: доля шипящих 4–8 кГц
# должна падать, а тишина между блоками — не быть цифровым нулём.
SOFT_SHELF_HZ = 4600     # выше — режем: там живёт «механическая» жёсткость
SOFT_SHELF_DB = -4.0     # эталон 1С: шипящих 7,8 % — у нас −3 дБ даёт 8,8 %
SOFT_BODY_DB = 5.0       # тела внизу: у эталона 16,5 % энергии ниже 120 Гц, у нас 8 %
SOFT_PRES_DB = 2.0       # присутствие 1,8 кГц: эталон ярче нас на ~190 Гц центроида,
                         # но яркость берём ниже шипящих, а не выше
ROOM_WET = 0.42          # сколько отражений подмешать к сухому голосу
ROOM_TAIL = 0.62         # длина хвоста комнаты, с
ROOM_TONE_DB = -85.0     # «воздух» студии. У эталона пол тишины −84,9 dBFS,
                         # у нас был абсолютный ноль — это и есть мёртвая пауза.
                         # Это не слышимый шум, а маскировка цифровой тишины.
LOUD_I = -20.0           # эталон −21,5 LUFS; −20 — компромисс с телефоном
LOUD_TP = -3.0           # dBTP, лимитер
FX_WHOOSH = 0.0          # шумовые эффекты на границах сцен — выключены
FX_STATIC = 0.0

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


def compress(x, thr=-16.0, ratio=1.8, att_ms=8.0, rel_ms=180.0):
    """Плотность студийной записи.

    Цель — не «плотнее», а как у эталона: у 1С LRA 7,1 LU. При ratio 3,5 у нас
    выходило 4,4 LU — уже пережато, и это слышно как ровное, бездыханное
    чтение. Здесь мягко: атака 8 мс, чтобы согласные не срезались.
    """
    a = max(1, int(att_ms * SR / 1000))
    env_db = 20.0 * np.log10(movavg(np.abs(x), a) + 1e-9)
    over = np.maximum(env_db - thr, 0.0)
    gr_db = movavg(over * (1.0 - 1.0 / ratio), max(1, int(rel_ms * SR / 1000)))
    return (x * (10.0 ** (-gr_db / 20.0))).astype(np.float32)


def studio_air(n):
    """Очень тихий ровный «воздух» на месте цифрового нуля.

    Пол тишины у эталона −84,9 dBFS. Убрать шум совсем — значит получить
    мёртвые паузы, в которых слышно, что это файл, а не запись. На −85 дБ
    шум не слышен как шум, он только убирает провал в абсолютный ноль.
    Детерминированный: повторный рендер даёт тот же результат.
    """
    rnd = np.random.RandomState(5)
    air = rnd.randn(n).astype(np.float32)
    air = highpass(air, 90)                     # без инфраниза
    return air * (10.0 ** (ROOM_TONE_DB / 20.0))


def integrated_lufs(path):
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s*(-?\d+\.\d+)\s*LUFS", r.stderr)
    return float(m[-1]) if m else LOUD_I


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


PRONOUNS = {"я", "он", "она", "оно", "его", "её", "ее", "ему", "ей", "они", "их"}


def _remarks(text):
    """Куски между тире, которые похожи на ремарку, а не на продолжение речи.

    Ремарка стоит после куска, оборванного запятой или многоточием («– Текст,
    – сказал X»), либо открывает новый кусок после тире, либо начинается с
    местоимения и прошедшего времени («– Она посмотрела на меня»). Кусок после
    точки («– Текст. – Новая реплика») ремаркой не считается: это речь.
    """
    segs = re.split(r"\s[–—]\s", text)[1:]
    out = []
    for i, seg in enumerate(segs):
        prev = segs[i - 1].rstrip() if i else ""
        starts_pron = re.match(r"\s*(?:Он|Она|Я)\s+[а-яё]{2,}(?:л|ла|лся|лась)\b", seg, re.I)
        if i == 0 or prev.endswith((",", "…", ":")) or starts_pron:
            out.append(seg)
    return out


def tag_cast(text):
    """Кто в ремарке: «– Ганна Фёдоровна, – лейтенант подошёл ровно, – …» → лейтенант.

    Имя при глаголе речи — сильное правило; имя в начале ремарки с действием
    после него («Бабушка помолчала») — слабое. Местоимение в позиции имени
    («сказал я», «поправил он») имени не даёт: этим занимается remark_pronoun.
    """
    remarks = _remarks(text)
    for seg in remarks:
        m = ATTR_RE.search(seg)
        if not m:
            continue
        word = (m.group(m.lastindex) or "").strip(",.!?…–—»« ")
        if word.lower() in PRONOUNS:
            continue
        hit = cast_hit(seg)
        if hit:
            return hit
    for seg in remarks:
        m = re.match(r"\s*([^\s,.;:!?»«–—]+)\s+[а-яё]{2,}(?:л|ла|лся|лась)\b", seg, re.I)
        if m:
            hit = cast_hit(m.group(1))
            if hit:
                return hit
    return None


def remark_pronoun(text):
    """Пол по ремарке без имени: «– поправил он», «– Она посмотрела на меня»."""
    for seg in _remarks(text):
        m = re.match(r"\s*(Он|Она|Я)\b", seg, re.I)
        if m:
            w = m.group(1).lower()
            return "hero" if w == "я" else ("male_recent" if w == "он" else "female_recent")
        m = re.search(r"\b[а-яё]{2,}(?:л|ла|лся|лась)\s+(он|она)\b", seg, re.I)
        if m:
            return "male_recent" if m.group(1).lower() == "он" else "female_recent"
    return None


def attribution_role(text):
    """Кто говорит по атрибуции внутри реплики: «– сказала бабушка», «– поправил он»."""
    hit = tag_cast(text)
    if hit:
        return hit
    g = remark_pronoun(text)
    if g:
        return g
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
    hit = cast_hit(window)
    if hit:
        return hit
    # «сказала вторая», «спросил старший»: имени нет, но род глагола есть
    verb = re.match(r"[а-яё]+", m.group(0), re.I)
    if verb:
        return "female_recent" if verb.group(0).lower().endswith("а") else "male_recent"
    return None


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
        # «сказал он» — это заведомо не рассказчик: о себе он сказал бы «сказал я».
        # Без этого recent[0] почти всегда hero и реплика уходила ему же.
        pool = pool - {"hero"}
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

    # Микроразброс. Без него каждая реплика одного персонажа звучит одним и тем
    # же пресетом — именно это и слышится как «механически». Разброс считается
    # от текста, поэтому повторный рендер даёт тот же результат и тот же кэш.
    j = int(hashlib.sha1(t.encode()).hexdigest()[:8], 16)
    # ±2 — предел без ресинтеза: ключ кэша включает rate/pitch, а голос
    # рассказчика (Dmitry) у сервиса периодически отбивает целиком.
    rate += (j % 5) - 2                       # ± 2 %
    pitch += ((j >> 8) % 5) - 2               # ± 2 Гц
    if j % 3 == 0 and len(t) > 90:            # длинная реплика — чуть ровнее
        rate -= 1

    spec = {"voice": base["voice"], "rate": f"{rate:+d}%", "pitch": f"{pitch:+d}Hz",
            "volume": f"{vol:+d}%", "fx": fx}
    if XTTS_URL:
        mood = "tense" if fx == "shout" or t.rstrip().endswith("!") else "calm"
        base_ref = XTTS_REFS.get(role, "hero")
        spec["ref"] = f"{base_ref}_{mood}"
        spec["speed"] = round(1.0 + rate / 100.0, 3)
        spec["shift"] = REF_PITCH.get(role, 0)
    return spec


def cache_key(spec, text):
    parts = [spec["voice"], spec["rate"], spec["pitch"], spec["volume"], text]
    if spec.get("ref"):
        parts += [spec["ref"], str(spec["speed"]), str(spec.get("shift", 0))]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:20]


def highpass(x, hz=BED_HP_HZ):
    """Однополюсный срез низа — чтобы подложка не гудела в паузах."""
    return (x - movavg(x, int(SR / hz))).astype(np.float32)


# Коррекция тембра: замер по 14 полосам против эталона 1С-Паблишинг
# (официальный демо-фрагмент, Влад Римский, введение книги 1).
# Слева — середина полосы, справа — на сколько дБ поднять/опустить.
# Эталон: сильный низ 50–120 Гц, меньше «коробки» 180–700, крупное присутствие
# 2,5–3,5 кГц, меньше шипящих 4,5–6 к и больше воздуха 8–11 к.
def _eq_table():
    """Кривая живёт в eq_curve.json: её правит eq_calibrate.py по замеру,
    а не человек на слух. Нет файла — берётся зашитый замер."""
    base = [(55.0, 3.6), (100.0, 4.7), (150.0, 0.0), (230.0, -4.2), (360.0, -2.8),
            (570.0, -3.1), (880.0, -2.2), (1350.0, -1.2), (2100.0, 1.8), (3000.0, 6.7),
            (4000.0, 1.0), (5200.0, -3.3), (7000.0, 0.5), (9500.0, 2.7), (12000.0, -6.0)]
    p = os.path.join(HERE, "eq_curve.json")
    try:
        with open(p, encoding="utf-8") as f:
            return [(float(a), float(b)) for a, b in json.load(f)["points"]]
    except Exception:
        return base


EQ_TABLE = _eq_table()


def soften(x):
    """Тембр под эталон: одна кривая по замеру, а не три догадки.

    «Механический» голос — это не только шипящие: у синтеза мало низкого тела
    и мало присутствия 2,5–3,5 кГц, зато больше «коробки» 200–700 Гц. Кривая
    EQ_TABLE снята сравнением спектров по полосам с записью 1С, поэтому
    исправляет сразу всё, что слышно как «не живой человек в студии».
    """
    n = len(x)
    if n < 256:
        return x
    S = np.fft.rfft(x.astype(np.float64))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    xs = np.log2(np.maximum(f, 1.0))
    pts_x = np.log2(np.array([p[0] for p in EQ_TABLE]))
    pts_y = np.array([p[1] for p in EQ_TABLE])
    db = np.interp(xs, pts_x, pts_y)
    g = 10.0 ** (db / 20.0)
    g *= 1.0 / (1.0 + (np.maximum(f - 11500.0, 0.0) / 1200.0) ** 4)   # без цифрового воздуха
    return np.fft.irfft(S * g, n).astype(np.float32)


def room(x, wet=ROOM_WET):
    """Ранние отражения и короткий хвост. Возвращает блок длиннее исходного:
    хвост ложится в паузу после реплики — так тишина перестаёт быть цифровым
    нулём, и чтение звучит как в помещении, а не в вакууме.
    """
    ir_len = int(ROOM_TAIL * SR)
    ir = np.zeros(ir_len, dtype=np.float32)
    for d_ms, a in ((9, 0.30), (16, 0.24), (25, 0.18), (37, 0.13), (53, 0.09), (71, 0.06)):
        ir[int(d_ms * SR / 1000)] += a
    tail = np.random.RandomState(11).randn(ir_len - int(0.014 * SR)).astype(np.float32)
    tail *= np.exp(-np.linspace(0.0, 6.5, len(tail))).astype(np.float32) * 0.05
    ir[int(0.014 * SR):] += tail
    ir /= max(float(np.abs(ir).sum()), 1e-6)
    n = len(x) + ir_len - 1
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n).astype(np.float32)
    out = np.zeros(n, dtype=np.float32)
    out[:len(x)] = x * (1.0 - wet)
    out += y * wet
    return out


def tail_gap(text, kind):
    g = int(0.22 * SR) if kind == "dialogue" else int(0.34 * SR)
    e = text.rstrip()
    if e.endswith("!"):
        g += int(0.12 * SR)
    if e.endswith("?"):
        g += int(0.06 * SR)
    if e.endswith("…") or e.endswith("..."):
        g += int(0.28 * SR)
    # Дыхание ±60 мс от текста: ровные паузы подряд слышны как метроном.
    j = int(hashlib.sha1(text.encode()).hexdigest()[:6], 16)
    g += int(((j % 5) - 2) * 0.03 * SR)
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

def synth_xtts(text, spec, path):
    """Синтез через XTTS v2: POST на сервер Windows-бокса, обратно — wav."""
    import urllib.request
    body = json.dumps({"text": text, "ref": spec["ref"], "language": "ru",
                       "speed": spec["speed"]}).encode()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(4):
        try:
            req = urllib.request.Request(XTTS_URL.rstrip("/") + "/tts", data=body,
                                         headers={"Content-Type": "application/json"})
            data = opener.open(req, timeout=600).read()
            if len(data) < 2000:
                raise ValueError(f"короткий ответ {len(data)} байт")
            raw = path + ".src.wav"
            with open(raw, "wb") as f:
                f.write(data)
            shift = spec.get("shift", 0)
            if shift:   # сдвиг тембра без смены длительности
                k = 2.0 ** (shift / 12.0)
                af = f"asetrate=24000*{k:.6f},aresample=24000,atempo={1/k:.6f}"
            else:
                af = "anull"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af,
                            "-b:a", "128k", path], check=True)
            os.remove(raw)
            return os.path.getsize(path) > 500
        except Exception as e:  # noqa: BLE001
            print(f"  ! XTTS {type(e).__name__}: {e} (попытка {attempt+1})", file=sys.stderr)
            time.sleep(1.0 * (attempt + 1))
    return False


async def synth_one(text, spec, path):
    if spec.get("ref"):
        return await asyncio.to_thread(synth_xtts, text, spec, path)
    if await synth_try(text, spec, path, 40):
        return True
    return await synth_split(text, spec, path)


# Сервис отдаёт звук неровно: 22.11 в провале было 0/16 и 0/12 подряд, днём
# 23.11 — стабильно 25 % успеха (3 из 12) даже в один поток, а изредка
# открывается «окно» и проходит почти всё. То есть «ничего не приходит 5 минут»
# — это провал, а «3 из 12» — рабочий режим, и путать их нельзя.
# Предохранитель общий для всех процессов (лежит файлом): смотрим не на число
# отказов подряд, а на время с последнего УСПЕХА. Если звука нет 45 с при 30
# отказах — вся машина спит, пауза 60/120/240/480 с по уровням, а любой
# успешный блок снимает паузу и обнуляет уровень.
BREAKER = os.path.join(CACHE, "breaker.json")


def _breaker_timeout():
    try:
        with open(BREAKER) as f:
            return max(0.0, float(json.load(f).get("until", 0)) - time.time())
    except Exception:
        return 0.0


def _breaker_update(ok):
    import fcntl
    with open(BREAKER + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            now = time.time()
            try:
                with open(BREAKER) as f:
                    st = json.load(f)
            except Exception:
                st = {"fail": 0, "level": 0, "until": 0.0, "last_ok": now}
            if ok:
                st.update(fail=0, level=0, until=0.0, last_ok=now)
            else:
                st["fail"] = st.get("fail", 0) + 1
                silent = now - float(st.get("last_ok", now))
                if st["fail"] >= 30 and silent > 45:
                    st["level"] = min(st.get("level", 0) + 1, 4)
                    wait = min(480, 60 * 2 ** (st["level"] - 1))
                    st.update(fail=0, until=now + wait)
                    print(f"  ⏸ звука нет {silent:.0f} с: вся машина спит {wait} с "
                          f"(уровень {st['level']})", file=sys.stderr)
            tmp = BREAKER + ".tmp"
            with open(tmp, "w") as f:
                json.dump(st, f)
            os.replace(tmp, BREAKER)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _svc_note(ok):
    _breaker_update(ok)


async def _svc_wait():
    while True:
        left = _breaker_timeout()
        if left <= 0:
            return
        await asyncio.sleep(min(left, 30) + random.random())


async def synth_try(text, spec, path, tries):
    """Долбим один и тот же текст, пока сервис не отдаст звук (без обрыва по времени)."""
    import edge_tts
    kwargs = {"rate": spec["rate"], "pitch": spec["pitch"], "volume": spec.get("volume", "+0%")}
    # Замер 22.11: сервис отбивает 8 запросов из 12 подряд даже при свободной
    # памяти и одном соединении — это его собственная чехарда, не наш троттлинг.
    # По времени блок не обрываем (обрыв = дырка в дорожке), но паузу растим:
    # отказ приходит за 2-4 с, поэтому в начале долбим часто, а на затяжной
    # волне переходим на выжидание.
    attempt = 0
    while attempt < tries:
        await _svc_wait()
        try:
            # Без таймаута один зависший запрос держит воркер часами: процесс
            # живёт, CPU 0 %, кэш не растёт. 25 с хватает любому блоку.
            await asyncio.wait_for(
                edge_tts.Communicate(text, spec["voice"], **kwargs).save(path), timeout=25)
            if os.path.getsize(path) > 500:
                _svc_note(True)
                return True
            _svc_note(False)
        except Exception as e:  # noqa: BLE001
            _svc_note(False)
            print(f"  ! {type(e).__name__} [{spec['voice'].split('-')[2]} {spec['rate']} {spec['pitch']}] "
                  f"(попытка {attempt+1}) {text[:40]}", file=sys.stderr)
        attempt += 1
        # Замер 23.11 (00:28): на 24 потоках отказов ровно столько же, сколько
        # в один поток (29–34 %), а успех растёт линейно с параллельностью:
        # 8 потоков — 35 блоков/мин, 16 — 78, 24 — 136. Поэтому «выжидающие»
        # паузы каждые 10 попыток только режут темп: провал ловит предохранитель
        # выше, а между попытками хватает короткой дрожи.
        await asyncio.sleep(0.15 + random.random() * 0.35)
    return False


async def synth_split(text, spec, path):
    """Блок, который сервис не отдаёт целиком, режем по фразам и склеиваем."""
    parts = [p for p in re.split(r"(?<=[.!?…])\s+", text) if p.strip()]
    if len(parts) < 2:                 # нечего резать — фраза одна
        return False
    print(f"  ~ блок не отдаётся, режу на {len(parts)} фраз", file=sys.stderr)
    pieces = []
    for i, part in enumerate(parts):
        p = f"{path}.p{i:03d}.mp3"
        if not await synth_try(part, spec, p, 40):
            for q in pieces:
                os.path.exists(q) and os.remove(q)
            return False
        pieces.append(p)
    lst = f"{path}.concat.txt"
    with open(lst, "w", encoding="utf-8") as f:
        for q in pieces:
            f.write("file '%s'\n" % os.path.abspath(q))
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", path], check=True)
    finally:
        for q in pieces + [lst]:
            os.path.exists(q) and os.remove(q)
    return os.path.getsize(path) > 500


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
    ap.add_argument("--dump-cast", action="store_true", help="записать разметку ролей в cast/")
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--xtts", default=None, metavar="URL",
                    help="синтез через XTTS на Windows-боксе, напр. http://192.168.88.20:8765")
    args = ap.parse_args()

    global XTTS_URL
    if args.xtts:
        XTTS_URL = args.xtts
    if XTTS_URL:
        print(f"движок: XTTS {XTTS_URL}")

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

    # Расстановка голосов угадывается по ремаркам и хорошо работает там, где
    # они есть. Файл cast/<глава>.cast.txt — источник правды: он же правится
    # руками. Нет файла — работает угадывание, как раньше.
    cast_path = os.path.join(CASTDIR, stem + ".cast.txt")
    if args.dump_cast:
        os.makedirs(CASTDIR, exist_ok=True)
        with open(cast_path, "w", encoding="utf-8") as f:
            f.write(f"# {stem} — кто говорит. Колонки: номер, тип, роль, текст.\n")
            f.write("# Правится только роль. Строки на # игнорируются.\n")
            f.write("# Роли: " + " ".join(sorted(VOICES)) + "\n")
            for i, kind, text, role in jobs:
                f.write("%d\t%s\t%s\t%s\n" % (i, kind, role, " ".join(text.split())))
        print(f"{stem}: разметка → {cast_path}, блоков {len(jobs)}")
        return

    if os.path.exists(cast_path):
        roles = {}
        for line in open(cast_path, encoding="utf-8"):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                roles[int(parts[0])] = parts[2].strip()
            except ValueError:
                continue
        fixed, out = 0, []
        for i, kind, text, role in jobs:
            want = roles.get(i)
            if want and want != role:
                if want in VOICES:
                    print(f"  #{i}: {role} → {want}   {text[:50]}")
                    role, fixed = want, fixed + 1
                else:
                    print(f"  #{i}: роли «{want}» нет, оставил {role}", file=sys.stderr)
            out.append((i, kind, text, role))
        jobs = out
        print(f"{stem}: разметка из файла, исправлено {fixed} из {len(jobs)}")

    if args.only_text:
        missing = 0
        for i, kind, text, role in jobs:
            spec = prosody(kind, text, role)
            mp3 = os.path.join(CACHE, cache_key(spec, cleanup_for_tts(text)) + ".mp3")
            if not (os.path.exists(mp3) and os.path.getsize(mp3) > 500):
                missing += 1
                if missing <= 5:
                    print(f"  НЕТ КЭША #{i} {role} ({len(text)} зн.): {text[:120]}")
        for i, kind, text, v in jobs[:20]:
            print(f"{i:3d} {kind:9s} {v:7s} {text[:60]}")
        print(f"... всего {len(jobs)} блоков, нет в кэше {missing}")
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
        total = sum(len(p[2]) for p in pieces) + int((0.35 + ROOM_TAIL) * SR) * len(pieces)

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
        # смягчение тембра и комната — на каждой реплике, до раскладки:
        # хвост уходит в паузу, поэтому блок становится длиннее исходного
        y = room(soften(x))
        # Микродинамика ±0.5 дБ по блоку: без неё соседние абзацы звучат
        # одной громкостью, и текст читается как объявление, а не как рассказ.
        y = y * np.float32(10.0 ** ((((i * 37) % 11) - 5) / 40.0))
        e = min(len(voice), cur + len(y))
        voice[cur:e] += y[: e - cur]
        samples.append((cur, cur + len(x)))
        g = tail_gap(text, kind)
        marks.append((cur + len(x) + g, "after_scene" if i in scene_after else kind))
        cur += len(x) + g

    n = cur + int(3.0 * SR)
    voice = voice[:n]

    # подложка: один цикл на всю главу с дакингом по огибающей голоса.
    # При BED_GAIN = 0 не считаем вовсе: тайл на 30 млн отсчётов впустую.
    if BED_GAIN > 0:
        reps = int(np.ceil(n / max(1, len(bed))))
        bedfull = np.tile(bed, reps)[:n]
        env = movavg(np.abs(voice), int(0.05 * SR))
        env = movavg(env, int(0.35 * SR))
        peak = float(np.max(env)) or 1.0
        duck = 1.0 - 0.78 * np.clip(env / peak, 0, 1)
        bed_track = bedfull * duck * BED_GAIN
    else:
        bed_track = np.zeros(1, dtype=np.float32)

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
            # шумовые эффекты на границах сцен убраны: сквозняк и статика
            # читались как «белый шум на фоне». Остались скрип двери и колокол.
            place(whoosh, pos, FX_WHOOSH)
            place(static, pos + int(0.15 * SR), FX_STATIC)
    # финальный аккорд
    place(whoosh, n - int(2.2 * SR), FX_WHOOSH)

    mix = voice * 1.0 + bed_track + fx * 0.8
    mix = compress(mix)                 # плотность как у студийной записи
    mix = mix + studio_air(len(mix))    # паузы перестают быть цифровым нулём
    # мягкий лимитер без поджатия: tanh с коэффициентом >1 добавлял гармоник,
    # а это и есть та самая «металлическая» жёсткость на громких репликах
    mix = np.tanh(mix * 0.85).astype(np.float32)
    mix = norm(mix, 0.92)

    tmp = os.path.join(OUTDIR, stem + ".wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    # Громкость статичной поправкой, а не loudnorm: однопроходный loudnorm
    # в динамическом режиме подкачивает уровень и убивает размах, из-за чего
    # чтение звучит ровно-механически. Считаем LUFS, добавляем ровно дельту,
    # пики держит alimiter.
    gain = LOUD_I - integrated_lufs(tmp)
    lim = 10.0 ** (LOUD_TP / 20.0)
    r = run(["ffmpeg", "-y", "-v", "error", "-i", tmp,
             "-af", f"volume={gain:.2f}dB,alimiter=limit={lim:.4f}:attack=5:release=80:level=disabled",
             "-ar", str(SR), "-ac", "1", "-b:a", "96k", out_path])
    if r.returncode != 0:
        print(r.stderr[-800:], file=sys.stderr)
        sys.exit(1)
    os.remove(tmp)
    dur = len(mix) / SR
    print(f"готово: {out_path}  {dur/60:.1f} мин, {LOUD_I:.0f} LUFS")


if __name__ == "__main__":
    main()
