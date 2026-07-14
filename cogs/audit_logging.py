"""
Cog: Audit Logging — comprehensive security event logging per-server.
Server admins configure their audit channel via /config_channel audit_log.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands

from config.settings import config

logger = logging.getLogger(__name__)


class AuditLogging(commands.Cog):
    """📋 Comprehensive security audit logging — per-server config."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_audit_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get audit channel from server config or global fallback."""
        server_cfg = self.bot.get_cog("ServerConfig")
        if server_cfg:
            ch = server_cfg.get_channel(guild, "audit_log_channel")
            if ch:
                return ch
        return self.bot.get_channel(config.audit_log_channel_id)

    # ── Message Events ──────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if not message.content and not message.attachments:
            return

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention} ({message.author})\n"
            f"**Channel:** {message.channel.mention}",
            color=config.theme_danger,
            timestamp=datetime.now(timezone.utc),
        )
        if message.content:
            embed.add_field(name="Content", value=message.content[:1024] or "[empty]", inline=False)
        if message.attachments:
            attach_list = "\n".join(a.url for a in message.attachments[:5])
            embed.add_field(name="Attachments", value=attach_list[:1024], inline=False)
        embed.set_footer(text=f"Message ID: {message.id} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot:
            return
        if before.content == after.content:
            return

        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}",
            color=config.theme_warning,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Before", value=before.content[:1024] or "[empty]", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "[empty]", inline=False)
        embed.set_footer(text=f"Message ID: {before.id} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(before.guild, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list):
        if not messages:
            return
        guild = messages[0].guild
        if not guild:
            return
        channel = messages[0].channel
        embed = discord.Embed(
            title="🗑️ Bulk Message Deletion",
            description=f"**Channel:** {channel.mention}\n**Count:** {len(messages)} messages",
            color=config.theme_danger,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(guild, embed)

    # ── Member Events ───────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        account_age = (datetime.now(timezone.utc) - member.created_at).days
        embed = discord.Embed(
            title="👋 Member Joined",
            description=f"{member.mention} ({member})",
            color=config.theme_accent,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        if account_age < 7:
            embed.add_field(name="⚠️ Warning", value="Account less than 7 days old — potential alt/raid", inline=False)
        await self._send_audit(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == member.id:
                embed = discord.Embed(
                    title="🔨 Member Banned",
                    description=f"**User:** {member} ({member.id})\n**Moderator:** {entry.user}\n**Reason:** {entry.reason or 'None'}",
                    color=config.theme_danger,
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
                await self._send_audit(member.guild, embed)
                return

        embed = discord.Embed(
            title="👋 Member Left / Kicked",
            description=f"**User:** {member} ({member.id})",
            color=config.theme_warning,
            timestamp=datetime.now(timezone.utc),
        )
        roles = ", ".join(r.name for r in member.roles[1:]) or "None"
        embed.add_field(name="Roles", value=roles[:1024], inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            if added or removed:
                embed = discord.Embed(
                    title="🔑 Roles Updated",
                    description=f"**User:** {after.mention} ({after})",
                    color=config.theme_primary,
                    timestamp=datetime.now(timezone.utc),
                )
                if added:
                    embed.add_field(name="➕ Added", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="➖ Removed", value=", ".join(r.mention for r in removed), inline=False)
                embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
                await self._send_audit(after.guild, embed)

        if before.nick != after.nick:
            embed = discord.Embed(
                title="🏷️ Nickname Changed",
                description=f"**User:** {after.mention}",
                color=config.theme_primary,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Before", value=before.nick or after.name, inline=True)
            embed.add_field(name="After", value=after.nick or after.name, inline=True)
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
            await self._send_audit(after.guild, embed)

    # ── Channel Events ──────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(
            title="📝 Channel Created",
            description=f"**Name:** {channel.mention}\n**Type:** {channel.type}",
            color=config.theme_accent,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"ID: {channel.id} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            description=f"**Name:** {channel.name}\n**Type:** {channel.type}",
            color=config.theme_danger,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"ID: {channel.id} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if hasattr(before, "topic") and before.topic != after.topic:
            changes.append("**Topic:** updated")
        if before.overwrites != after.overwrites:
            changes.append("**Permissions:** updated")
        if changes:
            embed = discord.Embed(
                title="🔧 Channel Updated",
                description=f"**Channel:** {after.mention}\n" + "\n".join(changes),
                color=config.theme_primary,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
            await self._send_audit(after.guild, embed)

    # ── Voice Events ────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return
        if before.channel and after.channel:
            embed = discord.Embed(
                title="🔊 Voice Moved",
                description=f"**User:** {member.mention}\n**From:** {before.channel.mention}\n**To:** {after.channel.mention}",
                color=config.theme_primary,
                timestamp=datetime.now(timezone.utc),
            )
        elif after.channel:
            embed = discord.Embed(
                title="🎙️ Voice Join",
                description=f"**User:** {member.mention}\n**Channel:** {after.channel.mention}",
                color=config.theme_accent,
                timestamp=datetime.now(timezone.utc),
            )
        elif before.channel:
            embed = discord.Embed(
                title="🔇 Voice Leave",
                description=f"**User:** {member.mention}\n**Channel:** {before.channel.mention}",
                color=config.theme_warning,
                timestamp=datetime.now(timezone.utc),
            )
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await self._send_audit(member.guild, embed)

    async def _send_audit(self, guild: discord.Guild, embed: discord.Embed):
        channel = self._get_audit_channel(guild)
        if not channel:
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Cannot send audit log to {channel.name} in {guild.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AuditLogging(bot))
