#!/usr/bin/env bash
# Ждёт, пока все дорожки тома станут новее метки сборки, проверяет их,
# вписывает факты в README (блок между маркерами auto) и заливает том в GitHub.
set -u
cd "$(dirname "$0")"
LOG="$PWD/logs/publish.log"
mkdir -p logs
say() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

BOOK="${BOOK:-BOOK01}"
if [ "$BOOK" = "BOOK01" ]; then
  OUT="${AUDIO_OUT:-out}"
else
  OUT="${AUDIO_OUT:-out$(echo "$BOOK" | sed 's/BOOK0*/-t/')}"
fi
export BOOK OUT
STAMP="$OUT/.cast-rebuild"
DEADLINE=$(( $(date +%s) + 6*3600 ))

count_fresh() {
  local total=0 fresh=0 b
  for f in ../$BOOK/ch*.md; do
    b=$(basename "${f%.md}"); total=$((total+1))
    [ -f "$OUT/$b.mp3" ] && [ "$OUT/$b.mp3" -nt "$STAMP" ] && fresh=$((fresh+1))
  done
  echo "$fresh $total"
}

while :; do
  read -r fresh total <<<"$(count_fresh)"
  say "дорожек готово $fresh из $total"
  [ "$fresh" -eq "$total" ] && break
  if [ "$(date +%s)" -gt "$DEADLINE" ]; then
    say "ОТБОЙ: за 6 часов собрались не все дорожки ($fresh из $total)"
    exit 1
  fi
  sleep 180
done

say "приёмка: check_out.py"
if python3 check_out.py >logs/check-out.txt 2>&1; then say "приёмка ok"; else say "приёмка: расхождения, см. logs/check-out.txt"; fi

say "сбор фактов для README"
# README один на каталог и описывает том 1; для остальных томов факты идут в TRACKS-tN.md
if [ "$BOOK" != "BOOK01" ]; then
  BOOK="$BOOK" python3 tracks.py >>"$LOG" 2>&1 || true
  say "факты тома — в TRACKS-t$(echo "$BOOK" | sed 's/BOOK0*//').md"
else
python3 - "$STAMP" <<'PY' >>"$LOG" 2>&1
import glob, json, os, subprocess, sys

stamp = float(os.stat(sys.argv[1]).st_mtime)
BOOK, OUT = os.environ["BOOK"], os.environ["OUT"]
files = sorted(f for f in glob.glob(f"../{BOOK}/ch*.md") if os.path.exists(OUT + "/" + os.path.basename(f)[:-3] + ".mp3"))
dur = size = 0.0
lufs = []
for md in files:
    mp3 = OUT + "/" + os.path.basename(md)[:-3] + ".mp3"
    d = float(subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                              "-of", "csv=p=0", mp3], capture_output=True, text=True).stdout.strip() or 0)
    dur += d
    size += os.path.getsize(mp3)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mp3,
                          "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("I:"):
            try: lufs.append(float(s.split()[1]))
            except ValueError: pass

hours, mins = divmod(round(dur / 60), 60)
block = (
    "<!-- auto:start -->\n"
    "## Собранный том\n\n"
    f"- дорожек: {len(files)}, общая длительность {hours} ч {mins} мин, {size / 1e6:.0f} МБ\n"
    f"- громкость: {min(lufs):.1f} … {max(lufs):.1f} LUFS, моно 44,1 кГц, 96 кбит/с\n"
    "- приёмка: `check_out.py` (длительность против объёма текста), лог `logs/check-out.txt`\n"
    "<!-- auto:end -->\n"
)
readme = open("README.md", encoding="utf-8").read()
if "<!-- auto:start -->" in readme:
    head, rest = readme.split("<!-- auto:start -->", 1)
    tail = rest.split("<!-- auto:end -->", 1)[1]
    readme = head + block + tail
else:
    readme = readme.rstrip() + "\n\n" + block
open("README.md", "w", encoding="utf-8").write(readme)
print(f"вписано в README: {len(files)} дорожек, {hours} ч {mins} мин, {size / 2**20:.0f} МБ, LUFS {min(lufs):.1f}…{max(lufs):.1f}")
PY
fi

cd ..
say "git: коммит и push"
git add -A >>"$LOG" 2>&1
if git diff --cached --quiet; then
  say "нечего коммитить"
else
  git commit -q -m "audio: том озвучен целиком — многоголосый каст, приёмка дорожек, факты в README" >>"$LOG" 2>&1
  say "коммит: $(git log --oneline -1)"
fi
if . /etc/dsh/dsh-github.env 2>/dev/null && [ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
  if git push "https://x-access-token:${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/rukazax/shov.git" main >>"$LOG" 2>&1; then
    say "push ok: $(git log --oneline -1)"
    touch audio/logs/published.ok
  else
    say "PUSH НЕ ПРОШЁЛ, см. $LOG"
    exit 1
  fi
else
  say "нет токена GitHub"
  exit 1
fi
