"""
Cog: Help — Complete command reference for all 42+ slash commands.
"""

import discord
from discord.ext import commands
from config.settings import config


class Help(commands.Cog):
    """📚 Complete command reference."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="bot_help", description="Show complete command reference (42+ commands)")
    async def help_cmd(self, ctx: commands.Context, category: str = None, command_name: str = None):
        if command_name:
            cmd = self.bot.get_command(command_name.lower())
            if cmd:
                await self._cmd_help(ctx, cmd)
            else:
                await ctx.send(f"❌ `{command_name}` not found.", ephemeral=True)
            return

        cats = {
            "moderation": "🛡️ Moderation",
            "automod": "🤖 AutoMod",
            "verification": "🔐 Verification",
            "threat_intel": "🔎 Threat Intel",
            "incident_alerts": "🚨 Incidents",
            "anti_raid": "🛡️ Anti-Raid",
            "reports": "📊 Reports",
            "backup": "💾 Backup",
            "server_config": "⚙️ Server Config",
            "admin": "⚙️ Admin",
            "music": "🎵 Music",
        }

        if category and category.lower() in cats:
            await self._cat_help(ctx, category.lower())
            return

        prefix = config.bot_prefix
        embed = discord.Embed(
            title="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — Commands",
            description=f"Prefix: `{prefix}` | Slash commands also available\n`/help <category>` for details",
            color=config.theme_primary,
        )

        embed.add_field(name="🛡️ Moderation (10)", value="`warn` `mute` `unmute` `kick` `ban` `unban` `softban` `purge` `nuke` = 9 + moderation events", inline=False)
        embed.add_field(name="🤖 AutoMod (10)", value="`automod_status` `automod_toggle` `automod_links` `automod_invites` `automod_mentions` `blacklist_add` `blacklist_remove` `blacklist_list` `whitelist_channel` `set_max_mentions`", inline=False)
        embed.add_field(name="🔐 Verification (5)", value="`verify` `confirm` `whois` `verify_manual` `verification_setup`", inline=False)
        embed.add_field(name="🔎 Threat Intel (4)", value="`check_ip` `check_hash` `check_url` `threat_report`", inline=False)
        embed.add_field(name="🚨 Incidents (9)", value="`alert` `incidents` `incident` `assign` `resolve` `update_incident` `incident_search` `incident_stats`", inline=False)
        embed.add_field(name="🛡️ Anti-Raid (5)", value="`lockdown` `raid_status` `lock_channel` `unlock_channel` `slowmode`", inline=False)
        embed.add_field(name="📊 Reports (7)", value="`server_info` `user_info` `channel_stats` `role_list` `activity_report` `audit_report`", inline=False)
        embed.add_field(name="💾 Backup (4)", value="`backup_roles` `backup_channels` `backup_full` `backup_list`", inline=False)
        embed.add_field(name="⚙️ Config (6)", value="`setup` `config_view` `config_channel` `config_role` `config_reset` `invite_info`", inline=False)
        embed.add_field(name="⚙️ Admin (5)", value="`ping` `status` `reload` `cogs` `invite` `servers` `help`", inline=False)
        embed.add_field(name="🎵 Music (29)", value="`play` `search` `skip` `forceskip` `pause` `resume` `stop` `queue` `loop` `shuffle` `volume` `bassboost` `nightcore` `autoplay` `seek` `restart` `remove` `clearqueue` `move` `history` `replay` `playnext` `play_now` `nowplaying` `lyrics` `music_help` `247` `dj` `disconnect`", inline=False)

        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • 42+ Global Commands • Use /bot_help • Works on ANY server!")
        await ctx.send(embed=embed)

    async def _cat_help(self, ctx: commands.Context, category: str):
        cog_map = {
            "moderation": "Moderation", "automod": "AutoMod",
            "verification": "Verification", "threat_intel": "ThreatIntel",
            "incident_alerts": "IncidentAlerts", "anti_raid": "AntiRaid",
            "reports": "Reports", "backup": "Backup",
            "server_config": "ServerConfig", "admin": "Admin", "music": "Music",
        }
        cog = self.bot.get_cog(cog_map.get(category, ""))
        if not cog:
            await ctx.send("Not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📚 {category.replace('_', ' ').title()} Commands",
            color=config.theme_primary,
        )
        for cmd in cog.get_commands():
            if not cmd.hidden:
                embed.add_field(name=f"`/{cmd.qualified_name}`", value=cmd.description or "—", inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    async def _cmd_help(self, ctx: commands.Context, cmd: commands.Command):
        embed = discord.Embed(
            title=f"Command: `/{cmd.qualified_name}`",
            description=cmd.description or "No description",
            color=config.theme_primary,
        )
        params = []
        for name, param in cmd.clean_params.items():
            p = f"[{name}]" if param.default is not param.empty else f"<{name}>"
            params.append(p)
        embed.add_field(name="Usage", value=f"`/{cmd.qualified_name} {' '.join(params)}`", inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
