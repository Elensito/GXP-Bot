import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

class RestoreGXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="restore_gxp", description="Restore a user's GXP for a specific date (server owner only)")
    @app_commands.describe(ign="Minecraft IGN", date="Date (YYYY-MM-DD)", gxp="GXP amount to restore")
    async def restore_gxp(self, interaction: discord.Interaction, ign: str, date: str, gxp: int):
        # Only server owner can use
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Only the server owner can use this command.", ephemeral=True)
            return
        try:
            async with aiosqlite.connect("db/gxp_data.db") as db:
                # Buscar UUID por IGN
                cursor = await db.execute("SELECT user_id FROM gxp WHERE ign=? LIMIT 1", (ign,))
                row = await cursor.fetchone()
                if not row:
                    await interaction.response.send_message(f"❌ IGN `{ign}` not found in database.", ephemeral=True)
                    return
                uuid = row[0]
                # Restaurar GXP para la fecha
                await db.execute(
                    "INSERT OR REPLACE INTO gxp (user_id, ign, date, daily_gxp) VALUES (?, ?, ?, ?)",
                    (uuid, ign, date, gxp)
                )
                await db.commit()
            await interaction.response.send_message(f"✅ Restored `{gxp}` GXP for `{ign}` on `{date}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RestoreGXP(bot))
