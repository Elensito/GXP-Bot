import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import aiosqlite

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)


# Cargar todos los comandos slash y sincronizarlos con Discord
async def load_slashcommands():
    for filename in os.listdir("./slashcommands"):
        if filename.endswith(".py"):
            await bot.load_extension(f"slashcommands.{filename[:-3]}")
    # Sincronizar los comandos slash con Discord
    try:
        synced = await bot.tree.sync()
        print(f"Comandos slash sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error al sincronizar comandos slash: {e}")

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    await load_slashcommands()

    # --- Recalcular activity points para días sin AP al iniciar el bot ---
    import aiosqlite
    from datetime import datetime, timedelta, timezone
    async def recalc_missing_activity_points():
        async with aiosqlite.connect("db/gxp_data.db") as db:
            # Buscar días con registros de GXP pero activity_points NULL o vacíos
            days_cursor = await db.execute("SELECT DISTINCT date FROM gxp")
            all_days = [row[0] for row in await days_cursor.fetchall()]
            for d in all_days:
                # ¿Hay algún registro sin activity_points?
                rows = await db.execute_fetchall("SELECT user_id, daily_gxp, activity_points FROM gxp WHERE date=?", (d,))
                needs_recalc = any(ap is None for _, _, ap in rows)
                if needs_recalc:
                    # Recalcular para ese día
                    rows_sorted = sorted(rows, key=lambda x: x[1], reverse=True)
                    for rank, (uid, gxp, _) in enumerate(rows_sorted):
                        ap = round(1.0 - (rank * 0.1), 1) if gxp > 0 and rank < 10 else 0.0
                        await db.execute("UPDATE gxp SET activity_points=? WHERE user_id=? AND date=?", (ap, uid, d))
                    await db.commit()
                    print(f"[AP RECALC] Activity Points recalculated for {d}")
    await recalc_missing_activity_points()

    # --- Tarea automática de actualización de GXP cada minuto ---
    import aiohttp
    import os
    from dotenv import load_dotenv
    load_dotenv()
    HYPIXEL_API_KEY = os.getenv("HYPIXEL_API_KEY")
    UPDATE_GUILD = os.getenv("UPDATE_GUILD")
    bot.last_guild_name = UPDATE_GUILD if UPDATE_GUILD else None

    async def auto_gxp_sync():
        while True:
            try:
                guild_name = UPDATE_GUILD if UPDATE_GUILD else getattr(bot, 'last_guild_name', None)
                if not HYPIXEL_API_KEY or not guild_name:
                    print("[GXP SYNC] Waiting for /link to be used or UPDATE_GUILD to be defined...")
                    await asyncio.sleep(60)
                    continue
                print(f"[GXP SYNC] Syncing GXP for guild '{guild_name}'...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.hypixel.net/guild?key={HYPIXEL_API_KEY}&name={guild_name}") as resp:
                        if resp.status != 200:
                            print(f"[GXP SYNC] Error fetching guild: Status {resp.status}")
                            await asyncio.sleep(60)
                            continue
                        data = await resp.json()
                        guild = data.get("guild")
                        if not guild or "members" not in guild:
                            print(f"[GXP SYNC] Guild '{guild_name}' not found or has no members.")
                            await asyncio.sleep(60)
                            continue
                        members = guild["members"]
                        today_utc = datetime.now(timezone.utc)
                        reset_hour, reset_minute = 6, 40
                        reset_time = today_utc.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
                        if today_utc < reset_time:
                            gxp_day = (today_utc - timedelta(days=1)).date()
                        else:
                            gxp_day = today_utc.date()
                        last_7_days = [(gxp_day - timedelta(days=i)).isoformat() for i in range(0, 7)]
                        async with aiosqlite.connect("db/gxp_data.db") as db:
                            for member in members:
                                uuid = member.get("uuid")
                                
                                # Verificar si ya existe un IGN para este user_id
                                cursor = await db.execute("SELECT ign FROM gxp WHERE user_id=? ORDER BY date DESC LIMIT 1", (uuid,))
                                existing_row = await cursor.fetchone()
                                
                                if existing_row and existing_row[0] and existing_row[0] != uuid:
                                    # Si ya existe un IGN válido (no es UUID), lo mantenemos
                                    ign = existing_row[0]
                                else:
                                    # Si no existe o es UUID, obtener IGN real desde Mojang API
                                    ign = None
                                    try:
                                        async with aiohttp.ClientSession() as mojang_session:
                                            async with mojang_session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}") as mojang_resp:
                                                if mojang_resp.status == 200:
                                                    mojang_data = await mojang_resp.json()
                                                    ign = mojang_data.get("name")
                                    except Exception as e:
                                        print(f"[GXP SYNC][WARN] Error obteniendo IGN para {uuid}: {e}")
                                    
                                    # Si no pudimos obtener el IGN, usar el UUID como fallback
                                    if not ign:
                                        ign = uuid
                                
                                exp_history = member.get("expHistory", {})
                                for day in last_7_days:
                                    if day in exp_history:
                                        gxp = exp_history[day]
                                        # Solo actualiza si el valor es mayor que 0
                                        if gxp > 0:
                                            cursor = await db.execute("SELECT daily_gxp FROM gxp WHERE user_id=? AND date=?", (uuid, day))
                                            row = await cursor.fetchone()
                                            prev_gxp = row[0] if row else None
                                            await db.execute(
                                                "INSERT OR REPLACE INTO gxp (user_id, ign, date, daily_gxp) VALUES (?, ?, ?, ?)",
                                                (uuid, ign, day, gxp)
                                            )
                                            if prev_gxp != gxp:
                                                print(f"[GXP SYNC] {ign} | {day}: {prev_gxp} -> {gxp}")
                            await db.commit()
                            
                            # Recalcular Activity Points para los días actualizados
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
                print(f"[GXP SYNC] Update completed.")
            except Exception as e:
                print(f"[GXP SYNC] Error: {e}")
            await asyncio.sleep(60)

    bot.loop.create_task(auto_gxp_sync())

    from datetime import datetime, timedelta, timezone
    async def daily_recalc_task():
        last_checked_day = None
        while True:
            today_utc = datetime.now(timezone.utc)
            reset_hour = 6
            reset_minute = 40
            reset_time = today_utc.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
            if today_utc < reset_time:
                gxp_day = (today_utc - timedelta(days=1)).date()
            else:
                gxp_day = today_utc.date()
            # Aquí podrías poner lógica de recálculo si lo deseas
            if last_checked_day is None or gxp_day != last_checked_day:
                last_checked_day = gxp_day
            await asyncio.sleep(180)

    bot.loop.create_task(daily_recalc_task())

if __name__ == "__main__":
    bot.run(TOKEN)
