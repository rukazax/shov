#!/usr/bin/env python3
"""Приёмка готовых дорожек: длительность против объёма текста.

Темп не берётся константой: он считается по медиане готовых дорожек, потому что
паузы между блоками и сценами зависят от главы. Так проверка ловит именно
выпавшие куски, а не разницу в темпе.
"""
import glob
import os
BOOK = os.environ.get("BOOK", "BOOK01")
OUT = os.environ.get("AUDIO_OUT", "out")
import os
import statistics
import subprocess

TOL = 0.12  # допуск на расхождение с медианным темпом


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    return float(out or 0)


rows = []
for f in sorted(glob.glob(f"../{BOOK}/ch*.md")):
    stem = os.path.splitext(os.path.basename(f))[0]
    mp3 = f"{OUT}/{stem}.mp3"
    chars = len(open(f, encoding="utf-8").read())
    if not os.path.exists(mp3):
        rows.append((stem, chars, None, None))
        continue
    d = duration(mp3)
    rows.append((stem, chars, d / 60, chars / d if d else 0))

ready = [(stem, chars, mins, rate) for stem, chars, mins, rate in rows if mins]
if not ready:
    raise SystemExit("нет дорожек")

med = statistics.median(r[3] for r in ready)
bad = 0
for stem, chars, mins, rate in rows:
    if not mins:
        print(f"{stem:20s} {'—':>24s} нет дорожки")
        bad += 1
        continue
    want = chars / med / 60
    dev = (mins - want) / want
    ok = abs(dev) < TOL
    bad += 0 if ok else 1
    print(f"{stem:20s} {mins:6.1f} мин (ждали {want:5.1f}, {dev*100:+5.1f}%) {'' if ok else 'РАСХОЖДЕНИЕ'}")

print(f"\nдорожек: {len(ready)}, медианный темп: {med:.1f} зн/с, расхождений: {bad}")
