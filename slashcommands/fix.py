import os
import aiosqlite
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands

load_dotenv()

class Fix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fix", description="Recalculate all Activity Points from the database (server owner only)")
    @app_commands.describe(tipo="Fix type: activity-points")
    async def fix(self, interaction: discord.Interaction, tipo: str):
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Only the server owner can use this command.", ephemeral=True)
            return
        if tipo != "activity-points":
            await interaction.response.send_message("❌ Fix type not supported. Use: activity-points", ephemeral=True)
            return
        await interaction.response.send_message("🔄 Recalculating Activity Points for all days...", ephemeral=True)
        try:
            async with aiosqlite.connect("db/gxp_data.db") as db:
                days_rows = await db.execute_fetchall("SELECT DISTINCT date FROM gxp")
                all_days = [row[0] for row in days_rows]
                for d in all_days:
                    rows = await db.execute_fetchall("SELECT user_id, daily_gxp FROM gxp WHERE date=? ORDER BY daily_gxp DESC", [d])
                    for rank_idx, row in enumerate(rows):
                        uid, gxp = row
                        ap = round(1.0 - (rank_idx * 0.1), 1) if gxp > 0 and rank_idx < 10 else 0.0
                        await db.execute("UPDATE gxp SET activity_points=? WHERE user_id=? AND date=?", (ap, uid, d))
                await db.commit()
                # Restar activity points gastados en la tienda
                shop_rows = await db.execute_fetchall("SELECT user_id, SUM(amount) FROM shop GROUP BY user_id")
                for uid, spent in shop_rows:
                    ap_total_row = await db.execute_fetchone("SELECT SUM(activity_points) FROM gxp WHERE user_id=?", (uid,))
                    ap_total = ap_total_row[0] if ap_total_row and ap_total_row[0] else 0.0
                    ap_final = max(ap_total - (spent or 0), 0.0)
                    await db.execute("UPDATE user_map SET activity_points=? WHERE user_id=?", (ap_final, uid))
                await db.commit()
            await interaction.edit_original_response(content="✅ All Activity Points have been recalculated and deducted according to shop purchases.")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(Fix(bot))
