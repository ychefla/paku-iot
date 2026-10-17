#!/bin/sh
# Renders Telegram alert notifications from env vars, then starts Grafana.
# Without credentials the file is left out so Grafana still starts; alert
# rules keep evaluating but nothing is sent.
set -e

OUT=/etc/grafana/provisioning/alerting/notifications.yaml

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  sed -e "s|__TELEGRAM_BOT_TOKEN__|${TELEGRAM_BOT_TOKEN}|" \
      -e "s|__TELEGRAM_CHAT_ID__|${TELEGRAM_CHAT_ID}|" \
      /etc/grafana/alerting-notifications.yaml.tmpl > "$OUT"
  echo "=== Telegram alert notifications enabled ==="
else
  rm -f "$OUT"
  echo "=== TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set: alert notifications disabled ==="
fi

exec /run.sh "$@"
