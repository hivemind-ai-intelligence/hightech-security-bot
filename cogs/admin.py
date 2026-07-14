"""
Cog: Admin — Bot diagnostics, ping, status, reload, and invite.
"""

import logging
import platform
import time
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config.settings import config

logger = logging.getLogger(__name__)
START_TIME = time.time()


class Admin(commands.Cog):
    """⚙️ Bot administration & diagnostics."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Check bot latency & uptime")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        uptime = time.time() - START_TIME
        h, rem = divmod(int(uptime), 3600)
        m, s = divmod(rem, 60)
        embed = discord.Embed(title="🏓 Pong!", color=config.theme_accent, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="Uptime", value=f"{h}h {m}m {s}s", inline=True)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="status", description="Show bot & server status")
    @commands.has_permissions(moderate_members=True)
    async def status(self, ctx: commands.Context):
        guild = ctx.guild
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        embed = discord.Embed(title="📊 Status", color=config.theme_primary, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.add_field(name="Members", value=f"{online} online / {guild.member_count}", inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Bot Version", value="2.0.0", inline=True)
        embed.add_field(name="Cogs", value=str(len(self.bot.cogs)), inline=True)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Global")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="reload", description="Hot-reload a cog (admin only)")
    @commands.has_permissions(administrator=True)
    async def reload_cog(self, ctx: commands.Context, cog_name: str):
        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await ctx.send(f"✅ Reloaded `{cog_name}`.", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❌ Failed: {e}", ephemeral=True)

    @commands.hybrid_command(name="cogs", description="List all loaded cogs")
    @commands.has_permissions(administrator=True)
    async def list_cogs(self, ctx: commands.Context):
        clist = "\n".join(f"• `{n}`" for n in sorted(self.bot.cogs.keys()))
        embed = discord.Embed(title="📦 Loaded Cogs", description=clist, color=config.theme_primary)
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="invite", description="Get bot invite link")
    async def invite(self, ctx: commands.Context):
        url = discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(administrator=True), scopes=["bot", "applications.commands"])
        embed = discord.Embed(title="🦇 Invite Link", description=f"[Click to Invite]({url})\n\nWorks on ANY server!", color=config.theme_primary)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="servers", description="Show server count (admin)")
    @commands.has_permissions(administrator=True)
    async def servers(self, ctx: commands.Context):
        ginfo = "\n".join(f"• {g.name} ({g.member_count} members)" for g in self.bot.guilds[:20])
        embed = discord.Embed(title=f"📡 {len(self.bot.guilds)} Servers", description=ginfo, color=config.theme_primary)
        if len(self.bot.guilds) > 20:
            embed.set_footer(text=f"...and {len(self.bot.guilds) - 20} more")
        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
