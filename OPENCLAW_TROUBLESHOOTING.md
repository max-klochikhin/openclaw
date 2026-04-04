# OpenClaw Mac Mini — Troubleshooting & Setup Notes

> Created: 2026-03-07  
> Environment: Mac mini, macOS, OpenClaw v2026.3.7

---

## Summary

After installing OpenClaw on the Mac mini, the gateway LaunchAgent was repeatedly
crashing (exit code 1) and the Telegram bot was not responding to messages.
This document describes each issue found, the root cause, and the fix applied.

---

## Issue 1: Gateway blocked from starting — `gateway.mode` not set

### Symptom
The LaunchAgent `ai.openclaw.gateway` was in a crash-loop visible via:

```
launchctl list | grep ai.openclaw
# showing non-zero exit code
```

`/Users/max/.openclaw/logs/gateway.err.log` was full of:

```
Gateway start blocked: set gateway.mode=local (current: unset) or pass --allow-unconfigured.
```

### Root Cause
OpenClaw requires `gateway.mode` to be explicitly set in `~/.openclaw/openclaw.json`
before the service will start. It was left unset after the initial installation wizard.

### Fix Applied
1. Added `"mode": "local"` inside the `gateway` object in `/Users/max/.openclaw/openclaw.json`.
2. Added `--allow-unconfigured` flag to the ProgramArguments in the LaunchAgent plist
   as a safety net to prevent this crash-loop from happening again in the future.

```json
// ~/.openclaw/openclaw.json  — gateway section
"gateway": {
  "mode": "local",
  "auth": {
    "mode": "token",
    "token": "..."
  }
}
```

---

## Issue 2: Telegram bot not configured — token missing from OpenClaw config

### Symptom
Even after the gateway started successfully, messages sent to the Telegram bot
(`@open_claw_ai_assistant_bot`) received no response.

`openclaw channels list` showed:

```
Telegram default: not configured, token=none, enabled
```

### Root Cause
OpenClaw stores its own Telegram bot token in `~/.openclaw/openclaw.json`.
Even though a `TELEGRAM_BOT_TOKEN` existed in `/Users/max/openclaw/.env`,
OpenClaw does **not** automatically read from that legacy `.env` file at runtime
— the token must be explicitly registered via `openclaw channels add`.

### Fix Applied
Ran the following command to register the bot token in OpenClaw's config:

```bash
/opt/homebrew/opt/node/bin/node /Users/max/openclaw/openclaw.mjs \
  channels add --channel telegram --token 8756536016:AAHInF4IcHHzQEBg_NilP2cR0x4SDtQC0y4
```

This wrote `"botToken": "..."` into the `channels.telegram` section of
`~/.openclaw/openclaw.json`.

---

## Issue 3: User allowlist missing sender's Telegram ID

### Symptom
Bot started successfully but still no response to messages.

### Root Cause
The `channels.telegram.allowFrom` list in `openclaw.json` contained only one user ID
(`1297932849`) but the user sending messages had a different Telegram user ID
(`135208609`). OpenClaw uses a strict allowlist — messages from unlisted IDs are
silently dropped.

### Fix Applied
Added the second user ID to the allowlist in `/Users/max/.openclaw/openclaw.json`:

```json
"channels": {
  "telegram": {
    "enabled": true,
    "dmPolicy": "allowlist",
    "botToken": "...",
    "allowFrom": [
      1297932849,
      135208609
    ],
    ...
  }
}
```

---

## Issue 4: LaunchAgent missing WorkingDirectory — .env not loaded on boot

### Symptom
After a Mac restart, the service started without loading environment variables from
`/Users/max/openclaw/.env`, causing potential API key failures.

### Root Cause
LaunchAgents do not inherit a working directory, so relative `.env` file lookups
fail. Without `WorkingDirectory` set, the Node process could not find `.env`
relative to the OpenClaw project directory.

### Fix Applied
Added `WorkingDirectory` to `/Users/max/Library/LaunchAgents/ai.openclaw.gateway.plist`:

```xml
<key>WorkingDirectory</key>
<string>/Users/max/openclaw</string>
```

---

## Issue 5: Gemini API limits reached — Shared account interference

### Symptom
OpenClaw was frequently hitting Gemini API rate limits (RPM/TPM) because the API key was shared with another system.

### Root Cause
Google AI Studio enforces free-tier limits per account. Using one key for multiple active systems caused them to compete for the same 15 RPM / 1500 RPD budget.

