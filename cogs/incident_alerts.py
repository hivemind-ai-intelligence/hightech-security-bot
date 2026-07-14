"""
Cog: Incidents — per-server incident tracking & alert management.
Channels configured via /config_channel incident and /config_channel alert.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

from config.settings import config
from utils.helpers import make_embed

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "critical": 0xFF0000,
    "high": 0xB22222,
    "medium": 0x8B0000,
    "low": 0x4A0000,
    "info": 0x2D0000,
}


class IncidentAlerts(commands.Cog):
    """🚨 Security incident monitoring & alerting — per server."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.incidents: dict = {}  # guild_id -> {incident_id: data}

    # ── Helpers ──────────────────────────────────────────

    def _get_incidents(self, guild_id: int) -> dict:
        if guild_id not in self.incidents:
            self.incidents[guild_id] = {}
        return self.incidents[guild_id]

    def _get_channel(self, guild: discord.Guild, key: str) -> Optional[discord.TextChannel]:
        cfg = self.bot.get_cog("ServerConfig")
        if cfg:
            ch = cfg.get_channel(guild, key)
            if ch:
                return ch
        fid = getattr(config, f"{key}_id", 0) if key.endswith("_channel") else getattr(config, f"{key}_channel_id", 0)
        return guild.get_channel(fid) if fid else None

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="alert", description="Create a security alert/incident")
    @commands.has_permissions(moderate_members=True)
    async def create_alert(self, ctx: commands.Context, severity: str = "medium", *, description: str):
        severity = severity.lower()
        if severity not in SEVERITY_COLORS:
            severity = "medium"

        guild_incidents = self._get_incidents(ctx.guild.id)
        incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        incident = {
            "id": incident_id,
            "severity": severity,
            "description": description,
            "reported_by": str(ctx.author),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "assigned_to": None,
            "updates": [],
        }

        guild_incidents[incident_id] = incident

        embed = self._format_incident_embed(incident)
        incident_channel = self._get_channel(ctx.guild, "incident_channel")
        if incident_channel:
            msg = await incident_channel.send("@here — New Security Alert!", embed=embed)
            if severity == "critical":
                await msg.pin()

        alert_channel = self._get_channel(ctx.guild, "alert_channel")
        if alert_channel and alert_channel != incident_channel:
            await alert_channel.send(embed=embed)

        await ctx.send(f"🚨 Incident **{incident_id}** created!", ephemeral=True)

    @commands.hybrid_command(name="incidents", description="List all active security incidents")
    @commands.has_permissions(moderate_members=True)
    async def list_incidents(self, ctx: commands.Context):
        guild_incidents = self._get_incidents(ctx.guild.id)
        if not guild_incidents:
            await ctx.send("✅ No active security incidents.", ephemeral=True)
            return

        embed = make_embed(
            title="🚨 Active Security Incidents",
            color=config.theme_danger,
        )
        for inc in sorted(guild_incidents.values(), key=lambda x: list(SEVERITY_COLORS).index(x["severity"])):
            status_icon = {"open": "🔴", "investigating": "🟡", "resolved": "🟢"}.get(inc.get("status", "open"), "🔴")
            embed.add_field(
                name=f"{status_icon} {inc['id']} [{inc['severity'].upper()}]",
                value=inc["description"][:200],
                inline=False,
            )
        embed.set_footer(text=f"Total: {len(guild_incidents)} • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="incident", description="View incident details")
    @commands.has_permissions(moderate_members=True)
    async def view_incident(self, ctx: commands.Context, incident_id: str):
        guild_incidents = self._get_incidents(ctx.guild.id)
        incident = guild_incidents.get(incident_id.upper())
        if not incident:
            await ctx.send(f"❌ Incident `{incident_id}` not found.", ephemeral=True)
            return
        embed = self._format_incident_embed(incident, full=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="resolve", description="Resolve/close an incident")
    @commands.has_permissions(moderate_members=True)
    async def resolve_incident(self, ctx: commands.Context, incident_id: str, *, resolution: str = "Resolved"):
        guild_incidents = self._get_incidents(ctx.guild.id)
        incident = guild_incidents.get(incident_id.upper())
        if not incident:
            await ctx.send(f"❌ Incident `{incident_id}` not found.", ephemeral=True)
            return
        incident["status"] = "resolved"
        incident["resolution"] = resolution
        incident["resolved_by"] = str(ctx.author)
        incident["resolved_at"] = datetime.now(timezone.utc).isoformat()
        incident["updates"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "resolved",
            "by": str(ctx.author),
            "detail": resolution,
        })
        await ctx.send(f"✅ Incident **{incident_id}** resolved.")

    @commands.hybrid_command(name="assign", description="Assign incident to a team member")
    @commands.has_permissions(moderate_members=True)
    async def assign_incident(self, ctx: commands.Context, incident_id: str, member: discord.Member):
        guild_incidents = self._get_incidents(ctx.guild.id)
        incident = guild_incidents.get(incident_id.upper())
        if not incident:
            await ctx.send(f"❌ Not found.", ephemeral=True)
            return
        incident["assigned_to"] = str(member)
        incident["updates"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "assigned",
            "by": str(ctx.author),
            "detail": f"Assigned to {member}",
        })
        await ctx.send(f"👤 Incident **{incident_id}** assigned to {member.mention}")
        try:
            await member.send(embed=make_embed(
                title=f"🛡️ Assigned: {incident_id}",
                description=f"**{incident['description'][:200]}**\nSeverity: **{incident['severity'].upper()}**",
                color=SEVERITY_COLORS.get(incident["severity"], 0xFFA500),
            ))
        except discord.Forbidden:
            pass

    @commands.hybrid_command(name="update_incident", description="Add update to an incident")
    @commands.has_permissions(moderate_members=True)
    async def update_incident(self, ctx: commands.Context, incident_id: str, *, update: str):
        guild_incidents = self._get_incidents(ctx.guild.id)
        incident = guild_incidents.get(incident_id.upper())
        if not incident:
            await ctx.send(f"❌ Not found.", ephemeral=True)
            return
        incident["updates"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "update",
            "by": str(ctx.author),
            "detail": update,
        })
        await ctx.send(f"📝 Updated incident **{incident_id}**.")

    @commands.hybrid_command(name="incident_search", description="Search incidents by keyword")
    @commands.has_permissions(moderate_members=True)
    async def incident_search(self, ctx: commands.Context, *, keyword: str):
        guild_incidents = self._get_incidents(ctx.guild.id)
        matches = [
            inc for inc in guild_incidents.values()
            if keyword.lower() in inc["description"].lower()
            or keyword.lower() in inc["id"].lower()
        ]
        if not matches:
            await ctx.send(f"🔍 No incidents matching `{keyword}`.")
            return

        embed = make_embed(
            title=f"🔍 Search: `{keyword}` — {len(matches)} results",
            color=config.theme_primary,
        )
        for inc in matches[:10]:
            embed.add_field(
                name=f"{inc['id']} [{inc['severity'].upper()}]",
                value=inc["description"][:150],
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="incident_stats", description="Incident statistics summary")
    @commands.has_permissions(moderate_members=True)
    async def incident_stats(self, ctx: commands.Context):
        guild_incidents = self._get_incidents(ctx.guild.id)
        total = len(guild_incidents)
        open_count = sum(1 for i in guild_incidents.values() if i["status"] == "open")
        resolved = sum(1 for i in guild_incidents.values() if i["status"] == "resolved")
        critical = sum(1 for i in guild_incidents.values() if i["severity"] == "critical")

        embed = make_embed(
            title="📊 Incident Statistics",
            color=config.theme_primary,
        )
        embed.add_field(name="Total", value=str(total), inline=True)
        embed.add_field(name="🔴 Open", value=str(open_count), inline=True)
        embed.add_field(name="🟢 Resolved", value=str(resolved), inline=True)
        embed.add_field(name="Critical", value=str(critical), inline=True)
        await ctx.send(embed=embed)

    def _format_incident_embed(self, incident: dict, full: bool = False) -> discord.Embed:
        severity = incident.get("severity", "medium")
        color = SEVERITY_COLORS.get(severity, 0xFFA500)
        icons = {"open": "🔴", "investigating": "🟡", "resolved": "🟢"}
        icon = icons.get(incident.get("status", "open"), "🔴")

        embed = discord.Embed(
            title=f"{icon} {incident['id']}: {incident['description'][:100]}",
            description=incident["description"] if full else incident["description"][:250],
            color=color,
            timestamp=datetime.fromisoformat(incident["created_at"]),
        )
        embed.add_field(name="Severity", value=severity.upper(), inline=True)
        embed.add_field(name="Status", value=incident.get("status", "open").title(), inline=True)
        embed.add_field(name="Reported By", value=incident.get("reported_by", "Unknown"), inline=True)
        if incident.get("assigned_to"):
            embed.add_field(name="Assigned To", value=incident["assigned_to"], inline=True)
        if full and incident.get("updates"):
            updates_text = "\n".join(
                f"• {u['timestamp'][:16]} — {u['detail'][:100]}" for u in incident["updates"][-5:]
            )
            embed.add_field(name="Updates", value=updates_text or "None", inline=False)
        if incident.get("resolution"):
            embed.add_field(name="Resolution", value=incident["resolution"], inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Incident Management")
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(IncidentAlerts(bot))
