#!/usr/bin/env bash
# Финиш звука тома без дежурства: дождаться дорожек → приёмка → коммит/пуш →
# ноты релиза по замеру → релиз vN.1 с zip.
# Запуск: VOL=3 ./scripts/finish_volume_audio.sh
# Долгий (часы), поэтому в systemd: см. scripts/README-audio.md.
set -u
cd "$(dirname "$0")/.."
VOL="${VOL:?укажи VOL=N}"
say() { printf '\n== %s\n' "$*"; }

say "ждать дорожки тома $VOL"
BOOK="BOOK$(printf '%02d' "$VOL")" ./audio/publish_when_done.sh || { echo "дорого не собрались"; exit 1; }

say "ноты релиза по замеру"
BOOK="$BOOK" VOL="$VOL" python3 - <<'PYEOF'
import glob, os, subprocess
BOOK, VOL = os.environ["BOOK"], os.environ["VOL"]
OUT = f"audio/out-t{VOL}"
mp3s = sorted(glob.glob(OUT + "/*.mp3"))
dur = size = 0.0
lufs = []
for f in mp3s:
    dur += float(subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                                 "-of","csv=p=0", f], capture_output=True, text=True).stdout.strip() or 0)
    size += os.path.getsize(f)
    err = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",f,"-af","ebur128","-f","null","-"],
                         capture_output=True, text=True).stderr
    for line in err.splitlines():
        s = line.strip()
        if s.startswith("I:"):
            try: lufs.append(float(s.split()[1]))
            except ValueError: pass
h, m = divmod(round(dur / 60), 60)
titles = {"1": ("Щепка", "v1.0"), "2": ("Ходок", "v2.0"), "3": ("Мост", "v3.0")}
name, text_tag = titles.get(VOL, (f"том {VOL}", ""))
body = f"""**Аудиоверсия тома {VOL} «{name}»: {len(mp3s)} дорожек, {h} ч {m:02d} мин, {size/2**20:.0f} МБ.**

| | |
|---|---|
| Дорожек | {len(mp3s)} (Введение + главы), отдельные mp3 |
| Звучание | {h} ч {m:02d} мин, {size/2**20:.0f} МБ |
| Громкость | {min(lufs):.1f}…{max(lufs):.1f} LUFS, моно 44,1 кГц, 96 кбит/с |
| Каст | два русских тембра, роли различает темп и тон; разметка ролей выверена по главам |

**Что сделано с голосами.** Разметку «кто говорит» проверили по всем 34 главам: `cast_audit.py` + сплошная сверка с текстом. Нашлось и исправлено около двух тысяч реплик, где эвристика ставила не того: герой вместо Кержака, начальница голосом старухи, двойник на голосе Вити. Седьмой в ведомости говорит тем же голосом, что человек в форме, — это не ошибка, а подсказка.

**Текст тома** — в релизе {text_tag}.
"""
open(f"logs/release-audio-t{VOL}.md","w",encoding="utf-8").write(body)
print(body[:300])
PYEOF

say "релиз"
VOL="$VOL" ./scripts/publish_audio.sh
