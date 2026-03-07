# 🚀 Master Plan: OpenClaw Deployment on Mac mini

This document serves as a "context snapshot" for continuing work in a new session (BrainStorm).

## 📍 Current Status (Status Quo)
- **Device**: Mac mini (Apple Silicon).
- **Access**: Configured via SSH at `crazy-home.keenetic.name:2022`.
- **Server Working Directory**: `/Users/max/openclaw`.
- **Progress So Far**: 
    - The `openclaw` repository has been successfully cloned to `~/openclaw`.
    - Homebrew detected at `/opt/homebrew/bin/brew`.
- **Obstacle**: Docker Desktop was not found in standard paths; requires manual installation or permission verification (sudo access needed for terminal install).

## 🛠 Tech Stack
- **OpenClaw**: The Agent Engine.
- **Docker**: Containerization (required for agent isolation).
- **Telegram**: Control Interface.
- **Node.js/Python**: Internal container dependencies.

## 📋 Implementation Roadmap

### Step 1: Infrastructure Preparation (Mac mini)
1. **Docker**: Install Docker Desktop manually (via GUI or `brew install --cask docker`). **Important:** Launch the app after installation and enable "Privileged Access".
2. **Node.js**: As a fallback, ensure local Node.js 20+ is available (`brew install node`).

### Step 2: Configuration (Environment)
Create the `~/openclaw/.env` file with the following parameters:
- `TELEGRAM_BOT_TOKEN`: `8756536016:AAHInF4IcHHzQEBg_NilP2cR0x4SDtQC0y4`
- `ALLOWED_TELEGRAM_USER_IDS`: [Your numeric ID from @userinfobot]
- `ANTHROPIC_API_KEY`: [Your Claude API Key]
- `WORKSPACE_DIR`: `/Users/max/projects` (The directory the bot will manage).

### Step 3: Docker Compose Customization
Configure `docker-compose.yml` to:
- Mount the host projects folder into the container:
  ```yaml
  volumes:
    - /Users/max/projects:/app/workspace
  ```
- Ensure the bot has network access to reach Telegram servers.

### Step 4: "Headless" Mode (Deep Automation)
Run the following command to prevent the Mac mini from sleeping:
```bash
sudo pmset -a preventsleep 1
```
*(Requires sudo password entry in the terminal once).*

### Step 5: Verification and Launch
1. `docker-compose up -d`
2. Check logs: `docker logs openclaw-bot -f`

## 🧩 Context for "BrainStorm"
When starting the new chat, provide this instruction and state:
> "We already have the repository cloned at `~/openclaw` on the Mac mini. SSH access is configured. We need to focus on correct Docker container configuration and integration with the projects folder in `/Users/max/projects`."

## 📎 Links and Commands
- **Clone (if needed)**: `git clone https://github.com/openclaw/openclaw.git`
- **SSH Command (from current project)**: 
  `ssh -p 2022 -i /Users/max.klochikhin/projects/kleinanzeigen-bot/tools/virtual_machines/mac_mini/ssh-keys/id_ed25519_macmini Max@crazy-home.keenetic.name`
