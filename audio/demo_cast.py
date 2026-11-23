#!/usr/bin/env python3
"""Тестовый фрагмент «Шова»: несколько голосов и интонаций.

Собирает дорожку из одной и той же рукописи двумя движками — для сравнения:

    python3 demo_cast.py --engine teratts      # новый: 4 тембра TeraTTSv2
    python3 demo_cast.py --engine edge         # прежний: 2 голоса edge-tts

Просодия от знаков берётся из render.prosody(): из неё вычитается базовая
манера роли edge-tts, остаются только дельты от пунктуации (вопрос выше,
`!` громче, `…` медленнее, микродвижение по тексту) — их и получает TeraTTS.

Фрагмент: витрина голосов, витрина интонаций, две сцены из первой главы.
Сведение — тем же трактом, что у книги: soften → room → микродинамика →
compress → воздух → лимитер → −20 LUFS.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render  # noqa: E402
import teratts_engine as te  # noqa: E402

SR = render.SR
OUT = os.path.join(HERE, "out-demo")

# role, kind, emotion, text. Ремарки вынесены рассказчику: персонаж читает
# только свою реплику — это то, чего в render.py пока нет (см. отчёт).
SCRIPT = [
    # --- витрина голосов ------------------------------------------------
    ("narrator", "narration", "calm",
     "Их четверо. Низкий мужской, светлый мужской, взрослый женский и молодой женский. "
     "Плюс системный голос — не человек. Слушай."),
    ("hero", "dialogue", "calm", "Сгодится."),
    ("babka", "dialogue", "tense", "Где Кузьма?"),
    ("vitya", "dialogue", "tired", "Я пас."),
    ("dasha", "dialogue", "joy", "Пап, а у нас в садике лифт есть!"),
    ("female", "dialogue", "calm", "А вы кто?"),
    ("narrator", "narration", "calm",
     "Над городом висела полоса. Она там висела всегда, сколько я себя помню."),
    ("system", "system", "calm",
     "Согласование: замер невозможен. Пост не отвечает. Метка: не обнаружена."),
    # --- витрина интонаций ----------------------------------------------
    ("narrator", "narration", "calm",
     "Одна и та же реплика, шесть раз: спокойно, тревожно, зло, устало, шёпотом и криком."),
    ("babka", "dialogue", "calm", "Он мяукает. Я слышу. Оттуда слышу, с улицы."),
    ("babka", "dialogue", "tense", "Он мяукает. Я слышу. Оттуда слышу, с улицы."),
    ("babka", "dialogue", "angry", "Он мяукает. Я слышу. Оттуда слышу, с улицы."),
    ("babka", "dialogue", "tired", "Он мяукает. Я слышу. Оттуда слышу, с улицы."),
    ("babka", "dialogue", "whisper", "Он мяукает. Я слышу. Оттуда слышу, с улицы."),
    ("babka", "dialogue", "shout", "Он мяукает! Я слышу! Оттуда слышу, с улицы!"),
    # --- сцена «Кузьма» (глава 1, блоки 79–101) -------------------------
    ("babka", "dialogue", "tense", "Кузьма?"),
    ("narrator", "narration", "calm", "Сказала бабушка, ещё не дав мне снять куртку."),
    ("hero", "dialogue", "calm", "Чего Кузьма?"),
    ("babka", "dialogue", "tense", "Где Кузьма?"),
    ("hero", "dialogue", "tired", "Не знаю. Я с работы."),
    ("babka", "dialogue", "tense",
     "Он третий день не приходит. Третий, Сеня. Кузьма домой не ходит, "
     "а он ходит всегда, даже когда его гонят."),
    ("narrator", "narration", "calm", "Бабушка посмотрела на меня строго."),
    ("hero", "dialogue", "calm", "Бабушка, он кот. Коты гуляют."),
    ("babka", "dialogue", "tense", "Он не гуляет. Он там."),
    ("hero", "dialogue", "tense", "Где «там»?"),
    ("babka", "dialogue", "calm", "В шахте."),
    ("narrator", "narration", "calm", "Я подождал, не пошутит ли она. Она не шутила."),
    ("babka", "dialogue", "tense",
     "Он мяукает. Я слышу. Оттуда слышу, с улицы. У меня слух хороший, ты знаешь."),
    ("hero", "dialogue", "tired", "И что ты хочешь?"),
    ("babka", "dialogue", "calm", "Достань."),
    ("hero", "dialogue", "calm", "Там нет лифта."),
    ("babka", "dialogue", "angry", "А на что ты мастер?"),
    ("hero", "dialogue", "calm",
     "Бабушка, туда нельзя. Шахта заброшена двадцать лет, там ствол осыпается, там…"),
    ("babka", "dialogue", "calm", "Там клеть. Она работает. Люди ездят."),
    ("hero", "dialogue", "tense", "Какие люди?"),
    ("babka", "dialogue", "tired", "Разные."),
    # --- звонок Вите (блоки 111–139) ------------------------------------
    ("babka", "dialogue", "tense",
     "Сеня. Звони Вите. Витя неплохой, он в темноте не боится."),
    ("hero", "dialogue", "calm", "Витя боится высоты."),
    ("babka", "dialogue", "calm",
     "Темноты не боится. Высота — это в голове. Ты ему скажи, что мы не на высоте, мы внизу."),
    ("hero", "dialogue", "tense", "Генка. Шахта. Завтра."),
    ("vitya", "dialogue", "tired", "Я пас."),
    ("hero", "dialogue", "tense", "Там кот."),
    ("vitya", "dialogue", "calm", "Пусть мчинские достают."),
    ("hero", "dialogue", "tense", "Какие?"),
    ("vitya", "dialogue", "calm",
     "Ну, которые на «Капитальной» живут. Там, на объездной, всегда кто-то живёт, ты не знал?"),
    ("hero", "dialogue", "tired", "Не знал. Честно — не знал."),
    ("vitya", "dialogue", "calm", "Да разные. Бомжи. Может, кто из шахтёров остался."),
    ("hero", "dialogue", "calm", "Сторожка? У заброшенной шахты?"),
    ("vitya", "dialogue", "calm", "Ну."),
    ("vitya", "dialogue", "calm",
     "Ладно. В шесть. Я с фонариком. Но если там будет что-то странное — "
     "я не снимаю, я разворачиваюсь."),
]

EMO_GAP = {"calm": 0.0, "tense": -0.04, "angry": -0.03, "joy": -0.02,
           "tired": 0.10, "sad": 0.12, "whisper": 0.06, "shout": -0.02}


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, path
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return a.astype(np.float32) / 32768.0


def synth_block(engine, role, kind, emo, text):
    spec = render.prosody(kind, text, role)
    if engine == "teratts":
        base = render.VOICES[role]
        d_rate = int(spec["rate"].rstrip("%")) - int(base["rate"].rstrip("%"))
        d_pitch = int(spec["pitch"].rstrip("Hz")) - int(base["pitch"].rstrip("Hz"))
        return read_wav(te.synth(text, role, rate=d_rate, pitch=d_pitch,
                                 emotion=emo, kind=kind))
    clean = render.cleanup_for_tts(text)
    path = os.path.join(render.CACHE, render.cache_key(spec, clean) + ".mp3")
    if not (os.path.exists(path) and os.path.getsize(path) > 500):
        ok = asyncio.run(render.synth_one(clean, spec, path))
        if not ok:
            raise RuntimeError(f"edge-tts не отдал звук: {text[:60]}")
    return render.decode_any(path)


def assemble(items):
    """Таймлайн и сведение — тем же трактом, что у книги."""
    chime = render.sess("chime.wav")
    gap_n, gap_d = int(0.34 * SR), int(0.22 * SR)
    cur = int(0.7 * SR)
    placed = []
    for i, it in enumerate(items):
        x = it["x"]
        if it["kind"] == "system":
            placed.append((cur, chime * np.float32(0.35), "fx"))
            cur += int(0.55 * SR)
        y = render.room(render.soften(x))
        y = y * np.float32(10.0 ** ((((i * 37) % 11) - 5) / 40.0))
        placed.append((cur, y, "voice"))
        g = render.tail_gap(it["text"], it["kind"]) + int(EMO_GAP[it["emo"]] * SR)
        cur += len(x) + max(g, int(0.12 * SR))
    n = cur + int(2.5 * SR)
    voice = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    for pos, y, kind in placed:
        e = min(n, pos + len(y))
        if kind == "voice":
            voice[pos:e] += y[: e - pos]
        else:
            fx[pos:e] += y[: e - pos]
    mix = voice + fx * 0.8
    mix = render.compress(mix)
    mix = mix + render.studio_air(len(mix))
    mix = np.tanh(mix * 0.85).astype(np.float32)
    mix = render.norm(mix, 0.92)
    return mix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["teratts", "edge"], default="teratts")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--dump-blocks", metavar="DIR",
                    help="писать каждый блок до сведения: для замера WER и f0")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    out = args.out or os.path.join(OUT, f"demo-{args.engine}.mp3")

    t0 = time.time()
    items, audio_s = [], 0.0
    for i, (role, kind, emo, text) in enumerate(SCRIPT):
        x = synth_block(args.engine, role, kind, emo, text)
        if kind == "system" and args.engine == "teratts":
            x = render.robotize(x)
        if kind == "system" and args.engine == "edge":
            x = render.robotize(x)
        audio_s += len(x) / SR
        items.append({"role": role, "kind": kind, "emo": emo, "text": text, "x": x})
        if args.dump_blocks:
            os.makedirs(args.dump_blocks, exist_ok=True)
            with wave.open(os.path.join(args.dump_blocks, f"{i:02d}_{role}.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SR)
                w.writeframes((x * 32767).astype("<i2").tobytes())
        print(f"  {i:2d} {role:8s} {emo:7s} {len(x) / SR:5.2f} с  {text[:48]}",
              file=sys.stderr, flush=True)
    print(f"синтез: {time.time() - t0:.0f} с на {audio_s:.0f} с речи "
          f"(RTF {(time.time() - t0) / max(audio_s, 1):.2f})", file=sys.stderr)

    mix = assemble(items)
    tmp = os.path.join(OUT, f"demo-{args.engine}.wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())

    gain = render.LOUD_I - render.integrated_lufs(tmp)
    lim = 10.0 ** (render.LOUD_TP / 20.0)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp,
                        "-af", f"volume={gain:.2f}dB,alimiter=limit={lim:.4f}:"
                               f"attack=5:release=80:level=disabled",
                        "-ar", str(SR), "-ac", "1", "-b:a", "96k", out])
    if r.returncode:
        print(r.stderr[-600:], file=sys.stderr)
        sys.exit(1)
    os.remove(tmp)

    dur = len(mix) / SR
    lufs = render.integrated_lufs(out)
    print(f"готово: {out}  {dur / 60:.2f} мин  {lufs:.1f} LUFS  "
          f"{os.path.getsize(out) / 1e6:.1f} МБ")
    json.dump({"engine": args.engine, "file": out, "duration_s": round(dur, 1),
               "lufs": round(lufs, 1), "blocks": len(items),
               "synth_s": round(time.time() - t0, 1), "speech_s": round(audio_s, 1)},
              open(os.path.join(OUT, f"report-{args.engine}.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
