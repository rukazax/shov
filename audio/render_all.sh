#!/usr/bin/env bash
# Озвучка тома целиком, устойчиво к падениям сервиса синтеза.
# Держит STREAMS потоков по главам, пока каждая дорожка не станет новее метки сборки.
# Метка out/.cast-rebuild = «дорогие mp3, собранные до неё, считаются старыми».
set -u
cd "$(dirname "$0")"
STREAMS=${STREAMS:-8}
export JOBS=${JOBS:-3}
STAMP=out/.cast-rebuild
[ -f "$STAMP" ] || touch "$STAMP"
STAMP_TS=$(stat -c %Y "$STAMP")

fresh() { [ -f "out/$1.mp3" ] && [ "$(stat -c %Y "out/$1.mp3" 2>/dev/null || echo 0)" -gt "$STAMP_TS" ]; }

pending() {
  local n=0
  for f in ../BOOK01/ch*.md; do
    b=$(basename "${f%.md}")
    fresh "$b" || n=$((n+1))
  done
  echo "$n"
}

for round in $(seq 1 40); do
  n=$(pending)
  echo "== круг $round: не собрано глав $n ($(date +%H:%M:%S))"
  [ "$n" -eq 0 ] && { echo "ГОТОВО: все дорожки новее метки"; exit 0; }

  for idx in $(seq 0 $((STREAMS-1))); do
    (
      i=0
      for f in ../BOOK01/ch*.md; do
        b=$(basename "${f%.md}")
        if fresh "$b"; then continue; fi
        if [ $((i % STREAMS)) -ne "$idx" ]; then i=$((i+1)); continue; fi
        i=$((i+1))
        exec 9>"out/$b.lock" || continue
        flock -n 9 || { exec 9>&-; continue; }
        echo "-- $b старт $(date +%H:%M:%S)"
        python3 -u render.py "$f" --jobs "$JOBS" || echo "  ! $b не собрался, вернёмся кругом позже"
        exec 9>&-
      done
    ) &
  done
  wait
  sleep 20
done
echo "ОТКАЗ: за 40 кругов дорожки не собрались"
exit 1