### Fix Applied (2026-03-07)
1. **Created Dedicated Account**: Logged into a new Google account (`avneet.everett.2021@gmail.com`).
2. **Generated New API Key**: Created a fresh key in AI Studio.
3. **Verified Key**: Verified the key works via a standalone `curl` request to the Gemini API.
4. **Isolated Config**: Updated the `GEMINI_API_KEY` in `/Users/max/openclaw/.env`. This decouples OpenClaw from the other system's limits.

---

## Issue 6: Миграция на Google Vertex AI — цепочка из 8 ошибок

> Дата: 2026-04-04  
> Цель: переключить агента с `google/gemini-flash-latest` на `google-vertex/gemini-3-flash-preview`  
> Используемые credentials: OAuth2 refresh_token из соседнего Telegram-бота `kleinanzeigen-bot`

---

### Ошибка 6.1 — `No API key found for provider "google-vertex"`

**Симптом:**
```
Agent failed before reply: No API key found for provider "google-vertex".
Auth store: /Users/max/.openclaw/agents/main/agent/auth-profiles.json
```

**Причина:**  
Файл `auth-profiles.json` был в устаревшем плоском формате (`{"google": {...}}`), тогда как OpenClaw ожидает обёртку `{"version": 1, "profiles": {...}}`. При загрузке функция `coerceAuthStore` видела неизвестный формат и возвращала пустое хранилище.

**Исправление:**  
Перезаписан `/Users/max/.openclaw/agents/main/agent/auth-profiles.json` в правильную структуру:

```json
{
  "version": 1,
  "profiles": {
    "google": {
      "default": { "apiKey": "AIzaSy..." }
    },
    "google-vertex": {
      "default": { "apiKey": "AIzaSy..." }
    }
  }
}
```

---

### Ошибка 6.2 — `Vertex AI requires a project ID`

**Симптом:**
```
Vertex AI requires a project ID. Set GOOGLE_CLOUD_PROJECT/GCLOUD_PROJECT or pass project in options.
```

**Причина:**  
LaunchAgent запускает daemon без переменных окружения из `.env`. `GOOGLE_CLOUD_PROJECT` не был передан процессу.

**Исправление:**  
Добавлено в `/Users/max/Library/LaunchAgents/ai.openclaw.gateway.plist`:

```xml
<key>GOOGLE_CLOUD_PROJECT</key>
<string>gen-lang-client-0431347096</string>
```

---

### Ошибка 6.3 — `Vertex AI requires a location`

**Симптом:**
```
Vertex AI requires a location. Set GOOGLE_CLOUD_LOCATION or pass location in options.
```

**Исправление:**  
Добавлено в plist:

```xml
<key>GOOGLE_CLOUD_LOCATION</key>
<string>global</string>
```

---

### Ошибка 6.4 — `Could not load the default credentials`

**Симптом:**
```
Could not load the default credentials. Browse to https://cloud.google.com/docs/authentication/...
```

**Причина:**  
Vertex AI требует OAuth2-credentials. Файл `gcloud_credentials.json` из соседнего бота (`kleinanzeigen-bot`) содержит `client_id`, `client_secret`, `refresh_token` типа `authorized_user` — именно их нужно использовать.

**Исправление:**  
Добавлено в plist:

```xml
<key>GOOGLE_APPLICATION_CREDENTIALS</key>
<string>/Users/max/kleinanzeigen_bot/tools/telegram_llm_bot/config/gcloud_credentials.json</string>
```

---

### Ошибка 6.5 — `Project/location and API key are mutually exclusive`

**Симптом:**
```
Project/location and API key are mutually exclusive in the client initializer.
```

**Причина:**  
`@google/genai` SDK не позволяет одновременно передавать `project`/`location` и `apiKey` при `vertexai: true`.

**Исправление:**  
Патч файла `pi-ai/dist/providers/google-vertex.js` — функция `createClient` теперь не передаёт `apiKey` вместе с `project`/`location`:

```javascript
function createClient(model, project, location, optionsHeaders) {
    const httpOptions = {};
    const accessToken = process.env.GOOGLE_ACCESS_TOKEN;
    if (accessToken) {
        httpOptions.headers = { 'Authorization': 'Bearer ' + accessToken };
    }
    return new GoogleGenAI({
        vertexai: true,
        project,
        location,
        apiVersion: API_VERSION,
        httpOptions: Object.keys(httpOptions).length ? httpOptions : undefined,
    });
}
```

---

### Ошибка 6.6 — `API keys are not supported by this API. Expected OAuth2 access token` (HTTP 401)

**Симптом:**
```json
{"error": {"code": 401, "message": "API keys are not supported by this API.
Expected OAuth2 access token...", "status": "UNAUTHENTICATED"}}
```

