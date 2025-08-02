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

    @app_commands.command(name="verify", description="Link your Discord to your Hypixel IGN if your Discord is set in Hypixel social media.")
    @app_commands.describe(ign="Your Minecraft IGN")
    async def verify(self, interaction: discord.Interaction, ign: str):
        user_id = str(interaction.user.id)
        await interaction.response.defer(ephemeral=True)
        # Fetch Hypixel player data
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.hypixel.net/player?key={HYPIXEL_API_KEY}&name={ign}") as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"❌ Could not fetch data for IGN `{ign}` from Hypixel. Status: {resp.status}", ephemeral=True)
                    return
                data = await resp.json()
                player = data.get("player")
                if not player:
                    await interaction.followup.send(f"❌ Player `{ign}` not found on Hypixel.", ephemeral=True)
                    return
                # Check for Discord in social media
                social = player.get("socialMedia", {}).get("links", {})
                hypixel_discord = social.get("DISCORD")
                if not hypixel_discord:
                    await interaction.followup.send(f"❌ No Discord account linked in Hypixel social media for `{ign}`.", ephemeral=True)
                    return
                # Compare Discord tag (case-insensitive, strip whitespace)
                user_tag = str(interaction.user)
                if hypixel_discord.strip().lower() != user_tag.strip().lower():
                    await interaction.followup.send(f"❌ The Discord linked on Hypixel (`{hypixel_discord}`) does not match your Discord account (`{user_tag}`).", ephemeral=True)
                    return
                # Save mapping in user_map
                uuid = player.get("uuid")
                async with aiosqlite.connect("db/gxp_data.db") as db:
                    await db.execute("INSERT OR REPLACE INTO user_map (discord_id, uuid, ign) VALUES (?, ?, ?)", (user_id, uuid, ign))
                    await db.commit()
                # Cambiar apodo y asignar rol según si está en la guild UPDATE_GUILD
                try:
                    if interaction.guild:
                        member = interaction.guild.get_member(interaction.user.id)
                        if member:
                            await member.edit(nick=ign, reason="Verified with /verify")
                            # Verificar si está en la guild de Hypixel
                            update_guild = os.getenv("UPDATE_GUILD")
                            in_guild = False
                            # Buscar en la lista de guilds del jugador
                            guilds = player.get("guilds")
                            # Si la API de Hypixel no da guilds, usar endpoint de guild
                            if not guilds:
                                # Buscar guild por UUID
                                async with aiohttp.ClientSession() as session2:
                                    async with session2.get(f"https://api.hypixel.net/guild?key={HYPIXEL_API_KEY}&player={uuid}") as resp2:
                                        if resp2.status == 200:
                                            data2 = await resp2.json()
                                            guild = data2.get("guild")
                                            if guild and guild.get("name") == update_guild:
                                                in_guild = True
                            else:
                                for g in guilds:
                                    if g.get("name") == update_guild:
                                        in_guild = True
                                        break
                            # Asignar rol según pertenencia
                            role_id_in = 1401227876497494066
                            role_id_out = 1401227867760890016
                            role_to_add = role_id_in if in_guild else role_id_out
                            # Quitar ambos roles antes de asignar
                            roles_to_remove = [role_id_in, role_id_out]
                            roles = [interaction.guild.get_role(rid) for rid in roles_to_remove]
                            await member.remove_roles(*[r for r in roles if r in member.roles])
                            role = interaction.guild.get_role(role_to_add)
                            if role:
                                await member.add_roles(role, reason="Verified with /verify")
                except Exception as e:
                    await interaction.followup.send(f"⚠️ Linked, but could not change nickname or assign role: {e}", ephemeral=True)
                await interaction.followup.send(f"✅ Successfully linked your Discord to IGN `{ign}`! Your nickname and role have been updated. You can now use `/member` without specifying your IGN.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Verify(bot))
