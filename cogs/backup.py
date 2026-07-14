"""
Cog: Backup — Server settings backup & restore.
Role backup, channel structure snapshot, server config export.
"""

import json
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config.settings import config
from utils.helpers import get_server_data_path, save_json, load_json, make_embed

logger = logging.getLogger(__name__)


class Backup(commands.Cog):
    """💾 Server configuration backup & restore utilities."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="backup_roles", description="Backup all server roles to a file")
    @commands.has_permissions(administrator=True)
    async def backup_roles(self, ctx: commands.Context):
        """Export all roles and their key permissions to JSON."""
        guild = ctx.guild
        roles_data = []

        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            roles_data.append({
                "name": role.name,
                "position": role.position,
                "color": str(role.color),
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "member_count": len(role.members),
            })

        path = get_server_data_path(guild.id, "backup_roles.json")
        save_json(path, {"guild": guild.name, "backup_date": str(datetime.now(timezone.utc)), "roles": roles_data})

        embed = make_embed(
            title="💾 Roles Backup Complete",
            description=f"Backed up **{len(roles_data)}** roles from **{guild.name}**.",
            color=config.theme_accent,
        )
        embed.add_field(name="File", value=f"`data/{guild.id}/backup_roles.json`", inline=False)
        embed.add_field(name="Date", value=str(datetime.now(timezone.utc))[:19], inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="backup_channels", description="Backup channel structure snapshot")
    @commands.has_permissions(administrator=True)
    async def backup_channels(self, ctx: commands.Context):
        """Export channel structure to JSON."""
        guild = ctx.guild
        channels_data = []

        for channel in guild.channels:
            ch_info = {
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
            }
            if isinstance(channel, discord.TextChannel):
                ch_info.update({
                    "topic": channel.topic,
                    "slowmode": channel.slowmode_delay,
                    "nsfw": channel.nsfw,
                })
            channels_data.append(ch_info)

        categories_data = []
        for cat in guild.categories:
            categories_data.append({
                "name": cat.name,
                "position": cat.position,
                "channels": [c.name for c in cat.channels],
            })

        data = {
            "guild": guild.name,
            "backup_date": str(datetime.now(timezone.utc)),
            "total_channels": len(channels_data),
            "categories": categories_data,
            "channels": channels_data,
        }

        path = get_server_data_path(guild.id, "backup_channels.json")
        save_json(path, data)

        embed = make_embed(
            title="💾 Channel Backup Complete",
            description=f"Backed up **{len(channels_data)}** channels from **{guild.name}**.",
            color=config.theme_accent,
        )
        embed.add_field(name="Categories", value=str(len(categories_data)), inline=True)
        embed.add_field(name="Total Channels", value=str(len(channels_data)), inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="backup_full", description="Full server backup (roles + channels + config)")
    @commands.has_permissions(administrator=True)
    async def backup_full(self, ctx: commands.Context):
        """Complete server backup."""
        guild = ctx.guild

        embed = make_embed(
            title="💾 Full Server Backup — In Progress...",
            description=f"Backing up **{guild.name}**...",
            color=config.theme_warning,
        )
        msg = await ctx.send(embed=embed)

        # Roles
        roles = []
        for r in sorted(guild.roles, key=lambda x: x.position, reverse=True):
            roles.append({"name": r.name, "position": r.position, "member_count": len(r.members)})

        # Channels
        channels = []
        for c in guild.channels:
            channels.append({"name": c.name, "type": str(c.type), "position": c.position})

        # Config
        cfg_path = get_server_data_path(guild.id, "config.json")
        server_cfg = load_json(cfg_path, {})

        data = {
            "guild_name": guild.name,
            "guild_id": guild.id,
            "backup_date": str(datetime.now(timezone.utc)),
            "member_count": guild.member_count,
            "owner": str(guild.owner),
            "roles": roles,
            "channels": channels,
            "bot_config": server_cfg,
        }

        path = get_server_data_path(guild.id, "backup_full.json")
        save_json(path, data)

        embed = make_embed(
            title="💾 Full Backup Complete ✅",
            description=f"Complete backup of **{guild.name}** saved.",
            color=config.theme_accent,
        )
        embed.add_field(name="Roles", value=str(len(roles)), inline=True)
        embed.add_field(name="Channels", value=str(len(channels)), inline=True)
        embed.add_field(name="File", value=f"`data/{guild.id}/backup_full.json`", inline=False)

        await msg.edit(embed=embed)

    @commands.hybrid_command(name="backup_list", description="List available backups for this server")
    @commands.has_permissions(administrator=True)
    async def backup_list(self, ctx: commands.Context):
        """Show all backup files."""
        import os
        server_dir = f"data/{ctx.guild.id}/"
        if not os.path.exists(server_dir):
            await ctx.send("📭 No backups found for this server.")
            return

        backups = [f for f in os.listdir(server_dir) if f.startswith("backup_")]
        if not backups:
            await ctx.send("📭 No backups found.")
            return

        embed = make_embed(
            title="💾 Available Backups",
            description="\n".join(f"• `{b}`" for b in backups),
            color=config.theme_primary,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="invite_info", description="Show bot invite link")
    async def invite_info(self, ctx: commands.Context):
        """Generate bot invite link."""
        perms = discord.Permissions(
            administrator=True
        )
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=perms,
            scopes=["bot", "applications.commands"],
        )
        embed = make_embed(
            title="🦇 Invite 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞",
            description=(
                f"**[Click here to invite]({invite_url})**\n\n"
                "The bot requires Administrator permissions for full security features.\n"
                "Works on **any Discord server** — no setup required!"
            ),
            color=config.theme_primary,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Backup(bot))
