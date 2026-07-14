"""
Cog: Anti-Raid — automated raid detection & server lockdown.
Uses per-server config for alert channels.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands, tasks

from config.settings import config

logger = logging.getLogger(__name__)


class AntiRaid(commands.Cog):
    """🛡️ Automated raid detection & server lockdown — per server."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.server_joins: dict = {}      # guild_id -> deque of join timestamps
        self.raid_mode: dict = {}          # guild_id -> bool
        self.lockdown_channels: dict = {}  # guild_id -> set of channel_ids
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    def _get_channel(self, guild: discord.Guild, key: str) -> Optional[discord.TextChannel]:
        cfg = self.bot.get_cog("ServerConfig")
        if cfg:
            return cfg.get_channel(guild, key)
        return None

    async def _log(self, guild: discord.Guild, title: str, description: str, color: int):
        channel = self._get_channel(guild, "alert_channel")
        if not channel:
            return
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Anti-Raid")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ── Events ──────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        now = datetime.now(timezone.utc)

        if guild.id not in self.server_joins:
            self.server_joins[guild.id] = deque()
            self.raid_mode[guild.id] = False
            self.lockdown_channels[guild.id] = set()

        self.server_joins[guild.id].append(now)
        cutoff = now - timedelta(seconds=config.raid_detection_window)
        while self.server_joins[guild.id] and self.server_joins[guild.id][0] < cutoff:
            self.server_joins[guild.id].popleft()

        if len(self.server_joins[guild.id]) >= config.raid_detection_threshold and not self.raid_mode[guild.id]:
            await self._trigger_raid_mode(guild)

    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=config.raid_detection_window * 2)
        for gid, joins in self.server_joins.items():
            while joins and joins[0] < cutoff:
                joins.popleft()

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="lockdown", description="Toggle full server lockdown")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx: commands.Context):
        guild = ctx.guild
        if guild.id not in self.raid_mode:
            self.raid_mode[guild.id] = False
            self.lockdown_channels[guild.id] = set()

        if self.raid_mode[guild.id]:
            self.raid_mode[guild.id] = False
            for ch_id in list(self.lockdown_channels[guild.id]):
                channel = guild.get_channel(ch_id)
                if channel:
                    await channel.set_permissions(guild.default_role, send_messages=None, reason="Lockdown lifted")
            self.lockdown_channels[guild.id].clear()
            await ctx.send("🔓 **Lockdown lifted.** All channels restored.")
            await self._log(guild, "🔓 Lockdown Lifted", f"Lifted by {ctx.author}", config.theme_accent)
        else:
            self.raid_mode[guild.id] = True
            locked = 0
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False, reason="Raid lockdown")
                    self.lockdown_channels[guild.id].add(channel.id)
                    locked += 1
                except discord.Forbidden:
                    pass
            await ctx.send(f"🔒 **LOCKDOWN ACTIVE** — {locked} channels locked. Use `/lockdown` to lift.")
            await self._log(guild, "🔒 Lockdown Activated", f"By {ctx.author} • {locked} channels", config.theme_danger)

    @commands.hybrid_command(name="raid_status", description="Check raid detection status")
    @commands.has_permissions(moderate_members=True)
    async def raid_status(self, ctx: commands.Context):
        gid = ctx.guild.id
        mode = self.raid_mode.get(gid, False)
        joins = len(self.server_joins.get(gid, deque()))
        locked = len(self.lockdown_channels.get(gid, set()))

        embed = discord.Embed(
            title="🛡️ Anti-Raid Status",
            color=config.theme_danger if mode else config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Raid Mode", value="🔴 ACTIVE" if mode else "🟢 Inactive", inline=True)
        embed.add_field(name="Recent Joins", value=f"{joins} in {config.raid_detection_window}s", inline=True)
        embed.add_field(name="Threshold", value=f"{config.raid_detection_threshold} per {config.raid_detection_window}s", inline=True)
        embed.add_field(name="Locked Channels", value=str(locked), inline=True)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Anti-Raid Protection")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="lock_channel", description="Lock a specific channel")
    @commands.has_permissions(manage_channels=True)
    async def lock_channel(self, ctx: commands.Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"Locked by {ctx.author}")
        await ctx.send("🔒 Channel locked.")
        await self._log(ctx.guild, "🔒 Channel Locked", f"{ctx.channel.mention} locked by {ctx.author}", config.theme_warning)

    @commands.hybrid_command(name="unlock_channel", description="Unlock the current channel")
    @commands.has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx: commands.Context):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None, reason=f"Unlocked by {ctx.author}")
        await ctx.send("🔓 Channel unlocked.")
        await self._log(ctx.guild, "🔓 Channel Unlocked", f"{ctx.channel.mention} unlocked by {ctx.author}", config.theme_accent)

    @commands.hybrid_command(name="slowmode", description="Set slowmode for the channel")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int = 5):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"⏱️ Slowmode set to **{seconds} seconds**.")
        await self._log(ctx.guild, "⏱️ Slowmode Set", f"{seconds}s in {ctx.channel.mention} by {ctx.author}", config.theme_primary)

    async def _trigger_raid_mode(self, guild: discord.Guild):
        self.raid_mode[guild.id] = True
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(guild.default_role, send_messages=False, reason="Automatic raid detection")
                self.lockdown_channels[guild.id].add(channel.id)
            except discord.Forbidden:
                pass

        alert_channel = self._get_channel(guild, "alert_channel")
        if alert_channel:
            embed = discord.Embed(
                title="🚨 RAID DETECTED — Auto Lockdown",
                description=(
                    f"**{len(self.server_joins[guild.id])} users** joined in "
                    f"{config.raid_detection_window}s.\nUse `/lockdown` to lift when safe."
                ),
                color=config.theme_danger,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Auto Protection")
            await alert_channel.send("@here", embed=embed)

        logger.warning(f"Raid detected in {guild.name}: {len(self.server_joins[guild.id])} joins")


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiRaid(bot))
