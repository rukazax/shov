#!/usr/bin/env bash
# Собирает дистрибутив для читателей: EPUB + единый markdown.
# Запускать после правок глав; метаданные и обложка берутся из assets/.
set -eu
cd "$(dirname "$0")"

python3 build_book.py >/dev/null
mkdir -p ../dist

pandoc SHOV-tom8.md \
  -o ../dist/shov-tom8.epub \
  --toc --toc-depth=1 --split-level=1 \
  --metadata title="Шов. Книга восьмая: Орбита" \
  --metadata author="Константин Ерёмин" \
  --metadata lang=ru-RU \
  --metadata date="2026-11-23" \
  --epub-cover-image=../assets/cover-tom8.png

cp SHOV-tom8.md ../dist/shov-tom8.md
ls -lh ../dist
