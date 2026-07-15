"""🦇 Hi-Tech Security — Minimal Discord Bot"""
import os, sys, logging, asyncio
import discord
from discord.ext import commands
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

logging.basicConfig(level=logging.INFO, stream=sys.stdout, 
    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass

PORT = int(os.getenv("PORT","8080"))
threading.Thread(target=lambda: HTTPServer(("0.0.0.0",PORT),H).serve_forever(), daemon=True).start()
log.info(f"Health :{PORT}")

TOKEN = os.getenv("DISCORD_BOT_TOKEN","")
PREFIX = os.getenv("BOT_PREFIX","!")
if not TOKEN:
    log.critical("NO TOKEN!"); sys.exit(1)

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(PREFIX), 
                        intents=discord.Intents.all(), case_insensitive=True)

    async def setup_hook(self):
        cogs = ["cogs.moderation","cogs.automod","cogs.verification","cogs.threat_intel",
                "cogs.incident_alerts","cogs.audit_logging","cogs.anti_raid","cogs.admin",
                "cogs.help","cogs.music","cogs.reports","cogs.backup","cogs.server_config"]
        ok=0
        for c in cogs:
            try:
                await self.load_extension(c); ok+=1
            except Exception as e:
                log.error(f"Cog {c}: {e}")
        log.info(f"Cogs: {ok}/{len(cogs)}")
        try:
            await self.tree.sync()
            log.info(f"Synced {len(self.tree.get_commands())} cmds")
        except Exception as e:
            log.warning(f"Sync defer: {e}")

    async def on_ready(self):
        log.info(f"ONLINE: {self.user} | {len(self.guilds)} guilds | {len(self.tree.get_commands())} cmds")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="🦇 /bot_help"))

bot = Bot()

@bot.event
async def on_connect(): log.info("WS connected")
@bot.event
async def on_disconnect(): log.warning("WS disconnected")

log.info(f"Starting... token={len(TOKEN)}c dpy={discord.__version__}")
try:
    bot.run(TOKEN, log_handler=None)
except Exception as e:
    log.critical(f"CRASH: {e}")
    import traceback; traceback.print_exc()