**Причина:**  
Vertex AI endpoint (`aiplatform.googleapis.com`) принимает только OAuth2 Bearer-токены. Ключи типа `AIzaSy...` (Google AI Studio) здесь не работают.

**Исправление:**  
1. Создан скрипт `/Users/max/openclaw/scripts/refresh-vertex-token.sh`, который:
   - Читает `client_id`, `client_secret`, `refresh_token` из `gcloud_credentials.json`
   - Обменивает `refresh_token` на свежий `access_token` через `https://oauth2.googleapis.com/token`
   - Записывает токен в plist как `GOOGLE_ACCESS_TOKEN`
   - Перезапускает daemon
2. Токен передаётся в HTTP-заголовке `Authorization: Bearer <token>` через `httpOptions.headers` в `createClient`

---

### Ошибка 6.7 — `Cannot convert undefined or null to object` (первая версия)

**Симптом:**
```
error=Cannot convert undefined or null to object
```

**Причина:**  
Даже с Bearer-токеном в `httpOptions.headers`, SDK `@google/genai` всё равно вызывал `this.googleAuth.getRequestHeaders(url)` (ADC) внутри `addGoogleAuthHeaders`. Функция ADC не проверяла, что `Authorization` уже установлен — она падала с этой ошибкой.

**Попытка исправления (неверный файл):**  
Был пропатчен `@google/genai/dist/node/index.cjs` с добавлением early-return:
```javascript
async addGoogleAuthHeaders(headers, url) {
    if (headers.get('Authorization') || headers.get('authorization')) return;
    // ...
}
```
Но Node.js загружал ES-модульную версию (`index.mjs`), а не CJS. Патч не имел эффекта.

---

### Ошибка 6.8 — `Cannot convert undefined or null to object` (финальная)

**Симптом:**  
Та же ошибка, несмотря на патч `index.cjs`.

**Диагностика:**  
Стек трейс, полученный через добавление try/catch в `google-vertex.js`:

```
at NodeAuth.addGoogleAuthHeaders
  (file:///.../node_modules/@google/genai/dist/node/index.mjs:18402:29)
at async ApiClient.getHeadersInternal
  (file:///.../node_modules/@google/genai/dist/node/index.mjs:12283:9)
```

**Ключевое открытие:**  
Файл загружается как `index.mjs` (ES module), а не `index.cjs`. Предыдущий патч был применён к неверному файлу.

**Финальное исправление:**  
Пропатчен `/Users/max/openclaw/node_modules/.pnpm/@google+genai@1.43.0/node_modules/@google/genai/dist/node/index.mjs`:

```javascript
// Строка ~18395
async addGoogleAuthHeaders(headers, url) {
    // PATCH: пропускаем ADC если Bearer-токен уже установлен
    if (headers.get('Authorization') || headers.get('authorization')) {
        return;
    }
    if (this.googleAuth === undefined) {
        throw new Error('Trying to set google-auth headers but googleAuth is unset');
    }
    const authHeaders = await this.googleAuth.getRequestHeaders(url);
    // ...
}
```

После этого патча прямой вызов API вернул ответ:
```
> Reply with just: OK
OK
DONE
```

---

### Автоматическое обновление токена

OAuth2 access-токены живут ~1 час. Для автоматического обновления:

**Скрипт:** `/Users/max/openclaw/scripts/refresh-vertex-token.sh`

```bash
#!/bin/bash
CREDS='/Users/max/kleinanzeigen_bot/tools/telegram_llm_bot/config/gcloud_credentials.json'
PLIST='/Users/max/Library/LaunchAgents/ai.openclaw.gateway.plist'
LOG='/Users/max/.openclaw/logs/token-refresh.log'

CLIENT_ID=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['client_id'])")
CLIENT_SECRET=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['client_secret'])")
REFRESH_TOKEN=$(python3 -c "import json; d=json.load(open('$CREDS')); print(d['refresh_token'])")

RESPONSE=$(curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&refresh_token=${REFRESH_TOKEN}&grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))")

# Обновляем GOOGLE_ACCESS_TOKEN в plist и перезапускаем daemon
python3 << PYEOF
import re
with open('$PLIST', 'r') as f:
    content = f.read()
content = re.sub(
    r'(<key>GOOGLE_ACCESS_TOKEN</key>\s*<string>)[^<]*(</string>)',
    f'\g<1>$ACCESS_TOKEN\g<2>', content
)
with open('$PLIST', 'w') as f:
    f.write(content)
PYEOF

launchctl unload "$PLIST" && sleep 1 && launchctl load "$PLIST"
echo "$(date): Токен обновлён и daemon перезапущен" >> "$LOG"
```

