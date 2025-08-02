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

class Link(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="link", description="Sync all guild members and calculate Activity Points (server owner only)")
    async def link(self, interaction: discord.Interaction, guild_name: str):
        # Restrict to server owner only
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Only the server owner can use this command.", ephemeral=True)
            return
        # Guardar la guild para la tarea automática
        interaction.client.last_guild_name = guild_name
        await interaction.response.send_message(f"🔗 Fetching guild data for `{guild_name}`...", ephemeral=True)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.hypixel.net/guild?key={HYPIXEL_API_KEY}&name={guild_name}") as resp:
                    if resp.status != 200:
                        await interaction.edit_original_response(content=f"❌ Could not fetch guild {guild_name} from Hypixel. Status: {resp.status}")
                        return
                    data = await resp.json()
                    guild = data.get("guild")
                    if not guild or "members" not in guild:
                        await interaction.edit_original_response(content=f"❌ Guild `{guild_name}` not found or has no members.")
                        return
                    members = guild["members"]
                    total = len(members)
                    await interaction.edit_original_response(content=f"📊 Found {total} members. Processing data...")

            # Rango de días según reset Hypixel
            today_utc = datetime.now(timezone.utc)
            reset_hour, reset_minute = 6, 40
            reset_time = today_utc.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
            if today_utc < reset_time:
                gxp_day = (today_utc - timedelta(days=1)).date()
            else:
                gxp_day = today_utc.date()
            last_7_days = [(gxp_day - timedelta(days=i)).isoformat() for i in range(0, 7)]

            async with aiosqlite.connect("db/gxp_data.db") as db:
                for idx, member in enumerate(members, 1):
                    uuid = member.get("uuid")
                    # Obtener IGN real desde Mojang API
                    ign = None
                    try:
                        async with aiohttp.ClientSession() as mojang_session:
                            async with mojang_session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}") as mojang_resp:
                                if mojang_resp.status == 200:
                                    mojang_data = await mojang_resp.json()
                                    ign = mojang_data.get("name")
                    except Exception as e:
                        print(f"[GXP SYNC][WARN] Error obteniendo IGN para {uuid}: {e}")
                    if not ign:
                        continue
                    exp_history = member.get("expHistory", {})
                    for day in last_7_days:
                        gxp = exp_history.get(day, 0)
                        await db.execute(
                            "INSERT OR REPLACE INTO gxp (user_id, ign, date, daily_gxp) VALUES (?, ?, ?, ?)",
                            (uuid, ign, day, gxp)
                        )
                    if idx % 10 == 0 or idx == total:
                        await interaction.edit_original_response(content=f"⚡ Processing {idx}/{total} members...")
                await db.commit()

                # Calcular Activity Points para cada día
                for day in last_7_days:
                    rows = await db.execute_fetchall(
                        "SELECT user_id, daily_gxp FROM gxp WHERE date=? ORDER BY daily_gxp DESC", (day,)
                    )
                    for rank, (uid, gxp) in enumerate(rows):
                        ap = round(1.0 - (rank * 0.1), 1) if gxp > 0 and rank < 10 else 0.0
                        await db.execute(
                            "UPDATE gxp SET activity_points=? WHERE user_id=? AND date=?",
                            (ap, uid, day)
                        )
                await db.commit()

                # Restar Activity Points gastados en la tienda
                shop_rows = await db.execute_fetchall("SELECT user_id, SUM(amount) FROM shop GROUP BY user_id")
                for uid, spent in shop_rows:
                    ap_total_row = await db.execute_fetchone("SELECT SUM(activity_points) FROM gxp WHERE user_id=?", (uid,))
                    ap_total = ap_total_row[0] if ap_total_row and ap_total_row[0] else 0.0
                    ap_final = max(ap_total - (spent or 0), 0.0)
                    await db.execute("UPDATE user_map SET activity_points=? WHERE user_id=?", (ap_final, uid))
                await db.commit()

            await interaction.edit_original_response(content=f"✅ Synchronization and calculation completed for `{guild_name}` ({total} members).")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(Link(bot))
