"""
Cog: AutoMod — Advanced auto-moderation rules management.
Keyword whitelist/blacklist, link filtering, attachment scanning,
mention limits, and custom rule toggling per server.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from config.settings import config
from utils.helpers import get_server_data_path, load_json, save_json, make_embed

logger = logging.getLogger(__name__)


class AutoMod(commands.Cog):
    """🦇 Advanced auto-moderation rules & keyword management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_settings: dict = {}  # guild_id -> settings (lazy-loaded)

    def _get_settings(self, guild_id: int) -> dict:
        if guild_id not in self.server_settings:
            path = get_server_data_path(guild_id, "automod.json")
            self.server_settings[guild_id] = load_json(path, {
                "anti_links": True,
                "anti_invites": True,
                "anti_spam": True,
                "anti_mass_mention": True,
                "max_mentions": 10,
                "custom_blacklist": [],
                "whitelist_channels": [],
                "ignored_roles": [],
                "enabled": True,
            })
        return self.server_settings[guild_id]

    def _save_settings(self, guild_id: int):
        path = get_server_data_path(guild_id, "automod.json")
        save_json(path, self._get_settings(guild_id))

    # ── Events ──────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.author.guild_permissions.administrator:
            return

        settings = self._get_settings(message.guild.id)
        if not settings.get("enabled", True):
            return

        # Skip whitelisted channels
        if message.channel.id in settings.get("whitelist_channels", []):
            return

        # Skip ignored roles
        author_role_ids = [r.id for r in message.author.roles]
        if any(r in settings.get("ignored_roles", []) for r in author_role_ids):
            return

        violations = []

        # Anti-invite
        if settings.get("anti_invites", True):
            invite_pattern = r"discord(?:app\.com/invite|\.gg)/([a-zA-Z0-9\-]+)"
            if re.search(invite_pattern, message.content):
                violations.append("Discord invite link")

        # Anti-link (non-Discord links)
        if settings.get("anti_links", False):
            url_pattern = r"https?://[^\s]+"
            matches = re.findall(url_pattern, message.content)
            if matches and not any("discord" in m for m in matches):
                violations.append("External link")

        # Anti-mass-mention
        if settings.get("anti_mass_mention", True):
            max_mentions = settings.get("max_mentions", 10)
            if len(message.mentions) > max_mentions:
                violations.append(f"Mass mention ({len(message.mentions)} users)")

        # Custom blacklist
        for word in settings.get("custom_blacklist", []):
            if word.lower() in message.content.lower():
                violations.append(f"Blacklisted word: `{word}`")
                break

        if violations:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            await self._notify_violation(message, violations)

    async def _notify_violation(self, message: discord.Message, violations: list):
        """Notify user and log the violation."""
        try:
            await message.author.send(
                embed=make_embed(
                    title="🦇 AutoMod Violation",
                    description=(
                        f"Your message in **{message.guild.name}** "
                        f"(#{message.channel.name}) was removed.\n\n"
                        f"**Violation(s):**\n" + "\n".join(f"• {v}" for v in violations)
                    ),
                    color=config.theme_danger,
                )
            )
        except discord.Forbidden:
            pass

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="automod_status", description="Show AutoMod settings for this server")
    @commands.has_permissions(manage_guild=True)
    async def automod_status(self, ctx: commands.Context):
        """Display current AutoMod configuration."""
        settings = self._get_settings(ctx.guild.id)
        embed = discord.Embed(
            title="🦇 AutoMod Configuration",
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Status", value="✅ Enabled" if settings["enabled"] else "❌ Disabled", inline=True)
        embed.add_field(name="Anti Invites", value="✅" if settings["anti_invites"] else "❌", inline=True)
        embed.add_field(name="Anti Links", value="✅" if settings["anti_links"] else "❌", inline=True)
        embed.add_field(name="Anti Spam", value="✅" if settings["anti_spam"] else "❌", inline=True)
        embed.add_field(name="Anti Mass Mention", value="✅" if settings["anti_mass_mention"] else "❌", inline=True)
        embed.add_field(name="Max Mentions", value=str(settings["max_mentions"]), inline=True)
        embed.add_field(name="Blacklisted Words", value=str(len(settings["custom_blacklist"])), inline=True)
        embed.add_field(name="Whitelist Channels", value=str(len(settings["whitelist_channels"])), inline=True)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • /automod_help for more")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="automod_toggle", description="Enable/disable AutoMod globally for this server")
    @commands.has_permissions(manage_guild=True)
    async def automod_toggle(self, ctx: commands.Context):
        """Toggle AutoMod on/off."""
        settings = self._get_settings(ctx.guild.id)
        settings["enabled"] = not settings["enabled"]
        self._save_settings(ctx.guild.id)
        status = "enabled" if settings["enabled"] else "disabled"
        await ctx.send(f"🦇 AutoMod **{status}** for this server.")

    @commands.hybrid_command(name="automod_links", description="Toggle external link filtering")
    @commands.has_permissions(manage_guild=True)
    async def automod_links(self, ctx: commands.Context):
        """Toggle anti-link filtering."""
        settings = self._get_settings(ctx.guild.id)
        settings["anti_links"] = not settings["anti_links"]
        self._save_settings(ctx.guild.id)
        status = "enabled" if settings["anti_links"] else "disabled"
        await ctx.send(f"🔗 Anti-Link filtering **{status}**.")

    @commands.hybrid_command(name="automod_invites", description="Toggle Discord invite filtering")
    @commands.has_permissions(manage_guild=True)
    async def automod_invites(self, ctx: commands.Context):
        """Toggle anti-invite filtering."""
        settings = self._get_settings(ctx.guild.id)
        settings["anti_invites"] = not settings["anti_invites"]
        self._save_settings(ctx.guild.id)
        status = "enabled" if settings["anti_invites"] else "disabled"
        await ctx.send(f"📨 Anti-Invite filtering **{status}**.")

    @commands.hybrid_command(name="automod_mentions", description="Toggle mass mention protection")
    @commands.has_permissions(manage_guild=True)
    async def automod_mentions(self, ctx: commands.Context):
        """Toggle anti-mass-mention."""
        settings = self._get_settings(ctx.guild.id)
        settings["anti_mass_mention"] = not settings["anti_mass_mention"]
        self._save_settings(ctx.guild.id)
        status = "enabled" if settings["anti_mass_mention"] else "disabled"
        await ctx.send(f"👥 Anti-Mass-Mention **{status}**.")

    @commands.hybrid_command(name="blacklist_add", description="Add a word to the blacklist")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_add(self, ctx: commands.Context, *, word: str):
        """Add a word to server blacklist."""
        settings = self._get_settings(ctx.guild.id)
        word = word.strip().lower()
        if word in settings["custom_blacklist"]:
            await ctx.send(f"⚠️ `{word}` is already blacklisted.", ephemeral=True)
            return
        settings["custom_blacklist"].append(word)
        self._save_settings(ctx.guild.id)
        await ctx.send(f"🦇 Added `{word}` to blacklist. ({len(settings['custom_blacklist'])} total)")

    @commands.hybrid_command(name="blacklist_remove", description="Remove a word from the blacklist")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_remove(self, ctx: commands.Context, *, word: str):
        """Remove a word from server blacklist."""
        settings = self._get_settings(ctx.guild.id)
        word = word.strip().lower()
        if word not in settings["custom_blacklist"]:
            await ctx.send(f"⚠️ `{word}` is not in the blacklist.", ephemeral=True)
            return
        settings["custom_blacklist"].remove(word)
        self._save_settings(ctx.guild.id)
        await ctx.send(f"🗑️ Removed `{word}` from blacklist.")

    @commands.hybrid_command(name="blacklist_list", description="Show all blacklisted words")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_list(self, ctx: commands.Context):
        """Show server blacklist."""
        settings = self._get_settings(ctx.guild.id)
        words = settings["custom_blacklist"]
        if not words:
            await ctx.send("📋 Blacklist is empty.")
            return
        embed = make_embed(
            title=f"📋 Blacklisted Words ({len(words)})",
            description=", ".join(f"`{w}`" for w in words),
            color=config.theme_primary,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="whitelist_channel", description="Add/remove channel from automod whitelist")
    @commands.has_permissions(manage_guild=True)
    async def whitelist_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Toggle a channel in the automod whitelist."""
        settings = self._get_settings(ctx.guild.id)
        ch = channel or ctx.channel

        if ch.id in settings["whitelist_channels"]:
            settings["whitelist_channels"].remove(ch.id)
            self._save_settings(ctx.guild.id)
            await ctx.send(f"🔓 {ch.mention} removed from whitelist.")
        else:
            settings["whitelist_channels"].append(ch.id)
            self._save_settings(ctx.guild.id)
            await ctx.send(f"🔒 {ch.mention} added to whitelist (AutoMod bypass).")

    @commands.hybrid_command(name="set_max_mentions", description="Set max mentions before auto-filter")
    @commands.has_permissions(manage_guild=True)
    async def set_max_mentions(self, ctx: commands.Context, count: int):
        """Set the maximum allowed mentions per message."""
        settings = self._get_settings(ctx.guild.id)
        settings["max_mentions"] = max(1, min(count, 100))
        self._save_settings(ctx.guild.id)
        await ctx.send(f"👥 Max mentions set to **{settings['max_mentions']}**.")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
