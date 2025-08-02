import discord
from discord.ext import commands
from discord import app_commands

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Guild Shop for Activity Points")
    async def shop(self, interaction: discord.Interaction):
        import aiosqlite
        XP_EMOJI = "<:xp:1396916494746779829>"
        TIER_1 = "<:tier_1:1396932891685949570>"
        TIER_2 = "<:tier_2:1396932952763400262>"
        TIER_3 = "<:tier_3:1396932981876068432>"
        AFK_PASS = "<:afk_pass:1396930235030831316>"
        items = [
            {"name": "Tier 1 Rank", "emoji": TIER_1, "cost": 100.0, "desc": "Part needed to unlock Tier 1 rank in the guild"},
            {"name": "Tier 2 Rank", "emoji": TIER_2, "cost": 30.0, "desc": "Part needed to unlock Tier 2 rank in the guild"},
            {"name": "Tier 3 Rank", "emoji": TIER_3, "cost": 7.5, "desc": "Part needed to unlock Tier 3 rank in the guild"},
            {"name": "AFK Pass", "emoji": AFK_PASS, "cost": 3.0, "desc": "Permits to not need to do the GXP weekly requirement in order to not get kicked from the guild"}
        ]
        user_id = str(interaction.user.id)
        async with aiosqlite.connect("db/gxp_data.db") as db:
            ap_row = await db.execute_fetchone("SELECT activity_points FROM gxp WHERE user_id=? ORDER BY date DESC LIMIT 1", [user_id])
        ap = ap_row[0] if ap_row else 0
        embed = discord.Embed(title="🛒 Guild Shop", description=f"Guild:\n{XP_EMOJI} Your Activity Points: `{ap}`\n\nAvailable Items", color=0x43FF43)
        for item in items:
            embed.add_field(name=f"{item['emoji']} {item['name']} - {item['cost']} {XP_EMOJI}", value=item['desc'], inline=False)
        class ShopView(discord.ui.View):
            @discord.ui.button(label="Tier 1", style=discord.ButtonStyle.green, emoji=TIER_1)
            async def tier1(self, button, interaction2):
                await interaction2.response.send_message(f"You bought Tier 1 for 100.0 {XP_EMOJI}", ephemeral=True)
            @discord.ui.button(label="Tier 2", style=discord.ButtonStyle.green, emoji=TIER_2)
            async def tier2(self, button, interaction2):
                await interaction2.response.send_message(f"You bought Tier 2 for 30.0 {XP_EMOJI}", ephemeral=True)
            @discord.ui.button(label="Tier 3", style=discord.ButtonStyle.green, emoji=TIER_3)
            async def tier3(self, button, interaction2):
                await interaction2.response.send_message(f"You bought Tier 3 for 7.5 {XP_EMOJI}", ephemeral=True)
            @discord.ui.button(label="AFK Pass", style=discord.ButtonStyle.green, emoji=AFK_PASS)
            async def afkpass(self, button, interaction2):
                await interaction2.response.send_message(f"You bought AFK Pass for 3.0 {XP_EMOJI}", ephemeral=True)
        await interaction.response.send_message(embed=embed, view=ShopView())

async def setup(bot):
    await bot.add_cog(Shop(bot))
