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

## Final State (as of 2026-03-07)

| Component | Value |
|---|---|
| LaunchAgent | `ai.openclaw.gateway` (loaded, RunAtLoad=true, KeepAlive=true) |
| Gateway port | `18789` |
| Bot username | `@open_claw_ai_assistant_bot` |
| Agent model | `google/gemini-flash-latest` |
| Config file | `/Users/max/.openclaw/openclaw.json` |
| Plist file | `/Users/max/Library/LaunchAgents/ai.openclaw.gateway.plist` |
| Logs (stdout) | `/Users/max/.openclaw/logs/gateway.log` |
| Logs (stderr) | `/Users/max/.openclaw/logs/gateway.err.log` |
| Detailed logs | `/tmp/openclaw/openclaw-YYYY-MM-DD.log` |

---

## Will it survive a Mac restart?

**Yes.** The LaunchAgent has:
- `RunAtLoad = true` — starts automatically when you log in
- `KeepAlive = true` — restarts automatically if it crashes
- `WorkingDirectory` configured — so `.env` is loaded correctly
- `gateway.mode = "local"` set in config — no longer blocked on startup
- `botToken` stored in config — Telegram channel is fully configured

**To check status after a restart:**

```bash
launchctl list | grep ai.openclaw
# Expected: PID   0   ai.openclaw.gateway  (0 = no error)

tail -f /Users/max/.openclaw/logs/gateway.log
# Should show: [telegram] [default] starting provider (@open_claw_ai_assistant_bot)
```

**To restart the service manually:**

```bash
launchctl unload ~/Library/LaunchAgents/ai.openclaw.gateway.plist
launchctl load   ~/Library/LaunchAgents/ai.openclaw.gateway.plist
```
