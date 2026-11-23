#!/usr/bin/env bash
# Озвучка тома целиком, устойчиво к падениям сервиса синтеза.
# Держит STREAMS потоков по главам, пока каждая дорожка не станет новее метки сборки.
# Метка out/.cast-rebuild = «дорогие mp3, собранные до неё, считаются старыми».
set -u
BOOK="${BOOK:-BOOK01}"
cd "$(dirname "$0")"
STREAMS=${STREAMS:-8}
export JOBS=${JOBS:-3}
STAMP=out/.cast-rebuild
[ -f "$STAMP" ] || touch "$STAMP"
STAMP_TS=$(stat -c %Y "$STAMP")

fresh() { [ -f "out/$1.mp3" ] && [ "$(stat -c %Y "out/$1.mp3" 2>/dev/null || echo 0)" -gt "$STAMP_TS" ]; }

pending() {
  local n=0
  for f in ../$BOOK/ch*.md; do
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
      # порядок строго по номеру главы: свободный поток берёт САМУЮ МЛАДШУЮ
      # несобранную дорожку (занятые пропускаем по flock), а не «свою» по остатку
      for f in ../$BOOK/ch*.md; do
        b=$(basename "${f%.md}")
        if fresh "$b"; then continue; fi
        exec 9>"out/$b.lock" || continue
        flock -n 9 || { exec 9>&-; continue; }
        echo "-- $b старт $(date +%H:%M:%S)"
        # упавшая глава не паркуется до конца круга (а круг — это вся книга):
        # три захода подряд, потом отпускаем, и её подхватит первый свободный поток
        for try in 1 2 3; do
          python3 -u render.py "$f" --jobs "$JOBS" && break
          echo "  ! $b не собрался, заход $try/3, пауза 20 с"
          [ "$try" -lt 3 ] && sleep 20
        done
        exec 9>&-
      done
    ) &
  done
  wait
  sleep 20
done
echo "ОТКАЗ: за 40 кругов дорожки не собрались"
exit 1
