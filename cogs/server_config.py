"""
Cog: Server Config — per-server channel & role configuration.
Allows each server to set its own log channels via slash commands.
No hardcoded IDs needed!
"""

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config.settings import config
from utils.helpers import get_server_data_path, load_json, save_json, make_embed

logger = logging.getLogger(__name__)


class ServerConfig(commands.Cog):
    """⚙️ Per-server configuration — channels, roles, and settings."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_configs: dict = {}

    def _get_config(self, guild_id: int) -> dict:
        if guild_id not in self.server_configs:
            path = get_server_data_path(guild_id, "config.json")
            self.server_configs[guild_id] = load_json(path, {
                "audit_log_channel": None,
                "alert_channel": None,
                "incident_channel": None,
                "threat_intel_channel": None,
                "welcome_channel": None,
                "verified_role": None,
                "security_role": None,
                "admin_role": None,
            })
        return self.server_configs[guild_id]

    def _save_config(self, guild_id: int):
        path = get_server_data_path(guild_id, "config.json")
        save_json(path, self._get_config(guild_id))

    # ── Helper: Get a configured channel ────────────────

    def get_channel(self, guild: discord.Guild, key: str) -> discord.TextChannel | None:
        """Get a configured channel, falling back to global config."""
        cfg = self._get_config(guild.id)
        ch_id = cfg.get(key) or getattr(config, f"{key}_id", 0)
        return guild.get_channel(ch_id) if ch_id else None

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="setup", description="Interactive server setup wizard")
    @commands.has_permissions(manage_guild=True)
    async def setup(self, ctx: commands.Context):
        """Guided setup for configuring the bot on this server."""
        embed = discord.Embed(
            title="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — Server Setup",
            description=(
                "Welcome to the setup wizard! Configure the bot for your server:\n\n"
                "**Step 1:** Set log channels\n"
                f"• `/config_channel audit_log #channel`\n"
                f"• `/config_channel alert #channel`\n"
                f"• `/config_channel incident #channel`\n\n"
                "**Step 2:** Set roles (optional)\n"
                f"• `/config_role verified @role`\n"
                f"• `/config_role security @role`\n\n"
                "**Step 3:** Configure AutoMod\n"
                f"• `/automod_status` — View settings\n"
                f"• `/automod_toggle` — Enable/disable\n"
                f"• `/blacklist_add <word>` — Add filtered words\n\n"
                "**Step 4:** Set up verification\n"
                f"• `/verification_setup` — Configure verification\n\n"
                f"Use `/config_view` to see all current settings."
            ),
            color=config.theme_primary,
        )
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Global Security Bot")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="config_view", description="View current server configuration")
    @commands.has_permissions(manage_guild=True)
    async def config_view(self, ctx: commands.Context):
        """Show all configured channels and roles for this server."""
        cfg = self._get_config(ctx.guild.id)
        embed = discord.Embed(
            title=f"⚙️ Server Config — {ctx.guild.name}",
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )

        channels = {
            "audit_log_channel": "📋 Audit Log",
            "alert_channel": "🚨 Alerts",
            "incident_channel": "🔴 Incidents",
            "threat_intel_channel": "🔎 Threat Intel",
            "welcome_channel": "👋 Welcome",
        }
        for key, label in channels.items():
            ch_id = cfg.get(key)
            ch = ctx.guild.get_channel(ch_id) if ch_id else None
            embed.add_field(name=label, value=ch.mention if ch else "❌ Not set", inline=True)

        roles = {
            "verified_role": "✅ Verified",
            "security_role": "🛡️ Security Team",
            "admin_role": "👑 Admin",
        }
        for key, label in roles.items():
            r_id = cfg.get(key)
            role = ctx.guild.get_role(r_id) if r_id else None
            embed.add_field(name=label, value=role.mention if role else "❌ Not set", inline=True)

        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • /config_channel to set")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="config_channel", description="Set a log channel (audit_log/alert/incident/threat_intel/welcome)")
    @commands.has_permissions(manage_guild=True)
    async def config_channel(
        self,
        ctx: commands.Context,
        channel_type: str,
        channel: discord.TextChannel = None,
    ):
        """Configure a channel for a specific purpose."""
        valid_types = ["audit_log", "alert", "incident", "threat_intel", "welcome"]
        ch = channel or ctx.channel

        key_map = {
            "audit_log": "audit_log_channel",
            "alert": "alert_channel",
            "incident": "incident_channel",
            "threat_intel": "threat_intel_channel",
            "welcome": "welcome_channel",
        }

        if channel_type.lower() not in valid_types:
            await ctx.send(f"❌ Invalid type. Options: {', '.join(valid_types)}", ephemeral=True)
            return

        key = key_map[channel_type.lower()]
        cfg = self._get_config(ctx.guild.id)
        cfg[key] = ch.id
        self._save_config(ctx.guild.id)

        labels = {
            "audit_log_channel": "Audit Log",
            "alert_channel": "Alerts",
            "incident_channel": "Incidents",
            "threat_intel_channel": "Threat Intel",
            "welcome_channel": "Welcome",
        }
        await ctx.send(f"✅ **{labels[key]}** channel set to {ch.mention}")

    @commands.hybrid_command(name="config_role", description="Set a role (verified/security/admin)")
    @commands.has_permissions(manage_guild=True)
    async def config_role(self, ctx: commands.Context, role_type: str, role: discord.Role):
        """Configure a role for the bot."""
        valid_types = ["verified", "security", "admin"]
        key_map = {
            "verified": "verified_role",
            "security": "security_role",
            "admin": "admin_role",
        }

        if role_type.lower() not in valid_types:
            await ctx.send(f"❌ Invalid type. Options: {', '.join(valid_types)}", ephemeral=True)
            return

        key = key_map[role_type.lower()]
        cfg = self._get_config(ctx.guild.id)
        cfg[key] = role.id
        self._save_config(ctx.guild.id)

        labels = {"verified_role": "Verified", "security_role": "Security Team", "admin_role": "Admin"}
        await ctx.send(f"✅ **{labels[key]}** role set to {role.mention}")

    @commands.hybrid_command(name="config_reset", description="Reset all server configuration")
    @commands.has_permissions(administrator=True)
    async def config_reset(self, ctx: commands.Context):
        """Reset this server's config to defaults."""
        path = get_server_data_path(ctx.guild.id, "config.json")
        if path.exists():
            path.unlink()
        self.server_configs.pop(ctx.guild.id, None)
        await ctx.send("🔄 Server configuration reset to defaults.")


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerConfig(bot))
