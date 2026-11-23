#!/usr/bin/env bash
# Публикация звука тома: zip дорожек → релиз vN.1 с нотами → проверка ассетов.
# Запуск: VOL=3 ./scripts/publish_audio.sh
# Требует уже собранные дорожки в audio/out-tN/ (см. audio/render_all.sh).
set -eu
cd "$(dirname "$0")/.."

VOL="${VOL:?укажи VOL=N}"
N=$(printf '%02d' "$VOL")
OUT="audio/out-t$VOL"
[ -d "$OUT" ] || { echo "нет каталога $OUT"; exit 1; }

say() { printf '\n== %s\n' "$*"; }

say "дорожки тома $VOL"
ls "$OUT"/*.mp3 | wc -l
day=$(ls "$OUT"/*.mp3 | wc -l)
hours=$(python3 - "$OUT" <<'PY'
import glob, os, subprocess, sys
d = 0.0
for f in glob.glob(sys.argv[1] + "/*.mp3"):
    d += float(subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                               "-of","csv=p=0", f], capture_output=True, text=True).stdout.strip() or 0)
print(f"{d/3600:.1f} {sum(os.path.getsize(f) for f in glob.glob(sys.argv[1] + '/*.mp3'))/2**20:.0f}")
PY
)
echo "длительность/вес: $hours"

say "zip"
ZIP="dist/shov-tom$VOL-audio.zip"
mkdir -p dist
rm -f "$ZIP"
(cd "$OUT" && zip -q -9 "../../$ZIP" ./*.mp3)
ls -lh "$ZIP"

say "релиз v$VOL.1"
set -a; . /etc/dsh/dsh-github.env; set +a
TAG="v$VOL.1"
BODY=$(cat "logs/release-audio-t$VOL.md" 2>/dev/null || echo "Аудиоверсия тома $VOL.")
RID=$(python3 - "$TAG" "$BODY" <<'PYEOF'
import json, os, sys, urllib.request
tag, body = sys.argv[1], sys.argv[2]
tok = os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"]
def api(path, data=None, method=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json"},
        method=method or ("POST" if data else "GET"))
    return json.load(urllib.request.urlopen(req))
exist = [r for r in api("/repos/rukazax/shov/releases") if r["tag_name"] == tag]
if exist:
    print(exist[0]["id"]); raise SystemExit
rel = api("/repos/rukazax/shov/releases", {"tag_name": tag,
          "name": f"Том {tag[1:-2]} — аудио", "body": body})
print(rel["id"])
PYEOF
)
echo "release id: $RID"

code=$(curl -sS -o /tmp/up-audio.json -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@$ZIP" \
  "https://uploads.github.com/repos/rukazax/shov/releases/$RID/assets?name=$(basename "$ZIP")")
echo "  $(basename "$ZIP") → $code"

say "проверка ассетов"
curl -sS -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  "https://api.github.com/repos/rukazax/shov/releases/$RID/assets" |
  python3 -c "import sys,json; [print(' ', a['name'], a['size'], a['state']) for a in json.load(sys.stdin)]"
