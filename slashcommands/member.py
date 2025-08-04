import discord
from discord.ext import commands
from discord import app_commands

class Member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="member", description="Show your GXP and Activity Points")
    async def member(self, interaction: discord.Interaction, ign: str = None):
        import datetime
        import aiosqlite
        GXP_COLOR = 0x43FF43
        XP_EMOJI = "<:xp:1396916494746779829>"

        def format_number(num):
            """Formatea números con separadores de miles usando puntos"""
            if num is None:
                return "0"
            return f"{int(num):,}".replace(",", ".")

        # Si no se especifica IGN, buscarlo en user_map por discord_id
        if not ign:
            user_id = str(interaction.user.id)
            async with aiosqlite.connect("db/gxp_data.db") as db:
                cursor = await db.execute("SELECT ign FROM user_map WHERE discord_id=?", [user_id])
                row = await cursor.fetchone()
                if row and row[0]:
                    ign = row[0]
                else:
                    ign = interaction.user.display_name
        # Solo responde si no se ha respondido ya
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("Loading...")
        except Exception:
            pass
        try:
            async with aiosqlite.connect("db/gxp_data.db") as db:
                cursor = await db.execute("SELECT user_id FROM gxp WHERE ign=? ORDER BY date DESC LIMIT 1", [ign])
                row = await cursor.fetchone()
                if not row:
                    await interaction.edit_original_response(content=f"❌ IGN `{ign}` not found in database.")
                    return
                user_id = row[0]
                today = datetime.datetime.utcnow().date()
                last_7_days = [(today - datetime.timedelta(days=i)).isoformat() for i in range(0, 7)]
                gxp_map = {}
                rows = await db.execute_fetchall("SELECT date, daily_gxp FROM gxp WHERE user_id=? AND date IN ({seq})".format(seq=','.join(['?']*len(last_7_days))), [user_id] + last_7_days)
                for date, daily_gxp in rows:
                    gxp_map[date] = daily_gxp
                gxp_rows = [(date, gxp_map.get(date, 0)) for date in last_7_days]
                # Monthly GXP: suma de los últimos 30 días
                from datetime import datetime, timedelta
                today2 = datetime.utcnow().date()
                thirty_days_ago = (today2 - timedelta(days=29)).isoformat()  # 30 días incluyendo hoy
                monthly_cursor = await db.execute(
                    "SELECT SUM(COALESCE(daily_gxp, 0)) FROM gxp WHERE user_id=? AND date >= ?",
                    [user_id, thirty_days_ago]
                )
                monthly_row = await monthly_cursor.fetchone()
                monthly_gxp_sum = int(monthly_row[0]) if monthly_row and monthly_row[0] is not None else 0
                
                # Lifetime GXP: suma de todos los días registrados
                lifetime_cursor = await db.execute(
                    "SELECT SUM(COALESCE(daily_gxp, 0)) FROM gxp WHERE user_id=?", 
                    [user_id]
                )
                lifetime_row = await lifetime_cursor.fetchone()
                lifetime_gxp_sum = int(lifetime_row[0]) if lifetime_row and lifetime_row[0] is not None else 0
                # Activity Points: suma de TODOS los días menos el actual, menos lo gastado en shop
                today_str = today.isoformat()
                ap_cursor = await db.execute(
                    "SELECT SUM(COALESCE(activity_points, 0)) FROM gxp WHERE user_id=? AND date <> ?",
                    [user_id, today_str]
                )
                ap_row = await ap_cursor.fetchone()
                ap_total = float(ap_row[0]) if ap_row and ap_row[0] is not None else 0.0
                spent_cursor = await db.execute("SELECT SUM(COALESCE(amount, 0)) FROM shop WHERE user_id=?", [user_id])
                spent_row = await spent_cursor.fetchone()
                spent = float(spent_row[0]) if spent_row and spent_row[0] is not None else 0.0
                activity_points_sum = max(ap_total - spent, 0.0)
            gxp_rows = list(gxp_rows)
            gxp_rows.sort(reverse=True)  # hoy primero
            embed = discord.Embed(title=f"GXP & Activity Points", color=GXP_COLOR)
            embed.set_author(name=ign)
            gxp_str = ""
            weekly_gxp_sum = 0
            # Obtener el top de cada día
            async with aiosqlite.connect("db/gxp_data.db") as db2:
                for date, daily_gxp in gxp_rows:
                    # Obtener ranking para ese día
                    top_cursor = await db2.execute(
                        "SELECT user_id, daily_gxp FROM gxp WHERE date=? ORDER BY daily_gxp DESC", [date]
                    )
                    top_rows = await top_cursor.fetchall()
                    rank = None
                    for idx, (uid, gxp_val) in enumerate(top_rows, 1):
                        if uid == user_id:
                            rank = idx
                            break
                    if rank is not None:
                        gxp_str += f"`{date}: {format_number(daily_gxp or 0)}  #{rank}`\n"
                    else:
                        gxp_str += f"`{date}: {format_number(daily_gxp or 0)}`\n"
                    weekly_gxp_sum += daily_gxp or 0
            embed.add_field(name="GXP Last 7 Days", value=gxp_str, inline=False)
            embed.add_field(name="Weekly GXP", value=f"`{format_number(weekly_gxp_sum)}`", inline=True)
            embed.add_field(name="Monthly GXP", value=f"`{format_number(monthly_gxp_sum)}`", inline=True)
            embed.add_field(name="Lifetime GXP", value=f"`{format_number(lifetime_gxp_sum)}`", inline=True)
            ap_sum_fmt = f"{round(activity_points_sum, 1):.1f}"
            embed.add_field(name=f"Activity Points {XP_EMOJI}", value=f"`{ap_sum_fmt}`", inline=False)
            embed.set_footer(text="Data updated according to Hypixel daily reset (06:40 UTC)")
            await interaction.edit_original_response(content=None, embed=embed)
        except Exception as e:
            try:
                await interaction.edit_original_response(content=f"❌ Error: {e}")
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(Member(bot))