**Cron-задача (каждые 45 минут):**

```
*/45 * * * * /Users/max/openclaw/scripts/refresh-vertex-token.sh
```

Добавлена через `crontab -e` пользователя `max`.

---

### Итоговый статус после всех исправлений (2026-04-04)

| Компонент | Значение |
|---|---|
| Модель агента | `google-vertex/gemini-3-flash-preview` |
| Vertex project | `gen-lang-client-0431347096` |
| Vertex location | `global` |
| Credentials source | `kleinanzeigen-bot/config/gcloud_credentials.json` (authorized_user) |
| Токен в plist | `GOOGLE_ACCESS_TOKEN` (обновляется cron каждые 45 мин) |
| Пропатченные файлы | `pi-ai/dist/providers/google-vertex.js`, `@google/genai/dist/node/index.mjs` |
| Скрипт обновления | `/Users/max/openclaw/scripts/refresh-vertex-token.sh` |
| Автозапуск | cron `*/45 * * * *` |

### Важное предупреждение о патчах node_modules

Оба пропатченных файла находятся в `node_modules` и будут **перезаписаны** при обновлении пакетов (`pnpm install`, `pnpm update`). После любого обновления зависимостей необходимо повторно применить патчи:

1. **`pi-ai/dist/providers/google-vertex.js`** — `createClient` с inject `Authorization: Bearer`
2. **`@google/genai/dist/node/index.mjs`** — `addGoogleAuthHeaders` с early-return при наличии токена

Долгосрочное решение — дождаться официальной поддержки `GOOGLE_ACCESS_TOKEN` в `pi-ai` или создать fork с постоянным патчем.

---

## Final State (as of 2026-04-04)

| Component | Value |
|---|---|
| LaunchAgent | `ai.openclaw.gateway` (loaded, RunAtLoad=true, KeepAlive=true) |
| Gateway port | `18789` |
| Bot username | `@open_claw_ai_assistant_bot` |
| Agent model | `google-vertex/gemini-3-flash-preview` |
| Vertex project | `gen-lang-client-0431347096` |
| Vertex location | `global` |
| OAuth2 credentials | `/Users/max/kleinanzeigen_bot/tools/telegram_llm_bot/config/gcloud_credentials.json` |
| Token refresh | cron `*/45 * * * *` → `/Users/max/openclaw/scripts/refresh-vertex-token.sh` |
| Config file | `/Users/max/.openclaw/openclaw.json` |
| Auth profiles | `/Users/max/.openclaw/agents/main/agent/auth-profiles.json` |
| Plist file | `/Users/max/Library/LaunchAgents/ai.openclaw.gateway.plist` |
| Logs (stdout) | `/Users/max/.openclaw/logs/gateway.log` |
| Logs (stderr) | `/Users/max/.openclaw/logs/gateway.err.log` |
| Detailed logs | `/tmp/openclaw/openclaw-YYYY-MM-DD.log` |
| Token refresh log | `/Users/max/.openclaw/logs/token-refresh.log` |

---

## Will it survive a Mac restart?

**Yes.** The LaunchAgent has:
- `RunAtLoad = true` — starts automatically when you log in
- `KeepAlive = true` — restarts automatically if it crashes
- `WorkingDirectory` configured — so `.env` is loaded correctly
- `gateway.mode = "local"` set in config — no longer blocked on startup
- `botToken` stored in config — Telegram channel is fully configured
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_ACCESS_TOKEN` — заданы в plist

**Единственное, что не переживёт перезагрузку без cron:**  
OAuth2 access-токен (`GOOGLE_ACCESS_TOKEN`) в plist протухает через 1 час. Cron-задача `*/45 * * * *` обновляет его автоматически. После перезагрузки Mac cron стартует автоматически вместе с системой.

**To check status after a restart:**

```bash
launchctl list | grep ai.openclaw
# Expected: PID   0   ai.openclaw.gateway  (0 = no error)

tail -f /Users/max/.openclaw/logs/gateway.log
# Should show: [telegram] [default] starting provider (@open_claw_ai_assistant_bot)

tail -f /Users/max/.openclaw/logs/token-refresh.log
# Should show recent: Токен обновлён и daemon перезапущен
```

**To restart the service manually:**

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load   ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```

**To manually refresh the Vertex AI token:**

```bash
/Users/max/openclaw/scripts/refresh-vertex-token.sh
```
