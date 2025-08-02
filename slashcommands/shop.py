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
            cursor = await db.execute("SELECT activity_points FROM gxp WHERE user_id=? ORDER BY date DESC LIMIT 1", [user_id])
            ap_row = await cursor.fetchone()
            ap = ap_row[0] if ap_row else 0

            embed = discord.Embed(title="🛒 Guild Shop", description=f"Guild:\n{XP_EMOJI} Your Activity Points: `{ap}`\n\nAvailable Items", color=0x43FF43)
            for item in items:
                embed.add_field(name=f"{item['emoji']} {item['name']} - {item['cost']} {XP_EMOJI}", value=item['desc'], inline=False)

            class ShopView(discord.ui.View):
                async def handle_purchase(self, interaction2, item_idx):
                    item = items[item_idx]
                    # Re-fetch AP in case it changed
                    cursor2 = await db.execute("SELECT activity_points FROM gxp WHERE user_id=? ORDER BY date DESC LIMIT 1", [user_id])
                    ap_row2 = await cursor2.fetchone()
                    ap2 = ap_row2[0] if ap_row2 else 0
                    if ap2 < item['cost']:
                        await interaction2.response.send_message(f"❌ Not enough Activity Points for {item['name']}!", ephemeral=True)
                        return
                    # Deduct AP
                    await db.execute("UPDATE gxp SET activity_points = activity_points - ? WHERE user_id=?", (item['cost'], user_id))
                    # Add item to shop table
                    await db.execute("INSERT INTO shop (user_id, item, amount) VALUES (?, ?, 1) ON CONFLICT(user_id, item) DO UPDATE SET amount = amount + 1", (user_id, item['name']))
                    await db.commit()
                    await interaction2.response.send_message(f"✅ You bought {item['name']} for {item['cost']} {XP_EMOJI}", ephemeral=True)

                @discord.ui.button(label="Tier 1", style=discord.ButtonStyle.green, emoji=TIER_1)
                async def tier1(self, button, interaction2):
                    await self.handle_purchase(interaction2, 0)
                @discord.ui.button(label="Tier 2", style=discord.ButtonStyle.green, emoji=TIER_2)
                async def tier2(self, button, interaction2):
                    await self.handle_purchase(interaction2, 1)
                @discord.ui.button(label="Tier 3", style=discord.ButtonStyle.green, emoji=TIER_3)
                async def tier3(self, button, interaction2):
                    await self.handle_purchase(interaction2, 2)
                @discord.ui.button(label="AFK Pass", style=discord.ButtonStyle.green, emoji=AFK_PASS)
                async def afkpass(self, button, interaction2):
                    await self.handle_purchase(interaction2, 3)

            await interaction.response.send_message(embed=embed, view=ShopView())
    @app_commands.command(name="inventory", description="Show your purchased items from the Guild Shop")
    async def inventory(self, interaction: discord.Interaction):
        import aiosqlite
        XP_EMOJI = "<:xp:1396916494746779829>"
        TIER_1 = "<:tier_1:1396932891685949570>"
        TIER_2 = "<:tier_2:1396932952763400262>"
        TIER_3 = "<:tier_3:1396932981876068432>"
        AFK_PASS = "<:afk_pass:1396930235030831316>"
        item_emojis = {
            "Tier 1 Rank": TIER_1,
            "Tier 2 Rank": TIER_2,
            "Tier 3 Rank": TIER_3,
            "AFK Pass": AFK_PASS
        }
        user_id = str(interaction.user.id)
        async with aiosqlite.connect("db/gxp_data.db") as db:
            cursor = await db.execute("SELECT item, amount FROM shop WHERE user_id=?", [user_id])
            rows = await cursor.fetchall()
        if not rows:
            embed = discord.Embed(title="🎒 Inventory", description="You have no items from the Guild Shop yet.", color=0x4A90E2)
        else:
            embed = discord.Embed(title="🎒 Inventory", description="Your purchased items:", color=0x4A90E2)
            for item, amount in rows:
                emoji = item_emojis.get(item, "❓")
                embed.add_field(name=f"{emoji} {item}", value=f"Quantity: `{amount}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Shop(bot))
