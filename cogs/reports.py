"""
Cog: Reports — Security analytics, user reports, message stats.
Generates server security health reports and activity summaries.
"""

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from config.settings import config
from utils.helpers import make_embed, format_duration

logger = logging.getLogger(__name__)


class Reports(commands.Cog):
    """📊 Security analytics, user reports & activity summaries."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="server_info", description="Detailed server security information")
    @commands.has_permissions(moderate_members=True)
    async def server_info(self, ctx: commands.Context):
        """Display comprehensive server security info."""
        guild = ctx.guild

        # Role counts
        admin_count = sum(1 for m in guild.members if m.guild_permissions.administrator)
        bot_count = sum(1 for m in guild.members if m.bot)
        human_count = guild.member_count - bot_count

        # Channel stats
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)

        # Verification level
        verification = str(guild.verification_level).title().replace("_", " ")

        # Join dates — new members in last 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        new_members = sum(1 for m in guild.members if m.joined_at and m.joined_at > cutoff)

        # Security score
        security_score = 100
        if guild.verification_level.value < 3:
            security_score -= 20
        if not guild.mfa_level:
            security_score -= 15
        if guild.default_notifications.value == 0:
            security_score -= 10

        score_color = (
            config.theme_danger if security_score < 50
            else config.theme_warning if security_score < 75
            else config.theme_accent
        )

        embed = discord.Embed(
            title=f"🦇 Server Security — {guild.name}",
            color=score_color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        embed.add_field(name="Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, "R"), inline=True)
        embed.add_field(name="Security Score", value=f"{security_score}/100", inline=True)
        embed.add_field(name="Members", value=f"{human_count} humans + {bot_count} bots", inline=True)
        embed.add_field(name="Admins", value=str(admin_count), inline=True)
        embed.add_field(name="New (7d)", value=str(new_members), inline=True)
        embed.add_field(name="Channels", value=f"{text_channels} text | {voice_channels} voice", inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Verification", value=verification, inline=True)
        embed.add_field(name="2FA Required", value="✅" if guild.mfa_level else "❌", inline=True)

        # Security recommendations
        recommendations = []
        if guild.verification_level.value < 3:
            recommendations.append("⬆️ Increase verification level to 'Highest'")
        if not guild.mfa_level:
            recommendations.append("🔐 Enable 2FA requirement for moderators")
        if new_members > 10:
            recommendations.append("👀 High new member influx — monitor for raids")

        if recommendations:
            embed.add_field(
                name="🔧 Recommendations",
                value="\n".join(f"• {r}" for r in recommendations),
                inline=False,
            )

        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Server Security Audit")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="user_info", description="Get detailed info about a user")
    @commands.has_permissions(moderate_members=True)
    async def user_info(self, ctx: commands.Context, member: discord.Member):
        """Display comprehensive user information."""
        # Account age
        account_age = (datetime.now(timezone.utc) - member.created_at).days
        server_age = (datetime.now(timezone.utc) - member.joined_at).days if member.joined_at else 0

        # Role hierarchy position
        top_role = member.top_role

        # Key permissions
        perms = member.guild_permissions
        key_perms = []
        if perms.administrator: key_perms.append("👑 Administrator")
        if perms.ban_members: key_perms.append("🔨 Ban")
        if perms.kick_members: key_perms.append("👢 Kick")
        if perms.manage_messages: key_perms.append("🗑️ Manage Msgs")
        if perms.manage_channels: key_perms.append("📝 Manage Channels")
        if perms.manage_roles: key_perms.append("🔑 Manage Roles")

        risk_level = "🟢 Low"
        if account_age < 7:
            risk_level = "🔴 High (New Account)"
        elif account_age < 30:
            risk_level = "🟡 Medium"

        embed = discord.Embed(
            title=f"👤 User Info — {member}",
            color=member.top_role.color if member.top_role.color.value else config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Top Role", value=top_role.mention, inline=True)
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        embed.add_field(name="Server Joined", value=discord.utils.format_dt(member.joined_at, "R"), inline=True)
        embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
        embed.add_field(name="Risk Level", value=risk_level, inline=True)
        embed.add_field(name="Bot", value="🤖 Yes" if member.bot else "👤 Human", inline=True)
        embed.add_field(name="Status", value=str(member.status).title(), inline=True)

        roles = [r.mention for r in reversed(member.roles[1:6])]
        embed.add_field(name=f"Roles ({len(member.roles) - 1})", value=" ".join(roles) or "None", inline=False)

        if key_perms:
            embed.add_field(name="Key Permissions", value=" | ".join(key_perms), inline=False)

        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • User Intelligence")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="channel_stats", description="Show channel activity statistics")
    @commands.has_permissions(moderate_members=True)
    async def channel_stats(self, ctx: commands.Context):
        """Display channel activity overview."""
        embed = discord.Embed(
            title=f"📊 Channel Overview — {ctx.guild.name}",
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )

        categories = {
            "total_text": 0, "total_voice": 0,
            "public_channels": 0, "private_channels": 0,
            "locked_channels": 0,
        }

        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel):
                categories["total_text"] += 1
                perms = channel.permissions_for(ctx.guild.default_role)
                if not perms.read_messages:
                    categories["private_channels"] += 1
                else:
                    categories["public_channels"] += 1
                if not perms.send_messages:
                    categories["locked_channels"] += 1
            elif isinstance(channel, discord.VoiceChannel):
                categories["total_voice"] += 1

        embed.add_field(name="Text Channels", value=str(categories["total_text"]), inline=True)
        embed.add_field(name="Voice Channels", value=str(categories["total_voice"]), inline=True)
        embed.add_field(name="Public", value=str(categories["public_channels"]), inline=True)
        embed.add_field(name="Private", value=str(categories["private_channels"]), inline=True)
        embed.add_field(name="Locked", value=str(categories["locked_channels"]), inline=True)
        embed.add_field(name="Categories", value=str(len(ctx.guild.categories)), inline=True)

        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Channel Analytics")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="role_list", description="List all roles with member counts")
    @commands.has_permissions(moderate_members=True)
    async def role_list(self, ctx: commands.Context):
        """Show all server roles and their member counts."""
        embed = discord.Embed(
            title=f"🔑 Role List — {ctx.guild.name}",
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )

        roles_sorted = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)

        for role in roles_sorted[:25]:  # Max 25 embed fields
            if role.is_default():
                embed.add_field(
                    name=f"@{role.name}",
                    value=f"{len(role.members)} members",
                    inline=True,
                )
            else:
                embed.add_field(
                    name=role.name,
                    value=f"{len(role.members)} members | {role.mention}",
                    inline=True,
                )

        if len(roles_sorted) > 25:
            embed.set_footer(text=f"Showing 25 of {len(roles_sorted)} roles • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        else:
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Role Analytics")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="activity_report", description="Generate a server activity report (24h)")
    @commands.has_permissions(moderate_members=True)
    async def activity_report(self, ctx: commands.Context):
        """Quick server activity snapshot."""
        guild = ctx.guild

        online = sum(1 for m in guild.members if m.status == discord.Status.online)
        idle = sum(1 for m in guild.members if m.status == discord.Status.idle)
        dnd = sum(1 for m in guild.members if m.status == discord.Status.do_not_disturb)
        offline = sum(1 for m in guild.members if m.status == discord.Status.offline)

        embed = discord.Embed(
            title=f"📊 Activity Report — {guild.name}",
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="🟢 Online", value=str(online), inline=True)
        embed.add_field(name="🟡 Idle", value=str(idle), inline=True)
        embed.add_field(name="🔴 DND", value=str(dnd), inline=True)
        embed.add_field(name="⚫ Offline", value=str(offline), inline=True)
        embed.add_field(name="Total", value=str(guild.member_count), inline=True)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Activity Snapshot")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="audit_report", description="Recent server audit log summary")
    @commands.has_permissions(view_audit_log=True)
    async def audit_report(self, ctx: commands.Context):
        """Show a summary of recent audit log actions."""
        actions = Counter()
        async for entry in ctx.guild.audit_logs(limit=100):
            action_name = entry.action.name.replace("_", " ").title()
            actions[action_name] += 1

        if not actions:
            await ctx.send("No audit log entries found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Recent Audit Log Summary",
            description="Last 100 audit log actions:\n\n" + "\n".join(
                f"• **{action}**: {count}" for action, count in actions.most_common(15)
            ),
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Audit Summary")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reports(bot))
