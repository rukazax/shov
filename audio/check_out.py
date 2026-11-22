#!/usr/bin/env python3
"""Проверка готовых глав: длительность против ожидаемой по объёму текста."""
import glob, os, subprocess

RATE = 720 / 60  # знаков в секунду, замерено на введении
rows, bad = [], 0
for f in sorted(glob.glob('../BOOK01/ch*.md')):
    stem = os.path.splitext(os.path.basename(f))[0]
    mp3 = f'out/{stem}.mp3'
    if not os.path.exists(mp3):
        rows.append((stem, None, None, 'нет'))
        continue
    d = float(subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                              '-of', 'csv=p=0', mp3], capture_output=True, text=True).stdout.strip())
    chars = len(open(f, encoding='utf-8').read())
    want = chars / RATE / 60
    ok = abs(d / 60 - want) / want < 0.12
    bad += 0 if ok else 1
    rows.append((stem, d / 60, want, 'ok' if ok else 'РАСХОЖДЕНИЕ'))
for stem, got, want, verdict in rows:
    flag = '' if got is None else f'{got:6.1f} мин (ждали {want:5.1f})'
    print(f'{stem:20s} {flag:24s} {verdict}')
print(f'\nрасхождений: {bad}')
