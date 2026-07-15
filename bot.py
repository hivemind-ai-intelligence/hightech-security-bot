"""🦇 Hi-Tech Security — Devil Mode"""
import os, sys, logging, asyncio, threading, subprocess
import discord
from discord.ext import commands
from http.server import HTTPServer, BaseHTTPRequestHandler
import yt_dlp
from datetime import timedelta

# OPUS fix
import ctypes
try: ctypes.cdll.LoadLibrary("/usr/local/lib/libopus.so.0")
except: pass

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self,*a): pass
threading.Thread(target=lambda: HTTPServer(("0.0.0.0",int(os.getenv("PORT","8080"))),H).serve_forever(), daemon=True).start()

TOKEN = os.getenv("DISCORD_BOT_TOKEN","")
PREFIX = os.getenv("BOT_PREFIX","!")
if not TOKEN: log.critical("NO TOKEN!"); sys.exit(1)

ytdl = yt_dlp.YoutubeDL({"format":"bestaudio/best","noplaylist":True,"quiet":True,"no_warnings":True,"extract_flat":False})

def yt_search(query, limit=3):
    try:
        info = ytdl.extract_info(f"ytsearch{limit}:{query}", download=False)
        return [{"title":(e.get("title")or"?")[:200],"url":e.get("webpage_url")or e.get("url")or"","duration":int(e.get("duration")or 0)} for e in (info.get("entries")or[]) if e]
    except: return []

FFMPEG_OPTS = {"before_options":"-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5","options":"-vn"}
queues = {}

def play_next(gid, vc):
    q = queues.get(gid,[])
    if not q or not vc or not vc.is_connected():
        if vc and vc.is_connected(): asyncio.ensure_future(vc.disconnect())
        return
    song = q.pop(0)
    try:
        info = ytdl.extract_info(song["url"], download=False)
        surl = info.get("url") or ""
        if not surl:
            for fmt in (info.get("formats") or []):
                if fmt.get("acodec")!="none" and fmt.get("url"): surl=fmt["url"]; break
        if surl:
            src = discord.FFmpegPCMAudio(surl, **FFMPEG_OPTS)
            vc.play(src, after=lambda e: play_next(gid, vc))
    except Exception as ex:
        log.error(f"play_next: {ex}")
        play_next(gid, vc)

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(PREFIX), intents=discord.Intents.all(), case_insensitive=True)
    async def on_ready(self):
        log.info(f"ONLINE: {self.user} | {len(self.guilds)} guilds")

bot = Bot()

@bot.command(name="play", aliases=["p"])
async def play_cmd(ctx, *, query: str = ""):
    if not query: return await ctx.send("Usage: `!play song name`")
    if not ctx.author.voice: return await ctx.send("Join a voice channel first!")
    vc = ctx.voice_client
    if not vc:
        try: vc = await ctx.author.voice.channel.connect(timeout=10, reconnect=True)
        except Exception as e: return await ctx.send(f"Cant join: {e}")
    
    msg = await ctx.send(f"Searching: `{query}`...")
    results = []
    if query.startswith("http"):
        try:
            info = ytdl.extract_info(query, download=False)
            results = [{"title":info.get("title","?"),"url":info.get("webpage_url",query),"duration":int(info.get("duration")or 0)}]
        except: pass
    else:
        results = yt_search(query, 3)
    
    if not results: return await msg.edit(content=f"No results for: `{query}`")
    
    gid = ctx.guild.id
    if gid not in queues: queues[gid] = []
    for r in results[:3]: queues[gid].append(r)
    
    t = results[0]
    dur = str(timedelta(seconds=t["duration"])) if t["duration"] else "?"
    embed = discord.Embed(title="Added to Queue", description=f"[{t['title']}]({t['url']})\n`{dur}`", color=0x8B0000)
    embed.set_footer(text=f"Hi-Tech | {len(queues[gid])} in queue")
    await msg.edit(content=None, embed=embed)
    
    if not vc.is_playing() and not vc.is_paused():
        play_next(gid, vc)

@bot.command(aliases=["s"])
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing(): vc.stop(); await ctx.send("Skipped!")
    else: await ctx.send("Nothing playing")

@bot.command(aliases=["dc","leave"])
async def stop(ctx):
    gid = ctx.guild.id; queues.pop(gid, None)
    vc = ctx.voice_client
    if vc:
        if vc.is_playing(): vc.stop()
        await vc.disconnect()
    await ctx.send("Stopped!")

@bot.command(aliases=["q"])
async def queue(ctx):
    q = queues.get(ctx.guild.id,[])
    if not q: return await ctx.send("Queue empty")
    lines = [f"{i+1}. [{s['title'][:50]}]({s['url']}) `{str(timedelta(seconds=s['duration']))}`" for i,s in enumerate(q[:10])]
    await ctx.send(embed=discord.Embed(title=f"Queue ({len(q)})",description="\n".join(lines),color=0x8B0000))

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing(): vc.pause(); await ctx.send("Paused")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused(): vc.resume(); await ctx.send("Resumed")

@bot.command(aliases=["np"])
async def nowplaying(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        q = queues.get(ctx.guild.id,[])
        await ctx.send(f"{'Paused' if vc.is_paused() else 'Playing'} | Queue: {len(q)}")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Ping: {round(bot.latency*1000)}ms")

@bot.command(name="bothelp", aliases=["bh"])
async def bothelp_cmd(ctx):
    embed = discord.Embed(title="Hi-Tech Security Commands", color=0x8B0000)
    embed.add_field(name="Music", value="`!play song` `!skip` `!stop` `!pause` `!resume` `!queue` `!np`", inline=False)
    embed.add_field(name="Other", value="`!ping` `!bothelp`", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and after.channel is None:
        gid = before.channel.guild.id if before.channel else None
        if gid: queues.pop(gid, None)

log.info("STARTING...")
bot.run(TOKEN, log_handler=None)
