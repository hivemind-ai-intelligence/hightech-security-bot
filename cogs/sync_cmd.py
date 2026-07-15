"""🦇 Manual Sync Command"""
import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class SyncCmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sync", description="🔄 Sync all slash commands (owner only)")
    async def sync_cmd(self, interaction: discord.Interaction):
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            await interaction.response.send_message("❌ Owner only!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"✅ Synced {len(synced)} commands!", ephemeral=True)
            logger.info(f"Manual sync: {len(synced)} cmds")
        except discord.HTTPException as e:
            if e.status == 429:
                rt = getattr(e, 'retry_after', 60)
                await interaction.followup.send(f"⏳ Rate limited — retry in {rt:.0f}s", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SyncCmd(bot))
