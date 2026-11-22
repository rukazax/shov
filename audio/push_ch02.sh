#!/usr/bin/env bash
# Добить одну главу: гоняет её, пока дорожка не станет свежей.
# Нужен, когда в главе застрял один блок, а общий поток уехал на следующие номера.
set -u
cd "$(dirname "$0")"
STAMP=out/.cast-rebuild
b=${1:?укажи главу, напр. ch02}
deadline=$(( $(date +%s) + ${2:-7200} ))
exec 9>"out/$b.lock" || exit 1
if ! flock -n 9; then echo "$b занята другим потоком — выхожу"; exit 0; fi
try=0
while [ "$(date +%s)" -lt "$deadline" ]; do
  try=$((try+1))
  if [ "out/$b.mp3" -nt "$STAMP" ]; then echo "$b готова (заходов $try)"; exit 0; fi
  echo "== заход $try $(date +%H:%M:%S)"
  python3 -u render.py "../BOOK01/$b.md" --jobs 3 && continue
  echo "  не вышло, пауза 30 с"; sleep 30
done
echo "ОТКАЗ: $b не собралась за отведённое время"; exit 1
