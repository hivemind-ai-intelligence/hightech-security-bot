"""
Cog: Verification — per-server email OTP identity verification.
Verified role set via /config_role verified.
"""

import asyncio
import logging
import secrets
import smtplib
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional

import discord
from discord.ext import commands

from config.settings import config

logger = logging.getLogger(__name__)


class Verification(commands.Cog):
    """🔐 Identity verification via email OTP — per server config."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending_codes: dict = {}

    def _get_verified_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        cfg = self.bot.get_cog("ServerConfig")
        if cfg:
            sc = cfg._get_config(guild.id)
            rid = sc.get("verified_role")
            if rid:
                return guild.get_role(rid)
        return None

    def _get_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        cfg = self.bot.get_cog("ServerConfig")
        if cfg:
            return cfg.get_channel(guild, "welcome_channel")
        return None

    # ── Events ──────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = self._get_welcome_channel(member.guild)
        if not ch:
            return
        embed = discord.Embed(
            title="🦇 Welcome to " + member.guild.name,
            description=(f"Welcome {member.mention}! Verify to gain access.\n"
                         f"Use `/verify email:you@company.com` then `/confirm code:XXXXXX`"),
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Verification")
        try:
            await ch.send(member.mention, embed=embed)
        except discord.Forbidden:
            pass

    # ── Commands ─────────────────────────────────────────

    @commands.hybrid_command(name="verify", description="Request a verification code via email")
    async def verify(self, ctx: commands.Context, email: str):
        uid = ctx.author.id
        if uid in self.pending_codes:
            elapsed = time.time() - self.pending_codes[uid].get("sent_at", 0)
            if elapsed < 60:
                await ctx.send(f"⏳ Wait {60 - int(elapsed)}s before requesting a new code.", ephemeral=True)
                return

        code = str(secrets.randbelow(10 ** config.verification_code_length)).zfill(config.verification_code_length)
        expires = time.time() + (config.verification_code_ttl_minutes * 60)
        self.pending_codes[uid] = {"code": code, "email": email, "attempts": 0, "expires": expires, "sent_at": time.time()}

        sent = await self._send_email(email, code, ctx.author)
        if sent:
            await ctx.send(f"📧 Code sent to `{email}`. Use `/confirm code:XXXXXX` within {config.verification_code_ttl_minutes} min.", ephemeral=True)
        else:
            await ctx.send("⚠️ Email failed. Contact admin. (Dev mode: code is in server logs)", ephemeral=True)

    @commands.hybrid_command(name="confirm", description="Confirm your verification code")
    async def confirm(self, ctx: commands.Context, code: str):
        uid = ctx.author.id
        if uid not in self.pending_codes:
            await ctx.send("❌ No pending verification. Use `/verify` first.", ephemeral=True)
            return
        pending = self.pending_codes[uid]
        if time.time() > pending["expires"]:
            del self.pending_codes[uid]
            await ctx.send("⏰ Code expired. Request a new one.", ephemeral=True)
            return
        if pending["attempts"] >= config.max_verification_attempts:
            del self.pending_codes[uid]
            await ctx.send("🚫 Too many attempts. Request a new code.", ephemeral=True)
            return
        if code != pending["code"]:
            pending["attempts"] += 1
            await ctx.send(f"❌ Invalid. {config.max_verification_attempts - pending['attempts']} attempts left.", ephemeral=True)
            return

        role = self._get_verified_role(ctx.guild)
        if not role:
            await ctx.send("⚠️ Verified role not configured. Admins: use `/config_role verified @role`.", ephemeral=True)
            return

        await ctx.author.add_roles(role, reason="Email verified")
        del self.pending_codes[uid]
        await ctx.send(f"✅ Welcome, {ctx.author.mention}! You are now verified.", ephemeral=True)

    @commands.hybrid_command(name="whois", description="Check a user's details")
    @commands.has_permissions(moderate_members=True)
    async def whois(self, ctx: commands.Context, member: discord.Member):
        roles = ", ".join(r.mention for r in member.roles[1:6]) or "None"
        embed = discord.Embed(
            title=f"🔍 {member}",
            color=config.theme_primary,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "R"), inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        embed.add_field(name="Roles", value=roles, inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="verify_manual", description="Manually verify a user (admin)")
    @commands.has_permissions(administrator=True)
    async def verify_manual(self, ctx: commands.Context, member: discord.Member):
        role = self._get_verified_role(ctx.guild)
        if role:
            await member.add_roles(role, reason=f"Manual verification by {ctx.author}")
        await ctx.send(f"✅ Manually verified {member.mention}")

    @commands.hybrid_command(name="verification_setup", description="Show verification setup guide")
    @commands.has_permissions(manage_guild=True)
    async def verification_setup(self, ctx: commands.Context):
        role = self._get_verified_role(ctx.guild)
        embed = discord.Embed(
            title="🔐 Verification Setup",
            description=(
                "**Current Config:**\n"
                f"• Verified Role: {role.mention if role else '❌ Not set'}\n"
                f"• SMTP Email: {'✅ ' + config.smtp_user if config.smtp_user else '❌ Not configured'}\n\n"
                "**Setup Steps:**\n"
                "1. Set verified role: `/config_role verified @role`\n"
                "2. Set welcome channel: `/config_channel welcome #channel`\n"
                "3. Set SMTP in `.env` file (bot owner only)\n\n"
                "Users will then use `/verify` to get an email OTP."
            ),
            color=config.theme_primary,
        )
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        await ctx.send(embed=embed)

    async def _send_email(self, email: str, code: str, user: discord.User) -> bool:
        if not config.smtp_host or not config.smtp_user:
            logger.info(f"[DEV] Verification code for {user} ({email}): {code}")
            return True

        try:
            msg = MIMEText(
                f"Hello {user.name},\n\n"
                f"Your Hi-Tech Security verification code is: **{code}**\n\n"
                f"Expires in {config.verification_code_ttl_minutes} minutes.\n\n"
                f"— Hi-Tech Security Team"
            )
            msg["Subject"] = f"Hi-Tech Security — Discord Verification: {code}"
            msg["From"] = config.smtp_user
            msg["To"] = email

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, msg.as_string(), [email])
            return True
        except Exception as e:
            logger.error(f"Email failed: {e}")
            logger.info(f"[DEV] Code for {email}: {code}")
            return False

    def _smtp_send(self, msg: str, recipients: list):
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as s:
            s.starttls()
            s.login(config.smtp_user, config.smtp_pass)
            s.sendmail(config.smtp_user, recipients, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
