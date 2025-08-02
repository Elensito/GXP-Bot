import os
import aiohttp
import aiosqlite
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands

load_dotenv()
HYPIXEL_API_KEY = os.getenv("HYPIXEL_API_KEY")

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Verify(bot))
