#!/usr/bin/env bash
# Собирает дистрибутив для читателей: EPUB + единый markdown.
# Запускать после правок глав; метаданные и обложка берутся из assets/.
set -eu
cd "$(dirname "$0")"

python3 build_book.py >/dev/null
mkdir -p ../dist

pandoc SHOV-tom9.md \
  -o ../dist/shov-tom9.epub \
  --toc --toc-depth=1 --split-level=1 \
  --metadata title="Шов. Книга девятая: Трос" \
  --metadata author="Константин Ерёмин" \
  --metadata lang=ru-RU \
  --metadata date="2026-11-23" \
  --epub-cover-image=../assets/cover-tom9.png

cp SHOV-tom9.md ../dist/shov-tom9.md
ls -lh ../dist
