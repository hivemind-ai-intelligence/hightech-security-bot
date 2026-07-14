"""
🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 Discord Bot — Main Entry Point
Global bot — works on ANY Discord server without hardcoded IDs.
64+ Security Commands + 29 Music Commands = 93+ total.
"""

import asyncio
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import discord
from discord.ext import commands

from config.settings import config

# ── Logging Setup ───────────────────────────────────────────
Path("data").mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("hightech-security-bot")


# ── Health Check Server (Render needs port binding) ──────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, *args):
        pass  # silent

def start_health_server():
    port = int(os.getenv("PORT", "8080"))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info(f"💚 Health server on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Health server failed: {e}")


# ── Bot Setup ───────────────────────────────────────────────
class SecurityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.bot_prefix),
            intents=intents,
            case_insensitive=True,
            description="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — 93+ Global Commands",
        )

    async def setup_hook(self):
        """Load all 13 cogs and sync global slash commands."""
        cog_files = [
            "cogs.moderation",
            "cogs.automod",
            "cogs.verification",
            "cogs.threat_intel",
            "cogs.incident_alerts",
            "cogs.audit_logging",
            "cogs.anti_raid",
            "cogs.admin",
            "cogs.help",
            "cogs.music",
            "cogs.reports",
            "cogs.backup",
            "cogs.server_config",
        ]
        loaded = 0
        for cog in cog_files:
            try:
                await self.load_extension(cog)
                loaded += 1
                logger.info(f"✓ {cog}")
            except Exception as e:
                logger.error(f"✗ {cog}: {e}")

        logger.info(f"📦 {loaded}/{len(cog_files)} cogs loaded, {len(self.cogs)} in registry")

        # Sync global slash commands
        try:
            synced = await self.tree.sync()
            # Count all commands across cogs
            total = sum(1 for c in self.tree.get_commands())
            logger.info(f"🔄 Synced {len(synced)} slash commands ({total} total)")
        except Exception as e:
            logger.error(f"✗ Sync failed: {e}")

    async def on_ready(self):
        total_cmds = sum(1 for c in self.tree.get_commands())
        logger.info(f"🦇 {self.user} (ID: {self.user.id}) ONLINE")
        logger.info(f"   Servers: {len(self.guilds)} | Users: {sum(g.member_count for g in self.guilds)}")
        logger.info(f"   Commands: {total_cmds} global | Cogs: {len(self.cogs)}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"🎵 /play | 🛡️ {total_cmds} commands",
            )
        )

    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"📥 Joined: {guild.name} ({guild.member_count} members)")
        channel = guild.system_channel
        if not channel:
            perms = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
            channel = perms[0] if perms else None
        if channel:
            embed = discord.Embed(
                title="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — Activated",
                description=(
                    "**Enterprise Discord Security Bot** 🩸\n\n"
                    "• `/bot_help` — All 93+ commands\n"
                    "• `/music_help` — 29 music commands\n"
                    "• `/play song` — YouTube music, no premium!\n"
                    "• `/setup` — Auto-configuration\n\n"
                    "🔐 Security + 🎵 Music — All in one!"
                ),
                color=config.theme_primary,
            )
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Works globally")
            try: await channel.send(embed=embed)
            except: pass


# ── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if not config.bot_token:
        logger.critical("DISCORD_BOT_TOKEN not set!")
        sys.exit(1)

    # Start health server in background (for Render)
    threading.Thread(target=start_health_server, daemon=True).start()

    # Diagnose voice support
    try:
        import davey
        logger.info(f"🔊 Voice: davey {getattr(davey, '__version__', 'OK')}")
    except ImportError:
        logger.warning("⚠️ davey not installed — voice will error on /play")

    try:
        import nacl
        logger.info(f"🔐 NaCl: v{nacl.__version__}")
    except ImportError:
        logger.warning("⚠️ PyNaCl not installed")

    try:
        import yt_dlp
        logger.info(f"🎵 yt-dlp: v{yt_dlp.version.__version__}")
    except ImportError:
        logger.warning("⚠️ yt-dlp not installed")

    bot = SecurityBot()
    bot.run(config.bot_token)
