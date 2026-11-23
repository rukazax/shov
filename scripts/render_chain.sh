#!/usr/bin/env bash
# Очередь рендера: дождаться конца тома A, потом собрать том B.
# Один том в памяти за раз — 15 ГБ хватает только на один (23.11 OOM на трёх потоках).
set -u
cd "$(dirname "$0")/.."
A_UNIT="${A_UNIT:-shov-render-t3}"
BOOK_NEXT="${BOOK_NEXT:-BOOK04}"
LOG=audio/logs/render-chain.log
say() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

say "ждём юнит $A_UNIT"
while systemctl is-active --quiet "$A_UNIT"; do sleep 60; done
say "$A_UNIT закончил, стартует $BOOK_NEXT"

cd audio
BOOK="$BOOK_NEXT" STREAMS=2 JOBS=2 ./render_all.sh >> "logs/render-${BOOK_NEXT}.log" 2>&1
rc=$?
say "$BOOK_NEXT рендер вышел с кодом $rc"
exit $rc
