#!/bin/bash
# Обновляет GOOGLE_ACCESS_TOKEN в LaunchAgent plist и перезапускает daemon
# Запускается по cron каждые 45 минут

CREDS='/Users/max/kleinanzeigen_bot/tools/telegram_llm_bot/config/gcloud_credentials.json'
PLIST='/Users/max/Library/LaunchAgents/ai.openclaw.gateway.plist'
LOG='/Users/max/.openclaw/logs/token-refresh.log'

CLIENT_ID=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['client_id'])")
CLIENT_SECRET=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['client_secret'])")
REFRESH_TOKEN=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['refresh_token'])")

RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&refresh_token=${REFRESH_TOKEN}&grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))")

if [ -z "$ACCESS_TOKEN" ]; then
  echo "$(date): ОШИБКА: не удалось получить токен: $RESPONSE" >> "$LOG"
  exit 1
fi

# Обновляем или добавляем GOOGLE_ACCESS_TOKEN в plist
python3 << PYEOF
import re, subprocess
plist_path = '$PLIST'
token = '$ACCESS_TOKEN'

with open(plist_path, 'r') as f:
    content = f.read()

if '<key>GOOGLE_ACCESS_TOKEN</key>' in content:
    # Обновляем существующий токен
    content = re.sub(
        r'(<key>GOOGLE_ACCESS_TOKEN</key>\s*<string>)[^<]*(</string>)',
        f'\\g<1>{token}\\g<2>',
        content
    )
else:
    # Добавляем новый токен
    old = '    <key>GEMINI_API_KEY</key>'
    new = f'    <key>GOOGLE_ACCESS_TOKEN</key>\n    <string>{token}</string>\n    <key>GEMINI_API_KEY</key>'
    content = content.replace(old, new, 1)

with open(plist_path, 'w') as f:
    f.write(content)
PYEOF

# Перезапускаем daemon
launchctl unload "$PLIST" 2>/dev/null
sleep 1
launchctl load "$PLIST"

echo "$(date): Токен обновлён и daemon перезапущен" >> "$LOG"
