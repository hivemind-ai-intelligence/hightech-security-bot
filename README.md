# ────────────────────────────────────────────────────────────
# 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 Discord Bot
# Enterprise-grade Discord server protection — Vampire Edition 🩸
# ────────────────────────────────────────────────────────────

## Features

### 🛡️ Automated Moderation
- **Content Filtering** — Auto-detects and removes banned keywords, invite links, scam patterns
- **Anti-Spam** — Rate-limit detection with automatic timeout and message cleanup
- **Manual Moderation** — `warn`, `mute`, `kick`, `ban`, `unban`, `purge`

### 🔐 Team Access Control & Verification
- **Email OTP Verification** — New members verify identity via 6-digit email code
- **Manual Verification** — Admins can manually verify trusted members
- **Whois Lookup** — Check user verification status and account details

### 🔎 Threat Intelligence
- **IP Reputation** — Check IPs against AbuseIPDB
- **File Hash Scanning** — Look up SHA-256/MD5 hashes on VirusTotal
- **URL Scanning** — Scan suspicious URLs on VirusTotal
- **Automated Threat Feed** — Periodic AlienVault OTX pulse ingestion
- **Threat Reports** — Generate combined threat summaries

### 🚨 Incident Management
- **Incident Tracking** — Create, assign, update, and resolve security incidents
- **Severity Levels** — Critical, High, Medium, Low, Info
- **Webhook Intake** — Accept alerts from external SIEM/IDS/monitoring tools
- **Alert Channels** — Auto-post to configured alert and incident channels

### 🛡️ Anti-Raid Protection
- **Raid Detection** — Monitors join velocity; auto-locks server on threshold breach
- **Manual Lockdown** — One-command full server lockdown/unlock
- **Per-Channel Lock** — Lock/unlock individual channels
- **Slowmode** — Set per-channel rate limiting

### 📋 Comprehensive Audit Logging
- Message edits/deletes (including bulk)
- Member joins/leaves/kicks/bans
- Role and nickname changes
- Channel creation/deletion/updates
- Voice channel activity

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- A Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- A Discord server where you have Admin permissions

### 2. Create a Discord Bot
1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it "Hi-Tech Security"
3. Go to the **Bot** tab → Add Bot
4. Enable all **Privileged Gateway Intents** (Presence, Server Members, Message Content)
5. Copy the **Token**
6. Go to **OAuth2** → **URL Generator**
   - Select `bot` and `applications.commands`
   - Bot Permissions: **Administrator** (or at minimum: Kick, Ban, Manage Messages, Manage Channels, Manage Roles, Timeout Members, Read Messages/View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Mention Everyone, Use Slash Commands)
   - Use the generated URL to invite the bot

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Discord token, channel IDs, role IDs, and API keys
```

### 4. Run the Bot

**Option A: Direct Python**
```bash
pip install -r requirements.txt
python bot.py
```

**Option B: Docker**
```bash
docker compose up -d
```

### 5. Set Up Discord Channels
Create these channels in your server and update their IDs in `.env`:
- `#audit-log` — All security events
- `#alerts` — High-priority security alerts
- `#threat-intel` — Automated threat feed
- `#incidents` — Active incident tracking
- `#welcome` — New member verification prompts

### 6. Set Up Roles
Create these roles and update their IDs in `.env`:
- `@Admin` — Full bot control
- `@Security Team` — Incident & moderation access
- `@Verified` — Granted after email verification

---

## 🎨 Vampire Theme

