#!/usr/bin/env bash
# Очередь рендера томов: дождаться, пока не останется ни одного юнита shov-render-<PREFIX>,
# затем поднять N юнитов для следующего тома. Запускать из root-контекста (systemd-run --uid=ka).
# Переменные: WAIT_PREFIX=shov-render-t3 NEXT_BOOK=BOOK04 STREAMS_UNITS=6
set -u
cd "$(dirname "$0")/.."
WAIT_PREFIX="${WAIT_PREFIX:?}"
NEXT_BOOK="${NEXT_BOOK:?}"
UNITS="${STREAMS_UNITS:-6}"
LOG=audio/logs/render-chain.log
say() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

say "ждём, пока погаснут юниты ${WAIT_PREFIX}*"
while systemctl list-units --no-legend --plain "${WAIT_PREFIX}*" 2>/dev/null | grep -q .; do sleep 60; done
say "все ${WAIT_PREFIX}* закончили; поднимаю $UNITS потоков на $NEXT_BOOK"

for i in $(seq 1 "$UNITS"); do
  u="shov-render-$(echo "$NEXT_BOOK" | sed 's/BOOK0*/-t/')${i}"
  touch "audio/logs/render-${u}.log"; chown ka:ka "audio/logs/render-${u}.log"
  systemd-run --unit="$u" --collect --property=User=ka --property=Group=ka \
    --property=Environment=HOME=/home/ka --property=MemoryMax=3G --property=MemoryHigh=2.5G \
    --setenv=BOOK="$NEXT_BOOK" --setenv=STREAMS=1 --setenv=JOBS=4 \
    --working-directory="$PWD/audio" \
    /usr/bin/bash -c "./render_all.sh >> logs/render-${u}.log 2>&1" >/dev/null 2>&1
  say "поднят $u"
done
say "очередь на $NEXT_BOOK поставлена"
