#!/usr/bin/env bash
# Ждать, пока у тома WAIT_VOL не соберутся все дорожки, затем поднять рендер NEXT_VOL.
# WAIT_VOL=4 NEXT_VOL=5 UNITS=6 ./render_chain3.sh   (из root-контекста: systemd-run --uid=ka)
set -u
cd "$(dirname "$0")/.."
WAIT_VOL="${WAIT_VOL:?}"; NEXT_VOL="${NEXT_VOL:?}"; UNITS="${UNITS:-6}"
LOG=audio/logs/render-chain.log
say() { printf '%s %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

want=$(ls BOOK0*/ch*.md 2>/dev/null | sed 's|/[^/]*$||' | sort -u | while read d; do echo "$d"; done >/dev/null; echo 34)
say "ждём 34 дорожки тома $WAIT_VOL"
while :; do
  n=$(ls "audio/out-t$WAIT_VOL"/*.mp3 2>/dev/null | wc -l)
  [ "$n" -ge 34 ] && break
  sleep 120
done
say "том $WAIT_VOL собран ($n дорожек); поднимаю $UNITS потоков на том $NEXT_VOL"

for i in $(seq 1 "$UNITS"); do
  u="shov-render-t${NEXT_VOL}-${i}"
  touch "audio/logs/render-${u}.log"; chown ka:ka "audio/logs/render-${u}.log"
  systemd-run --unit="$u" --collect --property=User=ka --property=Group=ka \
    --property=Environment=HOME=/home/ka --property=MemoryMax=3G --property=MemoryHigh=2.5G \
    --setenv=BOOK="BOOK0${NEXT_VOL}" --setenv=STREAMS=1 --setenv=JOBS=4 \
    --working-directory="$PWD/audio" \
    /usr/bin/bash -c "./render_all.sh >> logs/render-${u}.log 2>&1" >/dev/null 2>&1
  say "поднят $u"
done
say "очередь на том $NEXT_VOL поставлена"
