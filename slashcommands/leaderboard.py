import discord
from discord.ext import commands
from discord import app_commands

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Top members by weekly, monthly and lifetime GXP")
    async def leaderboard(self, interaction: discord.Interaction):
        # Responder inmediatamente para evitar timeout
        await interaction.response.send_message("🔄 Loading leaderboard...")
        
        import aiosqlite
        import discord
        XP_EMOJI = "<:xp:1396916494746779829>"
        # Colores para cada categoría
        DAILY_COLOR = 0xFF6B35    # Naranja vibrante
        WEEKLY_COLOR = 0x43FF43   # Verde original
        MONTHLY_COLOR = 0x4A90E2  # Azul
        LIFETIME_COLOR = 0x9B59B6 # Púrpura
        
        def format_number(num):
            """Formatea números con separadores de miles usando puntos"""
            if num is None:
                return "0"
            return f"{int(num):,}".replace(",", ".")
        
        async with aiosqlite.connect("db/gxp_data.db") as db:
            # Calculate current GXP day based on Hypixel reset time
            import datetime
            today_utc = datetime.datetime.utcnow()
            reset_hour = 6
            reset_minute = 40
            reset_time = today_utc.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
            if today_utc < reset_time:
                gxp_day = (today_utc - datetime.timedelta(days=1)).date()
            else:
                gxp_day = today_utc.date()
            
            # Daily GXP: GXP del día actual
            daily_query = """
            SELECT ign, COALESCE(daily_gxp, 0) as daily_total
            FROM gxp 
            WHERE date = ? AND ign IS NOT NULL
            ORDER BY daily_total DESC 
            LIMIT 15
            """
            daily = await db.execute_fetchall(daily_query, [gxp_day.isoformat()])
            
            # Weekly GXP: suma de últimos 7 días por usuario
            last_7_days = [(gxp_day - datetime.timedelta(days=i)).isoformat() for i in range(0, 7)]
            
            # Weekly leaderboard
            weekly_query = """
            SELECT ign, SUM(COALESCE(daily_gxp, 0)) as weekly_total
            FROM gxp 
            WHERE date IN ({seq}) AND ign IS NOT NULL
            GROUP BY user_id, ign
            ORDER BY weekly_total DESC 
            LIMIT 15
            """.format(seq=','.join(['?']*len(last_7_days)))
            weekly = await db.execute_fetchall(weekly_query, last_7_days)
            
            # Monthly leaderboard (últimos 30 días)
            thirty_days_ago = (gxp_day - datetime.timedelta(days=29)).isoformat()
            monthly_query = """
            SELECT ign, SUM(COALESCE(daily_gxp, 0)) as monthly_total
            FROM gxp 
            WHERE date >= ? AND ign IS NOT NULL
            GROUP BY user_id, ign
            ORDER BY monthly_total DESC 
            LIMIT 15
            """
            monthly = await db.execute_fetchall(monthly_query, [thirty_days_ago])
            
            # Lifetime leaderboard
            lifetime_query = """
            SELECT ign, SUM(COALESCE(daily_gxp, 0)) as lifetime_total
            FROM gxp 
            WHERE ign IS NOT NULL
            GROUP BY user_id, ign
            ORDER BY lifetime_total DESC 
            LIMIT 15
            """
            lifetime = await db.execute_fetchall(lifetime_query)
        # Format leaderboard with max 15 members per field, never exceeding 1024 chars
        async def get_real_ign(ign, user_id):
            """Obtiene el IGN real si el actual es un UUID"""
            # Si el IGN parece ser un UUID (32 caracteres hex), intentar obtener el IGN real
            if len(ign) == 32 and ign.replace('-', '').isalnum():
                try:
                    # Primero intentar buscar en la base de datos
                    async with aiosqlite.connect("db/gxp_data.db") as db:
                        cursor = await db.execute(
                            "SELECT ign FROM gxp WHERE user_id=? AND ign != ? AND LENGTH(ign) < 20 ORDER BY date DESC LIMIT 1",
                            [user_id, ign]
                        )
                        row = await cursor.fetchone()
                        if row and row[0]:
                            return row[0]
                    
                    # Si no encontramos en la base de datos, usar API de Mojang
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{ign}", timeout=2) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                real_ign = data.get("name")
                                if real_ign:
                                    return real_ign
                except Exception as e:
                    print(f"[LEADERBOARD][WARN] Error obteniendo IGN para {ign}: {e}")
            return ign
        
        async def format_lb_field(rows, gxp_type):
            # Calculate Activity Points for last 6 days (excluding today)
            last_6_days = [(gxp_day - datetime.timedelta(days=i)).isoformat() for i in range(1, 7)]
            
            async def get_user_id(ign):
                async with aiosqlite.connect("db/gxp_data.db") as db:
                    cursor = await db.execute("SELECT user_id FROM gxp WHERE ign=? ORDER BY date DESC LIMIT 1", [ign])
                    r = await cursor.fetchone()
                    return r[0] if r else None
            
            async def get_ap_sum(user_id):
                if not user_id:
                    return 0.0
                async with aiosqlite.connect("db/gxp_data.db") as db:
                    # Activity Points suma de últimos 6 días
                    ap_cursor = await db.execute(
                        "SELECT SUM(COALESCE(activity_points, 0)) FROM gxp WHERE user_id=? AND date IN ({seq})".format(seq=','.join(['?']*len(last_6_days))),
                        [user_id] + last_6_days
                    )
                    ap_row = await ap_cursor.fetchone()
                    ap_total = float(ap_row[0]) if ap_row and ap_row[0] is not None else 0.0
                    
                    # Restar lo gastado en shop
                    spent_cursor = await db.execute("SELECT SUM(COALESCE(amount, 0)) FROM shop WHERE user_id=?", [user_id])
                    spent_row = await spent_cursor.fetchone()
                    spent = float(spent_row[0]) if spent_row and spent_row[0] is not None else 0.0
                    return max(ap_total - spent, 0.0)
            
            lines = []
            total_len = 0
            for i, row in enumerate(rows):
                ign = row[0]
                gxp_value = row[1] if row[1] is not None else 0
                
                # Obtener user_id y arreglar IGN si es necesario
                user_id = await get_user_id(ign)
                real_ign = await get_real_ign(ign, user_id)
                
                # Obtener Activity Points
                ap_sum = await get_ap_sum(user_id)
                ap_sum_fmt = f"{round(ap_sum, 1):.1f}"
                
                line = f"`{i+1}.` {real_ign}: `{format_number(gxp_value)}` GXP {XP_EMOJI} `{ap_sum_fmt}`"
                if total_len + len(line) + 1 > 1024:
                    break
                lines.append(line)
                total_len += len(line) + 1
            return "\n".join(lines)
        embed = discord.Embed(title="Guild Leaderboard", color=DAILY_COLOR)
        daily_field = await format_lb_field(daily, "daily")
        embed.add_field(name="Daily GXP", value=daily_field, inline=False)
        embed.set_footer(text="Use the menu to view other categories")
        # Dropdown menu
        class LBView(discord.ui.View):
            @discord.ui.select(placeholder="Select leaderboard", options=[
                discord.SelectOption(label="Daily", value="daily", description="Current day GXP", emoji="🔥"),
                discord.SelectOption(label="Weekly", value="weekly", description="Last 7 days GXP", emoji="📅"),
                discord.SelectOption(label="Monthly", value="monthly", description="Last 30 days GXP", emoji="📊"),
                discord.SelectOption(label="Lifetime", value="lifetime", description="Total accumulated GXP", emoji="👑")
            ])
            async def select_callback(self, interaction2: discord.Interaction, select):
                embed.clear_fields()
                if select.values[0] == "daily":
                    embed.color = DAILY_COLOR
                    daily_field = await format_lb_field(daily, "daily")
                    embed.add_field(name="Daily GXP", value=daily_field, inline=False)
                elif select.values[0] == "weekly":
                    embed.color = WEEKLY_COLOR
                    weekly_field = await format_lb_field(weekly, "weekly")
                    embed.add_field(name="Weekly GXP", value=weekly_field, inline=False)
                elif select.values[0] == "monthly":
                    embed.color = MONTHLY_COLOR
                    monthly_field = await format_lb_field(monthly, "monthly")
                    embed.add_field(name="Monthly GXP", value=monthly_field, inline=False)
                elif select.values[0] == "lifetime":
                    embed.color = LIFETIME_COLOR
                    lifetime_field = await format_lb_field(lifetime, "lifetime")
                    embed.add_field(name="Lifetime GXP", value=lifetime_field, inline=False)
                await interaction2.response.edit_message(embed=embed)
        await interaction.edit_original_response(content=None, embed=embed, view=LBView())

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
