import discord
from discord.ext import commands
from discord import app_commands

BOT_VERSION = "1.0.0"
BOT_FEATURES = [
    "/verify: Link your Minecraft account to Discord",
    "/member: View your GXP and Activity Points",
    "/leaderboard: Guild GXP leaderboard (weekly, monthly, lifetime)",
    "/shop: Spend Activity Points on guild perks",
    "/inventory: View your purchased items from the Guild Shop",
]

class Version(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="version", description="Show bot version and features (server owner only)")
    async def version(self, interaction: discord.Interaction):
        # Restrict to server owner only
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Only the server owner can use this command.", ephemeral=True)
            return
        embed = discord.Embed(title=f"GXP Bot Version {BOT_VERSION}", color=0x4A90E2)
        embed.description = (
            "Current Features:\n" + "\n".join(f"- {f}" for f in BOT_FEATURES)
        )
        embed.set_footer(text="Last update: 2025/08/02")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Version(bot))
