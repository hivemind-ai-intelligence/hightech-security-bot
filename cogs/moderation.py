"""
Cog: Moderation — Hybrid commands + text prefix fallback.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import discord
from discord.ext import commands

from config.settings import config

logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    """🛡️ Server moderation — bans, kicks, mutes, purging, and anti-spam."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_tracker: Dict[int, list] = {}
        self.spam_warnings: Dict[int, int] = {}

    def _get_audit_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        cfg = self.bot.get_cog("ServerConfig")
        if cfg:
            return cfg.get_channel(guild, "audit_log_channel")
        return None

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed):
        ch = self._get_audit_channel(guild)
        if ch:
            try:
                await ch.send(embed=embed)
            except discord.Forbidden:
                pass

    # ── Events ──────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if message.author.guild_permissions.administrator:
            return
        await self._check_banned_keywords(message)
        await self._check_spam(message)

    async def _check_banned_keywords(self, message: discord.Message):
        for pattern in config.banned_keywords:
            if re.search(pattern, message.content, re.IGNORECASE):
                await message.delete()
                try:
                    await message.author.send(embed=discord.Embed(
                        title="⚠️ Message Removed",
                        description=f"Your message in **{message.guild.name}** violated security policy.\n**Pattern:** `{pattern}`",
                        color=config.theme_warning,
                    ))
                except discord.Forbidden:
                    pass
                return

    async def _check_spam(self, message: discord.Message):
        uid = message.author.id
        now = datetime.now(timezone.utc)
        if uid not in self.message_tracker:
            self.message_tracker[uid] = []
        cutoff = now - timedelta(seconds=5)
        self.message_tracker[uid] = [t for t in self.message_tracker[uid] if t > cutoff]
        self.message_tracker[uid].append(now)
        if len(self.message_tracker[uid]) > config.max_messages_per_second * 5:
            try:
                await message.author.timeout(timedelta(minutes=config.mute_duration_minutes), reason="Spam detected")
            except discord.Forbidden:
                pass

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="purge", description="Bulk-delete messages from this channel")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int = 10):
        if amount < 1 or amount > 500:
            await ctx.send("⚠️ Amount must be 1-500.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"🗑️ Deleted **{len(deleted) - 1}** messages.", ephemeral=True, delete_after=5)

    @commands.hybrid_command(name="warn", description="Formally warn a user")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            await member.send(embed=discord.Embed(
                title="⚠️ Security Warning",
                description=f"You were warned in **{ctx.guild.name}**.",
                color=config.theme_warning,
            ).add_field(name="Reason", value=reason).set_footer(text=f"Moderator: {ctx.author}"))
        except discord.Forbidden:
            pass
        await ctx.send(f"⚠️ Warned {member.mention} — {reason}")

    @commands.hybrid_command(name="mute", description="Timeout a user")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, minutes: int = 15, *, reason: str = "No reason"):
        minutes = min(minutes, 40320)
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"🔇 Muted {member.mention} for **{minutes} min** — {reason}")

    @commands.hybrid_command(name="unmute", description="Remove timeout from a user")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None)
        await ctx.send(f"🔊 Unmuted {member.mention}")

    @commands.hybrid_command(name="kick", description="Kick a user from the server")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        await member.kick(reason=reason)
        await ctx.send(f"👢 Kicked **{member}** — {reason}")

    @commands.hybrid_command(name="ban", description="Ban a user from the server")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"):
        await member.ban(reason=reason, delete_message_days=1)
        await ctx.send(f"🔨 Banned **{member}** — {reason}")

    @commands.hybrid_command(name="unban", description="Unban a user by ID")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason"):
        await ctx.guild.unban(user, reason=reason)
        await ctx.send(f"✅ Unbanned **{user}** — {reason}")

    @commands.hybrid_command(name="nuke", description="Clone and recreate a channel (clear all messages)")
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx: commands.Context):
        await ctx.defer()
        channel = ctx.channel
        new_channel = await channel.clone(reason=f"Nuked by {ctx.author}")
        await new_channel.edit(position=channel.position)
        await channel.delete(reason=f"Nuked by {ctx.author}")
        await new_channel.send(f"💥 Channel nuked by {ctx.author.mention} — fresh start!")

    @commands.hybrid_command(name="softban", description="Ban and immediately unban to clear messages")
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Softban"):
        await member.ban(reason=reason, delete_message_days=7)
        await ctx.guild.unban(member, reason=reason)
        await ctx.send(f"🧹 Softbanned **{member}** — messages cleared.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
