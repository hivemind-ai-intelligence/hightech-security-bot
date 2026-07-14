"""
Hi-Tech Security Discord Bot — Configuration
All sensitive values should be set via environment variables.

Bot works GLOBALLY — no hardcoded guild/server IDs.
Channel & role configs are optional and used as defaults only.
"""

import os
from dataclasses import dataclass, field
from typing import List
from pathlib import Path

# Auto-load .env file
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


@dataclass
class SecurityBotConfig:
    # ── Discord ──────────────────────────────────────────────
    bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
    bot_prefix: str = os.getenv("BOT_PREFIX", "!")

    # ── Optional Default Channel IDs (used as fallback) ─────
    audit_log_channel_id: int = int(os.getenv("AUDIT_LOG_CHANNEL_ID", "0"))
    alert_channel_id: int = int(os.getenv("ALERT_CHANNEL_ID", "0"))
    threat_intel_channel_id: int = int(os.getenv("THREAT_INTEL_CHANNEL_ID", "0"))
    incident_channel_id: int = int(os.getenv("INCIDENT_CHANNEL_ID", "0"))
    welcome_channel_id: int = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
    log_channel_id: int = int(os.getenv("LOG_CHANNEL_ID", "0"))

    # ── Threat Intelligence API Keys ─────────────────────────
    abuseipdb_api_key: str = os.getenv("ABUSEIPDB_API_KEY", "")
    virustotal_api_key: str = os.getenv("VIRUSTOTAL_API_KEY", "")
    alienvault_otx_api_key: str = os.getenv("ALIENVAULT_OTX_API_KEY", "")

    # ── Email Alerts ────────────────────────────────────────
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")
    alert_email: str = os.getenv("ALERT_EMAIL", "")

    # ── Rate Limiting & Anti-Spam ───────────────────────────
    max_messages_per_second: int = 5
    max_mentions_per_message: int = 10
    raid_detection_threshold: int = 5
    raid_detection_window: int = 10
    mute_duration_minutes: int = 15

    # ── Banned keywords (regex patterns) ────────────────────
    banned_keywords: List[str] = field(default_factory=lambda: [
        r"discord\.gg/\S+",
        r"nitro.*free",
        r"steam.*gift",
        r"free.*nitro",
        r"@everyone",
        r"@here",
    ])

    # ── 2FA Verification Settings ───────────────────────────
    verification_code_length: int = 6
    verification_code_ttl_minutes: int = 10
    max_verification_attempts: int = 3

    # ── Logging ─────────────────────────────────────────────
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "data/bot.log")

    # ── Vampire/Gothic Theme Colors ─────────────────────────
    theme_primary: int = 0x8B0000       # Dark Red (blood)
    theme_danger: int = 0xFF0000        # Bright Red (critical)
    theme_dark: int = 0x1A0000          # Near-black red
    theme_warning: int = 0xFF4500       # Orange-Red
    theme_success: int = 0x8B0000       # Dark Red (vampire theme)
    theme_info: int = 0x8B0000          # Dark Red
    theme_accent: int = 0xB22222        # Firebrick Red

    # Vampire Display Name for the bot
    bot_display_name: str = "🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞"


config = SecurityBotConfig()
