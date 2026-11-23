#!/usr/bin/env bash
# Публикация текстовой части тома: гейты → сборка → EPUB → коммит → пуш → релиз vN.0.
# Запуск:  VOL=3 ./scripts/publish_volume.sh
# Звук публикуется отдельно (release vN.1), см. publish_audio.sh.
set -eu
cd "$(dirname "$0")/.."

VOL="${VOL:?укажи VOL=N}"
[ "$VOL" -ge 1 ] || { echo "VOL должен быть ≥ 1"; exit 1; }
N=$(printf '%02d' "$VOL")
BOOK="BOOK$N"
[ -d "$BOOK" ] || { echo "нет каталога $BOOK"; exit 1; }

say() { printf '\n== %s\n' "$*"; }

say "гейты тома $VOL"
if ! "$BOOK/gate.sh" >"logs/gate-t$VOL.txt" 2>&1; then
  tail -30 "logs/gate-t$VOL.txt"
  echo "ГЕЙТЫ НЕ ПРОЙДЕНЫ — смотри logs/gate-t$VOL.txt"
  exit 1
fi
grep -E '^ГЕЙТЫ|^ИТОГО' "logs/gate-t$VOL.txt" || true

say "сборка"
python3 "$BOOK/build_book.py" | tail -6

say "EPUB"
"$BOOK/build_epub.sh" | tail -4
unzip -l "dist/shov-tom$VOL.epub" | grep -E 'cover|\.png' | head -3

say "git"
git add -A
git diff --cached --quiet && echo "нечего коммитить" || {
  git commit -q -m "Том $VOL: главы, библия, брифы, обложка, EPUB-сборка"
  git log --oneline -1
}
set -a; . /etc/dsh/dsh-github.env; set +a
git push "https://x-access-token:${GITHUB_PERSONAL_ACCESS_TOKEN}@github.com/rukazax/shov.git" main:main 2>&1 | tail -2

say "релиз v$VOL.0"
TAG="v$VOL.0"
BODY=$(cat "logs/release-t$VOL.md" 2>/dev/null || echo "Том $VOL.")
RID=$(python3 - "$TAG" "$BODY" <<'PY'
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
rel = api("/repos/rukazax/shov/releases", {"tag_name": tag, "name": f"Том {tag[1:-2]} — текст, EPUB, обложка", "body": body})
print(rel["id"])
PY
)
echo "release id: $RID"
for pair in "dist/shov-tom$VOL.epub:shov-tom$VOL.epub" "dist/shov-tom$VOL.md:shov-tom$VOL.md" "assets/cover-tom$VOL.png:cover-tom$VOL.png"; do
  f="${pair%%:*}"; name="${pair##*:}"
  [ -f "$f" ] || { echo "нет $f — пропускаю"; continue; }
  code=$(curl -sS -o /tmp/up.json -w '%{http_code}' -X POST \
    -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "@$f" \
    "https://uploads.github.com/repos/rukazax/shov/releases/$RID/assets?name=$name")
  echo "  $name → $code"
done

say "проверка ассетов"
curl -sS -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  "https://api.github.com/repos/rukazax/shov/releases/$RID/assets" |
  python3 -c "import sys,json; [print(' ', a['name'], a['size'], a['state']) for a in json.load(sys.stdin)]"
