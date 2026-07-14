"""
🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 — Advanced Music System
Powered by yt-dlp + FFmpeg | No API keys needed
YouTube, Search, Queue, Loop, Shuffle, Filters
25+ commands with full vampire-themed embeds + buttons
"""

import asyncio, json, logging, random, re, time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List

import discord
from discord.ext import commands, tasks

from config.settings import config

logger = logging.getLogger(__name__)

MUSIC_COLORS = {
    "playing": 0x8B0000, "paused": 0xFF4500, "queued": 0x4A0000,
    "stopped": 0x1A0000, "error": 0xFF0000, "lyrics": 0xB22222, "info": 0x8B0000,
}

ME = {
    "play": "▶️", "pause": "⏸️", "stop": "⏹️", "skip": "⏭️", "prev": "⏮️",
    "shuffle": "🔀", "repeat": "🔁", "repeat_one": "🔂", "queue": "📋",
    "vol_up": "🔊", "vol_down": "🔉", "mute": "🔇", "search": "🔎",
    "music": "🎵", "note": "🎶", "dj": "🎧", "bat": "🦇", "fire": "🔥",
    "crown": "👑", "sparkles": "✨", "skull": "💀",
}


@dataclass
class Track:
    title: str; url: str; duration: int; thumbnail: str; uploader: str
    requester_id: int; requester_name: str; is_live: bool = False
    source_type: str = "youtube"


@dataclass
class GuildMusicState:
    voice_client: Optional[discord.VoiceClient] = None
    queue: deque = field(default_factory=deque)
    history: deque = field(default_factory=deque)
    current_track: Optional[Track] = None
    loop_mode: str = "off"  # off | queue | track
    shuffle: bool = False; volume: float = 1.0; paused: bool = False
    start_time: float = 0; pause_time: float = 0; total_pause_time: float = 0
    now_playing_msg: Optional[discord.Message] = None
    text_channel: Optional[discord.TextChannel] = None
    dj_role_id: int = 0; is_24_7: bool = False; bass_boost: bool = False
    nightcore: bool = False; auto_play: bool = False
    skip_votes: dict = field(default_factory=dict); last_activity: float = 0
    disconnect_task: Optional[asyncio.Task] = None


