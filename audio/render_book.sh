#!/usr/bin/env bash
# Рендерит все главы, у которых md новее готового mp3. Идемпотентно.
set -u
cd "$(dirname "$0")"
fail=0
for f in ../BOOK01/ch*.md; do
  b=$(basename "$f" .md)
  out="out/$b.mp3"
  if [ -f "$out" ] && [ "$out" -nt "$f" ]; then continue; fi
  echo "== $b"
  python3 render.py "$f" || { echo "FAIL $b"; fail=1; }
done
echo "готово, fail=$fail"
