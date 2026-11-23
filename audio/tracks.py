#!/usr/bin/env python3
"""Собирает TRACKS.md: что озвучено, сколько звучит, где лежит."""
import glob, os, subprocess

BOOK = os.environ.get("BOOK", "BOOK01")
OUT = os.environ.get("AUDIO_OUT", "out")
TITLE = {"BOOK01": "1 «Щепка»", "BOOK02": "2 «Ходок»", "BOOK03": "3 «Мост»"}.get(BOOK, BOOK)

rows = []
OUTFILE = 'TRACKS.md' if BOOK == 'BOOK01' else 'TRACKS-' + BOOK[-2:].lstrip('0') + '.md'

for mp3 in sorted(glob.glob(f'{OUT}/ch*.mp3')):
    stem = os.path.splitext(os.path.basename(mp3))[0]
    md = f'../{BOOK}/{stem}.md'
    title = open(md, encoding='utf-8').readline().lstrip('# ').strip() if os.path.exists(md) else stem
    d = float(subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                              '-of', 'csv=p=0', mp3], capture_output=True, text=True).stdout.strip() or 0)
    mb = os.path.getsize(mp3) / 1e6
    rows.append((stem, title, d / 60, mb))

total = sum(r[2] for r in rows)
size = sum(r[3] for r in rows)
with open(OUTFILE, 'w', encoding='utf-8') as f:
    f.write(f'# Аудиоверсия тома {TITLE}\n\n')
    f.write(f'Дорожек: {len(rows)}. Всего звучания: {total/60:.1f} ч. Объём: {size:.0f} МБ.\n\n')
    f.write('| # | Дорожка | Время | Файл |\n|---|---|---|---|\n')
    for i, (stem, title, d, mb) in enumerate(rows, start=1):
        f.write(f'| {i} | {title} | {int(d)} мин | `{OUT}/{stem}.mp3` |\n')
print(f'дорожек {len(rows)}, {total/60:.1f} ч, {size:.0f} МБ')
