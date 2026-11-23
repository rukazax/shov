#!/usr/bin/env bash
# Машинные гейты тома 4. Запуск: BOOK03/gate.sh
set -u
cd "$(dirname "$0")"

FAIL=0
echo "=== полнота ==="
[ -f ch00_vvedenie.md ] || [ -f ch00.md ] || { echo "НЕТ ФАЙЛА: ch00"; FAIL=1; }
for n in $(seq -w 1 33); do
  f="ch${n}.md"
  [ -f "$f" ] || { echo "НЕТ ФАЙЛА: $f"; FAIL=1; }
done

echo
echo "=== объём и метрики по главам ==="
printf '%-16s %7s %4s %4s %4s %4s\n' "файл" "знаков" "диал" "сцен" "сист" "OK"
TOTAL=0; SCENES=0; SYSTEM=0
for f in ch*.md; do
  [ -f "$f" ] || continue
  chars=$(wc -m < "$f")
  lines=$(grep -cve '^[[:space:]]*$' "$f" || true)
  dial=$(grep -c '^– ' "$f" || true)
  scenes=$(grep -cE '^\* \* \*$' "$f" || true)
  sys=$(grep -cE '^(Согласование|Метка|Допуск|Протечка|Сдвиг|Регистрация|Скоба|Тяга|Контакт|Отклонение|Группа)' "$f" || true)
  dpct=0; [ "$lines" -gt 0 ] && dpct=$(( dial * 100 / lines ))
  ok="ok"
  if [ "$f" = "ch00_vvedenie.md" ]; then
    if [ "$chars" -lt 7000 ] || [ "$chars" -gt 12000 ]; then ok="ОБЪЁМ"; fi
  else
    if [ "$chars" -lt 16000 ] || [ "$chars" -gt 23000 ]; then ok="ОБЪЁМ"; fi
  fi
  if [ "$f" != "ch00_vvedenie.md" ] && [ "$dpct" -lt 25 ]; then ok="$ok/ДИАЛОГ"; fi
  [ "$ok" = "ok" ] || FAIL=1
  TOTAL=$((TOTAL+chars)); SCENES=$((SCENES+scenes)); SYSTEM=$((SYSTEM+sys))
  printf '%-16s %7d %3d%% %4d %4d %s\n' "$f" "$chars" "$dpct" "$scenes" "$sys" "$ok"
done
echo "итого знаков: $TOTAL  сцен: $SCENES  системных строк: $SYSTEM"

echo
echo "=== типографика ==="
bad=0
for f in ch*.md; do
  [ -f "$f" ] || continue
  a=$(grep -c '—' "$f" || true)
  b=$(grep -c '\.\.\.' "$f" || true)
  c=$(grep -cP '[A-Za-z]' "$f" || true)
  d=$(grep -cP '[а-я]\.[А-Я]' "$f" || true)
  if [ "$a$b$c$d" != "0000" ]; then
    echo "$f: длинное тире=$a троеточие=$b латиница=$c склейки=$d"
    FAIL=1
  fi
done
echo "(пусто выше = чисто)"

echo
echo "=== атрибуция реплик ==="
# «– сказал он» про героя-рассказчика запрещено: в томе двое Семёнов.
attr=0
for f in ch*.md; do
  [ -f "$f" ] || continue
  n=$(grep -cE '^– .*– (сказал|говорит|ответил|спросил) он[.,]' "$f" || true)
  if [ "$n" -gt 0 ]; then
    echo "$f: безличных «он» $n"
    attr=$((attr+n))
  fi
done
[ "$attr" -eq 0 ] && echo "(чисто)" || echo "ВСЕГО БЕЗЛИЧНЫХ: $attr (правило атрибуции из SPINE.md)"

echo
[ "$FAIL" -eq 0 ] && echo "ГЕЙТЫ: PASS" || echo "ГЕЙТЫ: FAIL"
exit "$FAIL"
