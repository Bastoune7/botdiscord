import discord
from discord.ext import commands
from discord import app_commands
from music_player import play_music, stop_music, leave_voice_channel
import asyncio
from datetime import timedelta
from pile_ou_face import pile_ou_face

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionnaire pour garder la trace des tâches de mute actives
mute_tasks = {}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot connecté en tant que {bot.user}')

# (Les événements on_message, pileouface, play, stop, leave sont ici comme avant)

# Commande slash pour mute un utilisateur (texte + vocal)
@bot.tree.command(name="tg", description="Mute un utilisateur temporairement en texte et vocal (Admin seulement).")
@app_commands.describe(member="L'utilisateur à mute", duration="Durée en minutes")
async def tg_command(interaction: discord.Interaction, member: discord.Member, duration: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu veux quoi toi t'es pas admin enculé", ephemeral=True)
        return

    # Récupérer ou créer un rôle muet pour le texte
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await interaction.guild.create_role(name="Muted", reason="Rôle pour mute temporairement les utilisateurs")
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(mute_role, send_messages=False)

    # Appliquer le rôle muet
    await member.add_roles(mute_role, reason="Utilisateur muté temporairement en texte")
    if member.voice and not member.voice.mute:
        await member.edit(mute=True, reason="Utilisateur muté temporairement en vocal")

    await interaction.response.send_message(f"Aller {member.mention}, toi tu fermes ta gueule pendant {duration} minutes, merci bien.")

    # Si un mute est déjà en cours pour cet utilisateur, on l'annule
    if member.id in mute_tasks:
        mute_tasks[member.id].cancel()

    # Créer la tâche de mute et l'ajouter au dictionnaire
    mute_task = asyncio.create_task(unmute_after_delay(member, mute_role, duration, interaction))
    mute_tasks[member.id] = mute_task

async def unmute_after_delay(member, mute_role, duration, interaction):
    try:
        await asyncio.sleep(duration * 60)
        if mute_role in member.roles:
            await member.remove_roles(mute_role, reason="Durée de mute texte écoulée")
        if member.voice and member.voice.mute:
            await member.edit(mute=False, reason="Durée de mute vocal écoulée")
        await interaction.followup.send(f"{member.mention} C'est l'heure de remettre la connexion mais m'embête pas trop parce que je peux couper l'électrécité aussi")
    finally:
        mute_tasks.pop(member.id, None)  # Nettoyer le dictionnaire après le mute

# Commande slash pour unmute un utilisateur
@bot.tree.command(name="untg", description="Enlève le mute d'un utilisateur (Admin seulement).")
@app_commands.describe(member="L'utilisateur à unmute")
async def untg_command(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu veux quoi toi t'es pas admin enculé", ephemeral=True)
        return

    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role, reason="Unmute manuel par un admin")
    if member.voice and member.voice.mute:
        await member.edit(mute=False, reason="Unmute vocal manuel par un admin")

    # Annuler la tâche de mute si elle existe
    if member.id in mute_tasks:
        mute_tasks[member.id].cancel()
        mute_tasks.pop(member.id, None)

    await interaction.response.send_message(f"{member.mention} Je t'ai remis la connexion mais fais gaffe à toi, sinon Thanatos se met en colère")

bot.run('')