class Music(commands.Cog):
    """🦇 Advanced Music System — 25+ commands, no API keys needed."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_states: Dict[int, GuildMusicState] = {}
        self.ydl_opts = {
            "format": "bestaudio/best", "quiet": True, "no_warnings": True,
            "extract_flat": False, "noplaylist": False, "playlist_items": "1-200",
            "ignoreerrors": True, "no_color": True, "source_address": "0.0.0.0",
            "geo_bypass": True, "socket_timeout": 15, "retries": 5,
        }
        self.ytdl = None
        self._init_ydl()

    def _init_ydl(self):
        try:
            import yt_dlp
            self.ytdl = yt_dlp.YoutubeDL(self.ydl_opts)
            logger.info("🎵 yt-dlp initialized")
        except ImportError:
            logger.error("yt-dlp not installed!")

    def _get_state(self, gid: int) -> GuildMusicState:
        if gid not in self.guild_states: self.guild_states[gid] = GuildMusicState()
        return self.guild_states[gid]

    async def _check_dj(self, ctx: commands.Context) -> bool:
        if ctx.author.guild_permissions.administrator: return True
        if ctx.author.guild_permissions.manage_guild: return True
        state = self._get_state(ctx.guild.id)
        if state.dj_role_id:
            role = ctx.guild.get_role(state.dj_role_id)
            if role and role in ctx.author.roles: return True
        dj_role = discord.utils.get(ctx.guild.roles, name="Hi-Tech DJ")
        if dj_role and dj_role in ctx.author.roles: return True
        if ctx.author.voice and ctx.author.voice.channel:
            members = [m for m in ctx.author.voice.channel.members if not m.bot]
            if len(members) <= 1: return True
        return False

    async def _ensure_voice(self, ctx: commands.Context):
        if not ctx.author.voice:
            embed = discord.Embed(title="🦇 No Voice Channel",
                description="Join a voice channel first, mortal.", color=MUSIC_COLORS["error"])
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Music")
            await ctx.send(embed=embed, ephemeral=True); return None
        ch = ctx.author.voice.channel; state = self._get_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_connected():
            if state.voice_client.channel.id != ch.id: await state.voice_client.move_to(ch)
            return state.voice_client
        perms = ch.permissions_for(ctx.guild.me)
        if not perms.connect or not perms.speak:
            await ctx.send("🦇 Need Connect + Speak permissions.", ephemeral=True); return None
        try:
            vc = await ch.connect(timeout=20, reconnect=True)
            state.voice_client = vc; state.text_channel = ctx.channel
            state.last_activity = time.time(); return vc
        except Exception as e:
            await ctx.send(f"🦇 Voice error: {e}", ephemeral=True); return None

    async def _extract_track(self, query: str, ctx: commands.Context):
        if not self.ytdl: return None
        loop = asyncio.get_event_loop()
        is_url = query.startswith("http://") or query.startswith("https://")
        try:
            if is_url: info = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(query, download=False))
            else: info = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(f"ytsearch10:{query}", download=False))
        except:
            try:
                if not is_url: info = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(f"ytsearch5:{query.strip()}", download=False))
                else: return None
            except: return None
        if not info: return None
        tracks = []
        if "entries" in info:
            for entry in info["entries"]:
                if entry:
                    t = self._parse_entry(entry, ctx)
                    if t: tracks.append(t)
        else:
            t = self._parse_entry(info, ctx)
            if t: tracks.append(t)
        return tracks if tracks else None

    def _parse_entry(self, entry: dict, ctx: commands.Context):
        try:
            return Track(
                title=(entry.get("title") or "Unknown")[:200],
                url=entry.get("webpage_url") or entry.get("url") or "",
                duration=int(entry.get("duration") or 0),
                thumbnail=entry.get("thumbnail") or "",
                uploader=(entry.get("uploader") or entry.get("channel") or "Unknown")[:100],
                requester_id=ctx.author.id, requester_name=ctx.author.display_name,
                is_live=entry.get("is_live", False),
            )
        except: return None

    async def _create_source(self, track: Track, state: GuildMusicState):
        if not self.ytdl: return None
        loop = asyncio.get_event_loop()
        try: info = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(track.url, download=False))
        except: return None
        stream_url = info.get("url")
        if not stream_url:
            for fmt in info.get("formats", []):
                if fmt.get("acodec") != "none" and fmt.get("url"):
                    stream_url = fmt["url"]; break
        if not stream_url: return None
        ffmpeg_opts = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
        vol = state.volume
        if state.bass_boost: ffmpeg_opts["options"] += f' -af "volume={vol},bass=g=10:f=110"'
        elif state.nightcore: ffmpeg_opts["options"] += f' -af "volume={vol},asetrate=44100*1.25,atempo=1.25"'
        else: ffmpeg_opts["options"] += f' -af "volume={vol}"'
        try: return discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
        except: return None

    async def _play_next(self, guild: discord.Guild):
        state = self._get_state(guild.id)
        if not state.voice_client or not state.voice_client.is_connected(): return
        if state.current_track:
            state.history.append(state.current_track)
            while len(state.history) > 20: state.history.popleft()
        next_track = None
        if state.loop_mode == "track" and state.current_track: next_track = state.current_track
        elif state.queue:
            if state.shuffle:
                idx = random.randint(0, len(state.queue)-1)
                next_track = state.queue[idx]; del state.queue[idx]
            elif state.loop_mode == "queue" and state.current_track:
                state.queue.append(state.current_track)
                next_track = state.queue.popleft()
            else: next_track = state.queue.popleft()
        elif state.loop_mode == "queue" and state.current_track: next_track = state.current_track
        elif state.auto_play and state.current_track:
            try:
                related = await self._extract_track(state.current_track.title, None)
                if related and len(related) > 1:
                    next_track = related[1]
                    next_track.requester_id = state.current_track.requester_id
                    next_track.requester_name = state.current_track.requester_name
            except: pass

        if not next_track:
            state.current_track = None; state.now_playing_msg = None
            await self._send_idle(state, guild)
            if not state.is_24_7:
                if state.disconnect_task: state.disconnect_task.cancel()
                state.disconnect_task = asyncio.create_task(self._auto_dc(guild))
            return

        state.current_track = next_track; state.start_time = time.time()
        state.total_pause_time = 0; state.paused = False; state.skip_votes.clear()
        source = await self._create_source(next_track, state)
        if not source:
            await self._send_error(state, guild, "Failed to load audio")
            await self._play_next(guild); return
        state.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self._after_next(guild.id, e), self.bot.loop))
        await self._send_np(state, guild); state.last_activity = time.time()

    def _after_next(self, gid, error):
        if error: logger.error(f"Playback err g{gid}: {error}")
        guild = self.bot.get_guild(gid)
        if guild: asyncio.ensure_future(self._play_next(guild), loop=self.bot.loop)

    async def _auto_dc(self, guild):
        await asyncio.sleep(180)
        state = self._get_state(guild.id)
        if not state.current_track and not state.is_24_7 and state.voice_client:
            await state.voice_client.disconnect(); state.voice_client = None

    # ── Embeds ─────────────────────────────────────

    async def _send_np(self, state, guild):
        if not state.current_track: return; t = state.current_track
        dur = t.duration
        if dur > 0:
            elapsed = int(time.time() - state.start_time - state.total_pause_time)
            pct = min(elapsed / max(dur, 1), 1.0)
            bar = f"{'🩸' * int(18*pct)}{'▬' * (18 - int(18*pct))}"
            e_str = str(timedelta(seconds=min(elapsed, dur)))
            t_str = str(timedelta(seconds=dur))
            if e_str.startswith("0:"): e_str = e_str[2:]
            if t_str.startswith("0:"): t_str = t_str[2:]
            prog = f"`{e_str}` {bar} `{t_str}`"
        else: prog = "🔴 **LIVE**"

        embed = discord.Embed(
            title=f"{ME['bat']} Now Playing",
            description=f"### [{t.title}]({t.url})\n{prog}",
            color=MUSIC_COLORS["playing"], timestamp=datetime.now(timezone.utc))
        if t.thumbnail: embed.set_thumbnail(url=t.thumbnail)
        embed.add_field(name=f"{ME['dj']} Requested", value=t.requester_name, inline=True)
        embed.add_field(name=f"{ME['music']} Uploader", value=t.uploader, inline=True)
        embed.add_field(name=f"{ME['note']} Duration",
            value="🔴 LIVE" if t.is_live else str(timedelta(seconds=dur)) if dur else "???", inline=True)
        embed.add_field(name=f"{ME['queue']} Queue", value=f"{len(state.queue)} tracks", inline=True)
        embed.add_field(name=f"{ME['vol_up']} Volume", value=f"{int(state.volume*100)}%", inline=True)
        modes = []
        if state.loop_mode=="track": modes.append(f"{ME['repeat_one']} Loop Track")
        elif state.loop_mode=="queue": modes.append(f"{ME['repeat']} Loop Queue")
        if state.shuffle: modes.append(f"{ME['shuffle']} Shuffle")
        if state.bass_boost: modes.append("🩸 Bass Boost")
        if state.nightcore: modes.append("⚡ Nightcore")
        if state.auto_play: modes.append("🤖 Auto-Play")
        if modes: embed.add_field(name=f"{ME['sparkles']} Modes", value=" | ".join(modes), inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Music Controls")

        if state.now_playing_msg:
            try: await state.now_playing_msg.delete()
            except: pass
        ch = state.text_channel or guild.system_channel
        if ch:
            try:
                view = MusicControlView(self, guild.id)
                state.now_playing_msg = await ch.send(embed=embed, view=view)
            except: pass

    async def _send_idle(self, state, guild):
        embed = discord.Embed(title=f"{ME['bat']} Queue Empty",
            description=f"Play something with `/play song name`\n\n**Quick:**\n{ME['play']} `/play song` — Search & play\n{ME['search']} `/search song` — Pick from results\n{ME['queue']} `/queue` — View queue\n{ME['repeat']} `/loop track` — Loop",
            color=MUSIC_COLORS["stopped"])
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Music")
        if state.now_playing_msg:
            try: await state.now_playing_msg.delete()
            except: pass
        ch = state.text_channel or guild.system_channel
        if ch:
            try:
                state.now_playing_msg = await ch.send(embed=embed, view=MusicIdleView(self, guild.id))
            except: pass

    async def _send_error(self, state, guild, msg):
        embed = discord.Embed(title="🦇 Error", description=f"```{msg}```", color=MUSIC_COLORS["error"])
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")
        ch = state.text_channel or guild.system_channel
        if ch:
            try: await ch.send(embed=embed, delete_after=10)
            except: pass

    # ── ALL SLASH COMMANDS ────────────────────────────

    @commands.hybrid_command(name="play", description="Play a song from YouTube (search or URL)")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play(self, ctx, *, query: str):
        await ctx.defer()
        vc = await self._ensure_voice(ctx)
        if not vc: return
        state = self._get_state(ctx.guild.id); state.text_channel = ctx.channel
        tracks = await self._extract_track(query, ctx)
        if not tracks:
            await ctx.send(embed=discord.Embed(title="🦇 No Results", description=f"Nothing found for `{query[:100]}`", color=MUSIC_COLORS["error"]).set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")); return
        if len(tracks) > 1:
            for t in tracks: state.queue.append(t)
            await ctx.send(embed=discord.Embed(title=f"{ME['queue']} Playlist Added", description=f"**{len(tracks)}** tracks added! 🩸", color=MUSIC_COLORS["queued"]).set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞"))
            if not state.current_track and not vc.is_playing(): await self._play_next(ctx.guild)
        else:
            t = tracks[0]; state.queue.append(t)
            embed = discord.Embed(title=f"{ME['queued']} Added", description=f"**[{t.title}]({t.url})**\n{ME['dj']} {t.requester_name}", color=MUSIC_COLORS["queued"])
            if t.thumbnail: embed.set_thumbnail(url=t.thumbnail)
            embed.add_field(name="Duration", value="🔴 LIVE" if t.is_live else str(timedelta(seconds=t.duration)))
            embed.add_field(name="Queue #", value=str(len(state.queue)))
            embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Music")
            await ctx.send(embed=embed)
            if not state.current_track and not vc.is_playing(): await self._play_next(ctx.guild)

    @commands.hybrid_command(name="play_now", description="Skip queue and play immediately (DJ)")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play_now(self, ctx, *, query: str):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ perms needed.", ephemeral=True); return
        await ctx.defer(); vc = await self._ensure_voice(ctx)
        if not vc: return
        state = self._get_state(ctx.guild.id)
        tracks = await self._extract_track(query, ctx)
        if not tracks: await ctx.send("🦇 Nothing found.", ephemeral=True); return
        t = tracks[0]; state.queue.appendleft(t)
        if state.voice_client and state.voice_client.is_playing(): state.voice_client.stop()
        await self._play_next(ctx.guild)
        await ctx.send(f"⚡ Now playing: **{t.title}**", ephemeral=True)

    @commands.hybrid_command(name="search", description="Search YouTube and pick a result")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def search(self, ctx, *, query: str):
        await ctx.defer(); await self._ensure_voice(ctx)
        tracks = await self._extract_track(query, ctx)
        if not tracks: await ctx.send("🦇 No results.", ephemeral=True); return
        results = tracks[:10]
        desc = "\n".join(f"**{i}.** [{t.title[:80]}]({t.url}) — `{str(timedelta(seconds=t.duration))}` | {t.uploader}" for i, t in enumerate(results, 1))
        embed = discord.Embed(title=f"🔎 Search: `{query[:80]}`", description=desc, color=MUSIC_COLORS["info"])
        embed.set_footer(text="🦇 Pick a number 1-10 | 30s timeout")
        view = SearchSelectView(self, ctx, results)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="skip", description="Skip the current track (vote or DJ)")
    async def skip(self, ctx):
        state = self._get_state(ctx.guild.id)
        if not state.current_track: await ctx.send("🦇 Nothing playing.", ephemeral=True); return
        if await self._check_dj(ctx):
            if state.voice_client: state.voice_client.stop()
            await ctx.send(f"{ME['skip']} Skipped by DJ {ctx.author.mention}")
            return
        vc_ch = state.voice_client.channel if state.voice_client else None
        if not vc_ch: await ctx.send("🦇 Join VC to vote."); return
        state.skip_votes[ctx.author.id] = True
        listeners = [m for m in vc_ch.members if not m.bot]
        needed = max(len(listeners)//2, 1); current = len(state.skip_votes)
        if current >= needed:
            state.voice_client.stop(); state.skip_votes.clear()
            await ctx.send(f"{ME['skip']} Vote passed! ({current}/{needed})")
        else: await ctx.send(f"🗳️ Skip: **{current}/{needed}** | `/skip` to vote")

    @commands.hybrid_command(name="forceskip", description="Force skip (DJ only)")
    async def forceskip(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if state.voice_client: state.voice_client.stop()
        await ctx.send(f"💀 Force skipped by {ctx.author.mention}")

    @commands.hybrid_command(name="stop", description="Stop playback and clear queue")
    async def stop(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        state.queue.clear(); state.loop_mode="off"; state.shuffle=False; state.auto_play=False
        if state.voice_client: state.voice_client.stop()
        await ctx.send(f"{ME['stop']} Stopped & cleared.")

    @commands.hybrid_command(name="disconnect", description="Disconnect bot from voice")
    async def disconnect(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if state.voice_client: await state.voice_client.disconnect(); state.voice_client=None
        state.current_track=None; state.queue.clear()
        await ctx.send(f"{ME['bat']} Disconnected. The moon descends...")

    @commands.hybrid_command(name="nowplaying", description="Show currently playing track")
    async def nowplaying(self, ctx):
        state = self._get_state(ctx.guild.id)
        if not state.current_track: await ctx.send("🦇 Nothing playing.", ephemeral=True); return
        await self._send_np(state, ctx.guild)

    @commands.hybrid_command(name="pause", description="Pause the music")
    async def pause(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.pause(); state.paused=True; state.pause_time=time.time()
            await ctx.send(f"{ME['pause']} Paused.")

    @commands.hybrid_command(name="resume", description="Resume playback")
    async def resume(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if state.voice_client and state.voice_client.is_paused():
            state.voice_client.resume(); state.paused=False
            state.total_pause_time += time.time() - state.pause_time
            await ctx.send(f"{ME['resume']} Resumed.")

    @commands.hybrid_command(name="queue", description="View music queue")
    async def queue(self, ctx, page: int = 1):
        state = self._get_state(ctx.guild.id)
        if not state.current_track and not state.queue:
            await ctx.send(embed=discord.Embed(title="📋 Empty Queue", description="Use `/play`!", color=MUSIC_COLORS["stopped"]).set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞")); return

        embed = discord.Embed(title=f"📋 Music Queue", color=MUSIC_COLORS["info"], timestamp=datetime.now(timezone.utc))

        # Current track
        t = state.current_track
        if t:
            elapsed = int(time.time() - state.start_time - state.total_pause_time) if not state.paused else int(state.pause_time - state.start_time - state.total_pause_time)
            embed.add_field(name=f"🎧 Now Playing {'⏸️' if state.paused else ''}",
                value=f"**[{t.title[:80]}]({t.url})**\n`{str(timedelta(seconds=elapsed))} / {str(timedelta(seconds=t.duration))}` | {t.requester_name}", inline=False)

        # Queue items
        qlist = list(state.queue)
        per_page = 10; total_pages = max((len(qlist)+per_page-1)//per_page, 1)
        page = max(1, min(page, total_pages))
        start = (page-1)*per_page; end = start+per_page
        for i, t in enumerate(qlist[start:end], start+1):
            embed.add_field(name=f"#{i} {t.title[:80]}",
                value=f"`{str(timedelta(seconds=t.duration))}` | {ME['dj']} {t.requester_name}", inline=False)

        total_dur = sum(t.duration for t in qlist)
        embed.add_field(name=f"{ME['note']} Summary",
            value=f"{len(qlist)} tracks | `{str(timedelta(seconds=total_dur))}` total | Page {page}/{total_pages}", inline=False)

        modes = []; 
        if state.loop_mode=="track": modes.append("🔂 Loop Track")
        elif state.loop_mode=="queue": modes.append("🔁 Loop Queue")
        if state.shuffle: modes.append("🔀 Shuffle")
        if state.auto_play: modes.append("🤖 Auto-Play")
        if modes: embed.add_field(name="Modes", value=" | ".join(modes), inline=False)

        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Music Queue")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="loop", description="Set loop mode (off/track/queue)")
    async def loop(self, ctx, mode: str = "track"):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        m = mode.lower()
        if m not in ("off","track","queue"): await ctx.send("🦇 Options: `off`, `track`, `queue`", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.loop_mode = m
        icons = {"off":"❌", "track":"🔂", "queue":"🔁"}
        await ctx.send(f"{icons[m]} Loop: **{m.upper()}**")

    @commands.hybrid_command(name="shuffle", description="Toggle shuffle mode")
    async def shuffle_cmd(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.shuffle = not state.shuffle
        await ctx.send(f"{ME['shuffle']} Shuffle: **{'ON' if state.shuffle else 'OFF'}**")

    @commands.hybrid_command(name="volume", description="Set volume (0-200)")
    async def volume(self, ctx, level: int):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.volume = max(0.0, min(2.0, level/100))
        await ctx.send(f"{ME['vol_up']} Volume: **{int(state.volume*100)}%**")

    @commands.hybrid_command(name="bassboost", description="Toggle bass boost filter")
    async def bassboost(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.bass_boost = not state.bass_boost; state.nightcore = False
        await ctx.send(f"🩸 Bass Boost: **{'ON' if state.bass_boost else 'OFF'}**")
        if state.current_track and state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
            await self._play_next(ctx.guild)

    @commands.hybrid_command(name="nightcore", description="Toggle nightcore filter")
    async def nightcore(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.nightcore = not state.nightcore; state.bass_boost = False
        await ctx.send(f"⚡ Nightcore: **{'ON' if state.nightcore else 'OFF'}**")
        if state.current_track and state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
            await self._play_next(ctx.guild)

    @commands.hybrid_command(name="autoplay", description="Toggle auto-play related songs")
    async def autoplay(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.auto_play = not state.auto_play
        await ctx.send(f"🤖 Auto-Play: **{'ON' if state.auto_play else 'OFF'}**")

    @commands.hybrid_command(name="seek", description="Seek to position in current track (seconds)")
    async def seek(self, ctx, seconds: int):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if not state.current_track or not state.voice_client: await ctx.send("🦇 Nothing playing.", ephemeral=True); return
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
        t = state.current_track; t.duration = max(0, t.duration - seconds)
        state.start_time = time.time() + seconds
        await self._play_next(ctx.guild)
        await ctx.send(f"⏩ Seeked to `{str(timedelta(seconds=seconds))}`")

    @commands.hybrid_command(name="restart", description="Restart current track from beginning")
    async def restart(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if not state.current_track: await ctx.send("🦇 Nothing playing.", ephemeral=True); return
        if state.voice_client: state.voice_client.stop()
        state.queue.appendleft(state.current_track)
        await self._play_next(ctx.guild)
        await ctx.send(f"{ME['prev']} Restarted!")

    @commands.hybrid_command(name="remove", description="Remove a track from queue by position")
    async def remove(self, ctx, position: int):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id)
        if position < 1 or position > len(state.queue):
            await ctx.send(f"🦇 Invalid position. Queue has {len(state.queue)} items.", ephemeral=True); return
        qlist = list(state.queue); removed = qlist.pop(position-1)
        state.queue = deque(qlist)
        await ctx.send(f"🗑️ Removed **{removed.title[:80]}**")

    @commands.hybrid_command(name="clearqueue", description="Clear the entire queue")
    async def clearqueue(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); cnt = len(state.queue); state.queue.clear()
        await ctx.send(f"🗑️ Cleared **{cnt}** tracks from queue.")

    @commands.hybrid_command(name="move", description="Move a track in the queue")
    async def move(self, ctx, from_pos: int, to_pos: int):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); qlist = list(state.queue)
        if from_pos < 1 or from_pos > len(qlist) or to_pos < 1 or to_pos > len(qlist):
            await ctx.send(f"🦇 Invalid. Queue: 1-{len(qlist)}", ephemeral=True); return
        item = qlist.pop(from_pos-1); qlist.insert(to_pos-1, item); state.queue = deque(qlist)
        await ctx.send(f"↔️ Moved **{item.title[:80]}** to #{to_pos}")

    @commands.hybrid_command(name="history", description="Show recently played tracks")
    async def history(self, ctx):
        state = self._get_state(ctx.guild.id)
        if not state.history:
            await ctx.send("📭 No history yet.", ephemeral=True); return
        embed = discord.Embed(title="📜 Recent History", color=MUSIC_COLORS["info"])
        for i, t in enumerate(reversed(list(state.history)[-10:]), 1):
            embed.add_field(name=f"{i}. {t.title[:80]}", value=f"{ME['dj']} {t.requester_name} | `{str(timedelta(seconds=t.duration))}`", inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • History")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="replay", description="Replay a track from history")
    async def replay(self, ctx, index: int = 1):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); hlist = list(state.history)
        if index < 1 or index > len(hlist): await ctx.send(f"🦇 Invalid. History: 1-{len(hlist)}", ephemeral=True); return
        t = hlist[-index]; state.queue.appendleft(t)
        if state.voice_client and state.voice_client.is_playing(): state.voice_client.stop()
        await self._play_next(ctx.guild)
        await ctx.send(f"🔁 Replaying: **{t.title[:80]}**")

    @commands.hybrid_command(name="playnext", description="Add a song to play after current track")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def playnext(self, ctx, *, query: str):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        await ctx.defer(); await self._ensure_voice(ctx)
        tracks = await self._extract_track(query, ctx)
        if not tracks: await ctx.send("🦇 Nothing found.", ephemeral=True)
        else:
            state = self._get_state(ctx.guild.id); state.queue.appendleft(tracks[0])
            await ctx.send(f"⏭️ Up next: **{tracks[0].title[:80]}**")

    @commands.hybrid_command(name="247", description="Toggle 24/7 mode (bot stays in VC)")
    async def twentyfourseven(self, ctx):
        if not await self._check_dj(ctx): await ctx.send("🦇 DJ only.", ephemeral=True); return
        state = self._get_state(ctx.guild.id); state.is_24_7 = not state.is_24_7
        await ctx.send(f"🦇 24/7 Mode: **{'ON' if state.is_24_7 else 'OFF'}**")

    @commands.hybrid_command(name="dj", description="Set the DJ role")
    @commands.has_permissions(manage_guild=True)
    async def set_dj(self, ctx, role: discord.Role):
        state = self._get_state(ctx.guild.id); state.dj_role_id = role.id
        await ctx.send(f"{ME['dj']} DJ role set to {role.mention}")

    @commands.hybrid_command(name="lyrics", description="Search for song lyrics")
    async def lyrics(self, ctx, *, query: str = None):
        await ctx.defer()
        state = self._get_state(ctx.guild.id)
        if not query and state.current_track: query = state.current_track.title
        if not query: await ctx.send("🦇 Provide a song name.", ephemeral=True); return
        # Simple lyrics search via web API
        import urllib.request, urllib.parse
        try:
            q = urllib.parse.quote(query)
            req = urllib.request.Request(f"https://api.lyrics.ovh/v1/{q}", headers={"User-Agent": "HiTechBot"})
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=8).read())
            data = json.loads(data)
            lyrics = data.get("lyrics", "No lyrics found.")
        except:
            # Fallback: generic search
            lyrics = f"🎵 Lyrics not available for: **{query}**\nTry a simpler song name without special characters."

        if len(lyrics) > 4000: lyrics = lyrics[:4000] + "\n..."
        embed = discord.Embed(title=f"📜 Lyrics — {query[:80]}", description=lyrics[:4096], color=MUSIC_COLORS["lyrics"])
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Lyrics")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="music_help", description="Show all music commands")
    async def music_help(self, ctx):
        embed = discord.Embed(title=f"{ME['bat']} Music Commands — 25+ Features",
            description="Advanced music system powered by YouTube. No premium needed!", color=MUSIC_COLORS["info"])
        cmds = [
            ("🎧 Playback", "`/play` `/play_now` `/playnext` `/search` `/skip` `/forceskip`"),
            ("⏯️ Controls", "`/pause` `/resume` `/stop` `/restart` `/seek` `/volume`"),
            ("📋 Queue", "`/queue` `/remove` `/clearqueue` `/move` `/shuffle` `/replay`"),
            ("🔄 Loop", "`/loop` `/autoplay` `/history` `/nowplaying`"),
            ("🎛️ Filters", "`/bassboost` `/nightcore` `/volume`"),
            ("📜 Extras", "`/lyrics` `/music_help` `/247` `/dj` `/disconnect`"),
        ]
        for name, val in cmds: embed.add_field(name=name, value=val, inline=False)
        embed.set_footer(text="🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞 • Free forever music system")
        await ctx.send(embed=embed)

    # ── Voice State Events ───────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            # Bot moved/disconnected
            if before.channel and not after.channel:
                state = self._get_state(before.channel.guild.id)
                state.voice_client = None; state.current_track = None
                state.queue.clear()


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE UI VIEWS — Music Control Buttons
# ═══════════════════════════════════════════════════════════════

class MusicControlView(discord.ui.View):
    """Music control buttons shown on Now Playing message."""
    def __init__(self, cog: Music, guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog; self.guild_id = guild_id

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="music_pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not state.voice_client:
            await interaction.response.send_message("Not connected.", ephemeral=True); return
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ permissions needed.", ephemeral=True); return
        if state.voice_client.is_playing():
            state.voice_client.pause(); state.paused = True; state.pause_time = time.time()
            await interaction.response.send_message("⏸️ Paused", ephemeral=True)
        elif state.voice_client.is_paused():
            state.voice_client.resume(); state.paused = False
            state.total_pause_time += time.time() - state.pause_time
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="music_skip")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        if state.voice_client: state.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        if state.voice_client: state.voice_client.stop()
        state.queue.clear(); state.loop_mode = "off"
        await interaction.response.send_message("⏹️ Stopped", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="music_shuffle")
    async def shuffle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        state.shuffle = not state.shuffle
        await interaction.response.send_message(f"🔀 Shuffle: {'ON' if state.shuffle else 'OFF'}", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="music_loop")
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        modes = ["off", "track", "queue"]; idx = modes.index(state.loop_mode)
        state.loop_mode = modes[(idx + 1) % 3]
        icons = {"off": "❌", "track": "🔂", "queue": "🔁"}
        await interaction.response.send_message(f"{icons[state.loop_mode]} Loop: **{state.loop_mode.upper()}**", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="music_vol_down")
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        state.volume = max(0.0, state.volume - 0.1)
        await interaction.response.send_message(f"🔉 Vol: {int(state.volume*100)}%", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="music_vol_up")
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        state.volume = min(2.0, state.volume + 0.1)
        await interaction.response.send_message(f"🔊 Vol: {int(state.volume*100)}%", ephemeral=True)

    @discord.ui.button(emoji="🩸", style=discord.ButtonStyle.success, custom_id="music_bass")
    async def bass_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog._get_state(self.guild_id)
        if not self._check_dj_interaction(interaction):
            await interaction.response.send_message("🦇 DJ needed.", ephemeral=True); return
        state.bass_boost = not state.bass_boost; state.nightcore = False
        await interaction.response.send_message(f"🩸 Bass: {'ON' if state.bass_boost else 'OFF'}", ephemeral=True)
        if state.current_track and state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
            await self.cog._play_next(self.cog.bot.get_guild(self.guild_id))

    def _check_dj_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator: return True
        if interaction.user.guild_permissions.manage_guild: return True
        state = self.cog._get_state(self.guild_id)
        if state.dj_role_id:
            role = interaction.guild.get_role(state.dj_role_id)
            if role and role in interaction.user.roles: return True
        dj_role = discord.utils.get(interaction.guild.roles, name="Hi-Tech DJ")
        if dj_role and dj_role in interaction.user.roles: return True
        return False


class MusicIdleView(discord.ui.View):
    """Buttons when queue is empty."""
    def __init__(self, cog: Music, guild_id: int):
        super().__init__(timeout=None)
        self.cog = cog; self.guild_id = guild_id

    @discord.ui.button(label="How to Play", emoji="🎵", style=discord.ButtonStyle.primary, custom_id="idle_how")
    async def how_btn(self, interaction, btn):
        await interaction.response.send_message("Use `/play song name` to search YouTube!\nNo premium or API keys needed. 🦇", ephemeral=True)

    @discord.ui.button(label="Music Help", emoji="📜", style=discord.ButtonStyle.secondary, custom_id="idle_help")
    async def help_btn(self, interaction, btn):
        await interaction.response.send_message("Use `/music_help` for all 25+ commands! 🦇", ephemeral=True)


class SearchSelectView(discord.ui.View):
    """Search result selection with buttons 1-10."""
    def __init__(self, cog: Music, ctx: commands.Context, results: List[Track]):
        super().__init__(timeout=30)
        self.cog = cog; self.ctx = ctx; self.results = results
        self.message: discord.Message = None
        for i in range(min(10, len(results))):
            btn = discord.ui.Button(label=str(i+1), style=discord.ButtonStyle.primary,
                custom_id=f"search_{i}", row=i//5)
            btn.callback = self.make_callback(i)
            self.add_item(btn)
        cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, row=2, custom_id="search_cancel")
        cancel.callback = self.cancel_cb
        self.add_item(cancel)

    def make_callback(self, idx):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("This is not your search!", ephemeral=True); return
            state = self.cog._get_state(self.ctx.guild.id)
            t = self.results[idx]; state.queue.append(t)
            if not state.current_track and state.voice_client and not state.voice_client.is_playing():
                await self.cog._play_next(self.ctx.guild)
            await interaction.response.send_message(f"✅ Added: **{t.title[:80]}**", ephemeral=True)
            try:
                if self.message: await self.message.edit(view=None)
            except: pass
            self.stop()
        return cb

    async def cancel_cb(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Not your search.", ephemeral=True); return
        await interaction.response.send_message("❌ Cancelled.", ephemeral=True)
        self.stop()
        try:
            if self.message: await self.message.delete()
        except: pass

    async def on_timeout(self):
        try:
            if self.message: await self.message.edit(view=None)
        except: pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))