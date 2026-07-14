"""
Cog: Threat Intelligence — IP/domain/hash lookups & threat feed.
Per-server threat intel channel configurable via /config_channel threat_intel.
"""

import asyncio
import base64
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands, tasks

from config.settings import config

logger = logging.getLogger(__name__)


class ThreatIntel(commands.Cog):
    """🔎 Threat intelligence lookups — AbuseIPDB, VirusTotal, AlienVault OTX."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.feed_task.start()

    def cog_unload(self):
        self.feed_task.cancel()

    def _get_intel_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        cfg = self.bot.get_cog("ServerConfig")
        if cfg:
            return cfg.get_channel(guild, "threat_intel_channel")
        return None

    @tasks.loop(hours=4)
    async def feed_task(self):
        await self.bot.wait_until_ready()
        pulses = await self._fetch_otx_pulses()
        if not pulses:
            return
        for guild in self.bot.guilds:
            ch = self._get_intel_channel(guild)
            if not ch:
                continue
            for pulse in pulses[:2]:
                embed = self._format_pulse(pulse)
                try:
                    await ch.send(embed=embed)
                except discord.Forbidden:
                    pass

    @feed_task.before_loop
    async def before_feed(self):
        await self.bot.wait_until_ready()

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="check_ip", description="Check IP reputation on AbuseIPDB")
    async def check_ip(self, ctx: commands.Context, ip: str):
        await ctx.defer()
        result = await self._check_abuseipdb(ip)
        if result is None:
            embed = discord.Embed(title=f"🔍 IP: `{ip}`", description="⚠️ AbuseIPDB API not configured.", color=config.theme_warning)
        elif "error" in result:
            embed = discord.Embed(title=f"🔍 IP: `{ip}`", description=f"❌ {result['error']}", color=config.theme_danger)
        else:
            score = result.get("abuseConfidenceScore", 0)
            color = config.theme_danger if score > 50 else config.theme_warning if score > 20 else config.theme_accent
            embed = discord.Embed(title=f"🔍 IP: `{ip}`", color=color, timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Abuse Score", value=f"{score}%", inline=True)
            embed.add_field(name="Reports", value=str(result.get("totalReports", "N/A")), inline=True)
            embed.add_field(name="Country", value=result.get("countryName", "N/A"), inline=True)
            embed.add_field(name="ISP", value=result.get("isp", "N/A"), inline=True)
            embed.set_footer(text="AbuseIPDB • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="check_hash", description="Check a file hash on VirusTotal")
    async def check_hash(self, ctx: commands.Context, file_hash: str):
        await ctx.defer()
        result = await self._check_vt_hash(file_hash)
        if result is None:
            embed = discord.Embed(title=f"🔍 Hash: `{file_hash[:16]}...`", description="⚠️ VirusTotal API not configured.", color=config.theme_warning)
        elif "error" in result:
            embed = discord.Embed(title=f"🔍 Hash: `{file_hash[:16]}...`", description=f"❌ {result['error']}", color=config.theme_danger)
        else:
            attrs = result.get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            total = sum(stats.values()) if stats else 0
            color = config.theme_danger if malicious > 0 else config.theme_accent
            embed = discord.Embed(title=f"🔍 VT: `{file_hash[:16]}...`", color=color, timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Detections", value=f"{malicious}/{total}", inline=True)
            embed.add_field(name="Type", value=attrs.get("type_description", "N/A"), inline=True)
            embed.set_footer(text="VirusTotal • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="check_url", description="Scan a URL on VirusTotal")
    async def check_url(self, ctx: commands.Context, url: str):
        await ctx.defer()
        result = await self._check_vt_url(url)
        if result is None:
            embed = discord.Embed(title=f"🔍 URL: `{url[:50]}...`", description="⚠️ VirusTotal API not configured.", color=config.theme_warning)
        elif "error" in result:
            embed = discord.Embed(title=f"🔍 URL: `{url[:50]}...`", description=f"❌ {result['error']}", color=config.theme_danger)
        else:
            attrs = result.get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            total = sum(stats.values()) if stats else 0
            color = config.theme_danger if malicious > 0 else config.theme_accent
            embed = discord.Embed(title=f"🔍 URL: `{url[:80]}`", color=color, timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Detections", value=f"{malicious}/{total}", inline=True)
            embed.set_footer(text="VirusTotal • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="threat_report", description="Threat intelligence summary")
    @commands.has_permissions(moderate_members=True)
    async def threat_report(self, ctx: commands.Context):
        await ctx.defer()
        pulses = await self._fetch_otx_pulses()
        embed = discord.Embed(title="📊 Threat Intelligence Report", description="Latest threat landscape", color=config.theme_primary, timestamp=datetime.now(timezone.utc))
        if pulses:
            for p in pulses[:5]:
                embed.add_field(name=p.get("name", "Unknown")[:100], value=f"Indicators: {len(p.get('indicators', []))}", inline=False)
        else:
            embed.description = "⚠️ No data. Configure AlienVault OTX API key."
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Threat Intel")
        await ctx.send(embed=embed)

    # ── API Methods ─────────────────────────────────────

    async def _check_abuseipdb(self, ip: str) -> dict | None:
        if not config.abuseipdb_api_key:
            return None
        try:
            req = urllib.request.Request(f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90", headers={"Key": config.abuseipdb_api_key, "Accept": "application/json"})
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10).read())
            return json.loads(data).get("data", {})
        except Exception as e:
            logger.error(f"AbuseIPDB: {e}")
            return {"error": str(e)}

    async def _check_vt_hash(self, fhash: str) -> dict | None:
        if not config.virustotal_api_key:
            return None
        try:
            req = urllib.request.Request(f"https://www.virustotal.com/api/v3/files/{fhash}", headers={"x-apikey": config.virustotal_api_key})
            loop = asyncio.get_event_loop()
            return json.loads(await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10).read()))
        except Exception as e:
            return {"error": str(e)}

    async def _check_vt_url(self, url: str) -> dict | None:
        if not config.virustotal_api_key:
            return None
        try:
            url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
            req = urllib.request.Request(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers={"x-apikey": config.virustotal_api_key})
            loop = asyncio.get_event_loop()
            return json.loads(await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10).read()))
        except Exception as e:
            return {"error": str(e)}

    async def _fetch_otx_pulses(self) -> list:
        if not config.alienvault_otx_api_key:
            return []
        try:
            req = urllib.request.Request("https://otx.alienvault.com/api/v1/pulses/subscribed?limit=3", headers={"X-OTX-API-KEY": config.alienvault_otx_api_key})
            loop = asyncio.get_event_loop()
            return json.loads(await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10).read())).get("results", [])
        except Exception:
            return []

    def _format_pulse(self, pulse: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"🛡️ {pulse.get('name', 'Threat Pulse')[:100]}",
            description=pulse.get("description", "")[:250] or "No description",
            color=config.theme_danger,
            url=f"https://otx.alienvault.com/pulse/{pulse.get('id', '')}",
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="TLP", value=pulse.get("TLP", "unknown").upper(), inline=True)
        embed.add_field(name="Indicators", value=str(len(pulse.get("indicators", []))), inline=True)
        tags = ", ".join(pulse.get("tags", [])[:5]) or "None"
        embed.add_field(name="Tags", value=tags, inline=True)
        embed.set_footer(text="OTX • 🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(ThreatIntel(bot))
