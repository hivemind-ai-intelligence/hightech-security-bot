"""
🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 Discord Bot — Main Entry Point
Global bot — 64+ Security + 29 Music Commands
"""

import asyncio
import logging
import os
import sys
import traceback
from pathlib import Path

import discord
from discord.ext import commands

# ── Logging ─────────────────────────────────────────────────
Path("data").mkdir(exist_ok=True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("hightech-bot")

# ── Load settings ──────────────────────────────────────────
from config.settings import config

# ── Bot Setup ───────────────────────────────────────────────
class SecurityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.bot_prefix),
            intents=intents,
            case_insensitive=True,
        )

    async def setup_hook(self):
        """Load cogs and sync commands."""
        cogs = [
            "cogs.moderation", "cogs.automod", "cogs.verification",
            "cogs.threat_intel", "cogs.incident_alerts", "cogs.audit_logging",
            "cogs.anti_raid", "cogs.admin", "cogs.help", "cogs.music",
            "cogs.reports", "cogs.backup", "cogs.server_config",
        ]
        ok = 0
        for c in cogs:
            try:
                await self.load_extension(c)
                ok += 1
                logger.info(f"  ✓ {c}")
            except Exception as e:
                logger.error(f"  ✗ {c}: {e}")
                traceback.print_exc()
        
        logger.info(f"📦 {ok}/{len(cogs)} cogs loaded")
        
        # Sync — Discord rate limits, so we just queue it
        try:
            await self.tree.sync()
            total = len(self.tree.get_commands())
            logger.info(f"🔄 {total} commands synced globally")
        except Exception as e:
            logger.warning(f"Sync delayed (rate limit): {e}")

    async def on_ready(self):
        total = len(self.tree.get_commands())
        logger.info(f"🦇 ONLINE as {self.user} ({self.user.id})")
        logger.info(f"   Guilds: {len(self.guilds)} | Cogs: {len(self.cogs)} | Commands: {total}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"🦇 {total} commands | /bot_help",
            )
        )

# ── Main ────────────────────────────────────────────────────
if __name__ == "__main__":
    token = config.bot_token or os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        logger.critical("❌ DISCORD_BOT_TOKEN not set!")
        sys.exit(1)

    logger.info(f"🔑 Token found ({len(token)} chars)")
    logger.info(f"🐍 Python {sys.version.split()[0]} | discord.py {discord.__version__}")

    # Diagnose
    try:
        import davey; logger.info("🔊 davey OK")
    except: logger.warning("⚠️ no davey")
    try:
        import yt_dlp; logger.info("🎵 yt-dlp OK")
    except: logger.warning("⚠️ no yt-dlp")
    try:
        import nacl; logger.info("🔐 PyNaCl OK")
    except: logger.warning("⚠️ no PyNaCl")

    bot = SecurityBot()
    bot.run(token)
