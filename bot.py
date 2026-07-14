"""
Hi-Tech Security Discord Bot — Main Entry Point
Global bot — works on ANY Discord server without hardcoded IDs.
"""

import asyncio
import logging
import sys
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


# ── Bot Setup ───────────────────────────────────────────────
class SecurityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.bot_prefix),
            intents=intents,
            case_insensitive=True,
            description="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — Global Discord Security Bot",
        )

    async def setup_hook(self):
        """Load all cogs on startup and sync global slash commands."""
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
        for cog in cog_files:
            try:
                await self.load_extension(cog)
                logger.info(f"✓ Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"✗ Failed to load cog {cog}: {e}")

        # Sync global slash commands — works on ALL servers
        try:
            synced = await self.tree.sync()
            logger.info(f"🔄 Synced {len(synced)} global slash commands")
        except Exception as e:
            logger.error(f"✗ Failed to sync commands: {e}")

    async def on_ready(self):
        logger.info(f"🦇 Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"   Servers: {len(self.guilds)} | Users: {sum(g.member_count for g in self.guilds)}")
        logger.info(f"   Global commands active — works on ALL servers")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 | /bot_help",
            )
        )

    async def on_guild_join(self, guild: discord.Guild):
        """When bot joins a new server, log and send welcome message."""
        logger.info(f"📥 Joined new server: {guild.name} (ID: {guild.id}) | Members: {guild.member_count}")

        # Try to send welcome in system channel or first text channel
        channel = guild.system_channel
        if not channel:
            perms = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
            channel = perms[0] if perms else None

        if channel:
            embed = discord.Embed(
                title="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — Activated",
                description=(
                    "Thank you for adding the **Hi-Tech Security Bot**! 🩸\n\n"
                    "**Quick Setup:**\n"
                    "• Use `/setup` for guided server configuration\n"
                    "• Use `/bot_help` to see all 42+ commands\n"
                    "• Use `/config_channel` to set log channels\n\n"
                    "🔐 Your server is now protected by enterprise-grade security."
                ),
                color=config.theme_primary,
            )
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Blood Red Edition")
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass


# ── Run ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if not config.bot_token:
        logger.critical("DISCORD_BOT_TOKEN environment variable not set!")
        sys.exit(1)

    bot = SecurityBot()
    bot.run(config.bot_token)
