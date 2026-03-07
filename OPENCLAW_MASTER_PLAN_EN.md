# 🚀 Master Plan: OpenClaw Deployment on Mac mini (Remote via SSH)

This document serves as the source of truth for the deployment process ON THE REMOTE MAC MINI. All commands are executed from the local laptop via SSH.

## 📍 Current Status (Status Quo)
- **Remote Host**: Mac mini (Apple Silicon) at `crazy-home.keenetic.name:2022`
- **User**: `Max`
- **Remote Project Path**: `/Users/max/openclaw`
- **GitHub**: [max-klochikhin/openclaw](https://github.com/max-klochikhin/openclaw)
- **Local Proxy folder**: `/Users/max.klochikhin/projects/openclaw` (Used only for documentation and plan tracking).

## 📋 Implementation Roadmap

### Step 1: Environment Preparation (DONE)
1. **Node.js**: Installed v25+ via brew on Mac mini.
2. **PM2**: Installed globally via npm on Mac mini.
3. **pnpm**: Installed via brew on Mac mini.

### Step 2: Configuration
Create/Update `.env` in the remote project root `~/openclaw/.env`:
- `TELEGRAM_BOT_TOKEN`: `8756536016:AAHInF4IcHHzQEBg_NilP2cR0x4SDtQC0y4`
- `ALLOWED_TELEGRAM_USER_IDS`: [Your numeric ID]
- `ANTHROPIC_API_KEY`: [REQUIRED]
- `WORKSPACE_DIR`: `/Users/max/projects`

### Step 3: Remote Installation
1. Install dependencies: `pnpm install`
2. Build the project: `pnpm build`

### Step 4: Launch & Persistence
1. Start with PM2: `pm2 start dist/index.js --name openclaw`
2. Configure auto-start on reboot: `pm2 save && pm2 startup`

### Step 5: Optimization
1. Prevent sleep: `sudo pmset -a preventsleep 1`

---

## 📜 Installation Log (Remote)
| Step | Action | Remote Command | Result | Rollback Command |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Install Node/pnpm | `brew install node pnpm` | Done | `brew uninstall node pnpm` |
| 2 | Install PM2 | `npm install -g pm2` | Done | `npm uninstall -g pm2` |
| 3 | Install dependencies | `pnpm install` | Done | `rm -rf ~/openclaw/node_modules` |
| 4 | Build project | `pnpm build` | Done | `rm -rf ~/openclaw/dist` |
| 5 | Create .env | `echo ... > .env` | Done | `rm ~/openclaw/.env` |
| 6 | Create Workspace | `mkdir -p /Users/max/projects` | Done | `rmdir /Users/max/projects` |

---

## 📎 Links and Commands
- **SSH Command**: 
  `ssh -p 2022 -i /Users/max.klochikhin/projects/kleinanzeigen-bot/tools/virtual_machines/mac_mini/ssh-keys/id_ed25519_macmini Max@crazy-home.keenetic.name`
