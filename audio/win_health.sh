#!/usr/bin/env bash
# Раз в 13 минут (таймер shov-win-health): Windows-бокс синтеза жив и говорит ли.
# Отвечает — строка в лог. Не отвечает — перезапуск движка на боксе и повторная проверка.
# Доступ к боксу: SMB/RPC, креды в /etc/shov-win-health.env (0600).
set -u
cd "$(dirname "$0")"
ENVF=/etc/shov-win-health.env
[ -r "$ENVF" ] && . "$ENVF"
HOST=${WIN_HOST:-192.168.88.20}
PORT=${WIN_PORT:-8765}
CREDS=${WIN_CREDS:-}
WMIPATH=${WMIPATH:-/srv/apps/toolchains/venv-imp/bin/wmiexec.py}
LOG=${LOG:-logs/win-health.log}

mkdir -p "$(dirname "$LOG")"
[ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 2000000 ] && mv -f "$LOG" "$LOG.1"

say() { printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }
health() { curl -s --noproxy '*' -m 8 -o /dev/null -w '%{http_code}' "http://$HOST:$PORT/health" 2>/dev/null || echo 000; }
# Настоящая проба: /health отдаёт живой поток, даже когда модель не считает.
# Синтез короткой фразы — единственное доказательство, что движок работает.
probe() {
  curl -s --noproxy '*' -m 25 -X POST -H 'Content-Type: application/json' \
    -d '{"text":"Проверка.","ref":"hero_calm"}' "http://$HOST:$PORT/tts" 2>/dev/null | wc -c | tr -d ' \n'
}

ping -c2 -W2 "$HOST" >/dev/null 2>&1 && alive=1 || alive=0
code=$(health)
bytes=$(probe)

gpu=""
if [ "$alive" = 1 ] && [ -n "$CREDS" ] && [ -x "$WMIPATH" ]; then
  gpu=$(timeout 90 "$WMIPATH" "$CREDS@$HOST" \
    'nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader' 2>/dev/null \
    | grep -oE '[0-9]+ %, [0-9]+ MiB, [0-9]+' | head -1)
fi

if [ "$alive" = 1 ] && [ "$code" = 200 ] && [ "${bytes:-0}" -gt 2000 ]; then
  say "ok ping=1 health=$code tts=${bytes}Б${gpu:+ gpu=[$gpu]}"
  exit 0
fi

say "ПРОБЛЕМА ping=$alive health=$code tts=${bytes}Б — перезапускаю движок на боксе"
if [ "$alive" != 1 ]; then
  say "бокс не отвечает на ping: удалённо не чиню, жду возвращения"
  exit 1
fi
if [ -z "$CREDS" ] || [ ! -x "$WMIPATH" ]; then
  say "нет доступа ($ENVF / $WMIPATH) — перезапуск невозможен"
  exit 1
fi

# Движок 8765 держит задача планировщика ttsserver (C:\tts\tts_server.py).
# Раньше здесь стоял restart_f5.bat — он поднимает ДРУГОЙ сервер (F5-TTS, 8767),
# поэтому «перезапуск» проходил успешно, а 8765 оставался мёртвым (23.11).
timeout 90 "$WMIPATH" "$CREDS@$HOST" \
  'schtasks /end /tn ttsserver & schtasks /run /tn ttsserver' >>"$LOG" 2>&1
for i in 1 2 3 4 5; do
  sleep 15
  code=$(health)
  bytes=$(probe)
  if [ "$code" = 200 ] && [ "${bytes:-0}" -gt 2000 ]; then
    say "починено с $i-й проверки после перезапуска: health=$code tts=${bytes}Б"
    exit 0
  fi
done
say "НЕ ПОЧИНИЛОСЬ: health=$code tts=${bytes}Б — нужен человек"
exit 1