The bot uses a **red-black gothic/vampire aesthetic** throughout:
- **Display Name:** `🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞` (Unicode gothic font)
- **Avatar:** Red-black gradient shield emblem (see `data/avatar.png`)
- **All Embeds:** Blood-red (#8B0000) to crimson (#FF0000) color scheme
- **Status:** Dark gothic presence with vampire bat emoji

### Setting the Avatar
1. Download the generated avatar from the `data/` folder or regenerate via `/generate_image`
2. Go to https://discord.com/developers/applications → Your Bot → **Bot** tab
3. Under "Display Name" set it to: `🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞`
4. Upload the avatar image under "Bot Icon"

> ⚠️ The Unicode gothic name works on Discord! Discord supports Unicode math-bold-fraktur characters.

## Commands Reference

### Moderation
| Command | Permission | Description |
|---------|-----------|-------------|
| `/warn <@user> [reason]` | Moderate Members | Issue a warning |
| `/mute <@user> [minutes] [reason]` | Moderate Members | Timeout a user |
| `/unmute <@user>` | Moderate Members | Remove timeout |
| `/kick <@user> [reason]` | Kick Members | Kick a user |
| `/ban <@user> [reason]` | Ban Members | Ban a user |
| `/unban <user_id> [reason]` | Ban Members | Unban a user |
| `/purge <amount>` | Manage Messages | Bulk-delete messages |

### Verification
| Command | Permission | Description |
|---------|-----------|-------------|
| `/verify email:<email>` | Everyone | Request OTP code |
| `/confirm code:<code>` | Everyone | Submit OTP code |
| `/whois <@user>` | Moderate Members | Check user status |
| `/verify_manual <@user> <email>` | Admin | Manual verification |

### Threat Intelligence
| Command | Permission | Description |
|---------|-----------|-------------|
| `/check_ip <ip>` | Everyone | IP reputation lookup |
| `/check_hash <hash>` | Everyone | VirusTotal hash scan |
| `/check_url <url>` | Everyone | VirusTotal URL scan |
| `/threat_report` | Moderate Members | Threat summary |

### Incidents & Alerts
| Command | Permission | Description |
|---------|-----------|-------------|
| `/alert <severity> <description>` | Moderate Members | Create incident |
| `/incidents` | Moderate Members | List all incidents |
| `/incident <id>` | Moderate Members | View incident details |
| `/assign <id> <@user>` | Moderate Members | Assign incident |
| `/update_incident <id> <text>` | Moderate Members | Add update |
| `/resolve <id> [note]` | Moderate Members | Resolve incident |

### Anti-Raid
| Command | Permission | Description |
|---------|-----------|-------------|
| `/lockdown` | Admin | Toggle server lockdown |
| `/raid_status` | Moderate Members | Check raid detection |
| `/lock_channel` | Manage Channels | Lock one channel |
| `/unlock_channel` | Manage Channels | Unlock one channel |
| `/slowmode <seconds>` | Manage Channels | Set slowmode |

### Admin
| Command | Permission | Description |
|---------|-----------|-------------|
| `/ping` | Everyone | Bot latency |
| `/status` | Moderate Members | Server & bot stats |
| `/config_show` | Admin | View configuration |
| `/reload <cog>` | Admin | Hot-reload module |
| `/cogs` | Admin | List loaded modules |
| `/help` | Everyone | Command reference |

---

## Optional Integrations

### Threat Intel APIs
- **AbuseIPDB** — Sign up at https://www.abuseipdb.com/account/api (free tier available)
- **VirusTotal** — Sign up at https://www.virustotal.com/gui/my-apikey (free tier)
- **AlienVault OTX** — Sign up at https://otx.alienvault.com/ (free)

### Email Verification
- Use Gmail with an **App Password** (recommended for testing)
- Or any SMTP server

### External Alert Webhook
The webhook server accepts POST requests from SIEM, IDS/IPS, or monitoring tools:
```bash
curl -X POST http://your-server:8080/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-webhook-api-key" \
  -d '{
    "title": "Suspicious Login Detected",
    "severity": "high",
    "source": "SIEM",
    "details": "Multiple failed SSH attempts from 203.0.113.42",
    "source_ip": "203.0.113.42",
    "target": "prod-server-01"
  }'
```

---

## Project Structure
```
hightech-security-bot/
├── bot.py                  # Main entry point
├── webhook_server.py       # External alert intake HTTP server
├── config/
│   └── settings.py         # Configuration dataclass
├── cogs/
│   ├── moderation.py       # Auto-moderation & content filtering
│   ├── verification.py     # Email OTP identity verification
│   ├── threat_intel.py     # IP/hash/URL lookups, OTX feed
│   ├── incident_alerts.py  # Incident management & tracking
│   ├── audit_logging.py    # Comprehensive event logging
│   ├── anti_raid.py        # Raid detection & server lockdown
│   ├── admin.py            # Bot diagnostics & config
│   └── help.py             # Unified help command
├── data/                   # Persistent data (verification codes, incidents)
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image
└── docker-compose.yml      # Docker Compose stack
```
