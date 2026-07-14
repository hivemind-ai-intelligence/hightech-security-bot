"""
Shared utility helpers used across all cogs.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import discord
from discord.ext import commands

DATA_DIR = Path("data")


def get_server_data_path(guild_id: int, filename: str) -> Path:
    """Get per-server data file path."""
    server_dir = DATA_DIR / str(guild_id)
    server_dir.mkdir(parents=True, exist_ok=True)
    return server_dir / filename


def load_json(path: Path, default: Any = None) -> Any:
    """Safely load a JSON file."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: Path, data: Any):
    """Safely save data to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def make_embed(
    title: str,
    description: str = "",
    color: int = 0x8B0000,
    footer: str = "🦇 𝕳𝖎-𝕿𝖊𝖈𝖍 𝕾𝖊𝖈𝖚𝖗𝖎𝖙𝖞",
    fields: list = None,
) -> discord.Embed:
    """Create a themed embed quickly."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if footer:
        embed.set_footer(text=footer)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    return embed


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {mins}m"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


def get_channel_safe(guild: discord.Guild, channel_id: int) -> Optional[discord.TextChannel]:
    """Safely get a channel, return None if not found."""
    return guild.get_channel(channel_id) if channel_id else None
