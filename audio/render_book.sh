#!/usr/bin/env bash
# usage: ./render_book.sh FROM TO   (номера глав включительно)
# Каждая глава рендерится под flock, чтобы параллельные воркеры не мешали друг другу.
set -u
cd "$(dirname "$0")"
FROM=${1:-0}; TO=${2:-99}
JOBS=${JOBS:-4}   # больше 6 параллельных запросов edge-tts начинает троттлить
for f in ../BOOK01/ch*.md; do
  b=$(basename "$f" .md)
  n=$(printf '%s' "$b" | grep -o '[0-9]\+' | head -1); n=${n:-0}
  [ "$n" -ge "$FROM" ] && [ "$n" -le "$TO" ] || continue
  out="out/$b.mp3"
  [ -f "$out" ] && [ "$out" -nt "$f" ] && [ -z "${FORCE:-}" ] && continue
  (
    flock -n 9 || { echo "занято: $b"; exit 0; }
    [ -f "$out" ] && [ "$out" -nt "$f" ] && [ -z "${FORCE:-}" ] && exit 0
    echo "== $b"
    # Глава не собралась (сервис синтеза молчал волной) — пауза и ещё заход.
    # Кэш блоков делает повтор дешёвым: синтезируется только недостающее.
    for try in 1 2 3 4 5 6; do
      if python3 render.py "$f" --jobs "$JOBS"; then break; fi
      echo "  $b: заход $try не собрался, пауза 120 с"
      sleep 120
    done
  ) 9>"out/$b.lock"
done
echo "воркер $FROM-$TO готов"
