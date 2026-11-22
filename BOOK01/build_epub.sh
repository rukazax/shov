#!/usr/bin/env bash
# Собирает дистрибутив для читателей: EPUB + единый markdown.
# Запускать после правок глав; метаданные и обложка берутся из assets/.
set -eu
cd "$(dirname "$0")"

python3 build_book.py >/dev/null
mkdir -p ../dist

pandoc SHOV-tom1.md \
  -o ../dist/shov-tom1.epub \
  --toc --toc-depth=1 --split-level=1 \
  --metadata title="Шов. Книга первая: Щепка" \
  --metadata author="Константин Ерёмин" \
  --metadata lang=ru-RU \
  --metadata date="2026-11-22" \
  --epub-cover-image=../assets/cover-tom1.png

cp SHOV-tom1.md ../dist/shov-tom1.md
ls -lh ../dist
