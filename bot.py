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

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot connecté en tant que {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "ping" in message.content.lower():
        await message.channel.send("Pong! 🏓")

    if "thanatos" in message.content.lower():
        await message.channel.send("Oui ? 😎")

    if "keo" in message.content.lower():
        await message.channel.send("L'aigri est en train d'écrire...")

    if "pong" in message.content.lower():
        await message.channel.send("Bon tg")

    if "joris" in message.content.lower():
        await message.reply("Qu'il repose en paix 🪦😢")

    if any(phrase in message.content.lower() for phrase in ["ta gueule", "tagueule", "tg"]):
        await message.reply("Toi ferme la 😡")

    await bot.process_commands(message)

# Commande pile ou face en slash
@bot.tree.command(name="pileouface", description="Lance une pièce pour pile ou face")
async def pileouface_command(interaction: discord.Interaction):
    await pile_ou_face(interaction)

# Commande slash pour jouer de la musique
@bot.tree.command(name="play", description="Joue de la musique depuis une URL YouTube.")
async def play_command(interaction: discord.Interaction, url: str):
    await play_music(interaction, url)

# Commande slash pour arrêter la musique
@bot.tree.command(name="stop", description="Arrête la musique en cours.")
async def stop_command(interaction: discord.Interaction):
    await stop_music(interaction)

# Commande slash pour quitter le canal vocal
@bot.tree.command(name="leave", description="Fait quitter le canal vocal au bot.")
async def leave_command(interaction: discord.Interaction):
    await leave_voice_channel(interaction)


# Commande slash pour mute un utilisateur (texte + vocal)
@bot.tree.command(name="tg", description="Mute un utilisateur temporairement en texte et vocal (Admin seulement).")
@app_commands.describe(member="L'utilisateur à mute", duration="Durée en minutes")
async def tg_command(interaction: discord.Interaction, member: discord.Member, duration: int):
    # Vérifiez si l'utilisateur exécutant la commande est admin
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu veux quoi toi t'es pas admin enculé", ephemeral=True)
        return

    # Récupérer ou créer un rôle muet pour le texte
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await interaction.guild.create_role(name="Muted",
                                                        reason="Rôle pour mute temporairement les utilisateurs")

        # Supprimer la permission d'envoyer des messages sur tous les salons texte
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(mute_role, send_messages=False)

    # Appliquer le rôle muet à l'utilisateur pour le texte
    await member.add_roles(mute_role, reason="Utilisateur muté temporairement en texte")

    # Muter l'utilisateur en vocal s'il est connecté à un canal vocal
    if member.voice and not member.voice.mute:
        await member.edit(mute=True, reason="Utilisateur muté temporairement en vocal")

    # Envoyer un message de confirmation
    await interaction.response.send_message(
        f"Aller {member.mention}, toi tu fermes ta gueule pendant {duration} minutes, merci bien.")

    # Définir un délai pour enlever le rôle muet et rétablir le vocal après la durée spécifiée
    await asyncio.sleep(duration * 60)
    await member.remove_roles(mute_role, reason="Durée de mute texte écoulée")

    # Démuter l'utilisateur en vocal après le délai
    if member.voice and member.voice.mute:
        await member.edit(mute=False, reason="Durée de mute vocal écoulée")

    # Message pour informer que le mute est terminé
    await interaction.followup.send(
        f"{member.mention} bon tu reparles mais fais pas trop de bruit sinon je te recoupe la connexion.")


# Commande slash pour unmute un utilisateur
@bot.tree.command(name="untg", description="Enlève le mute d'un utilisateur (Admin seulement).")
@app_commands.describe(member="L'utilisateur à unmute")
async def untg_command(interaction: discord.Interaction, member: discord.Member):
    # Vérifiez si l'utilisateur exécutant la commande est admin
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu veux quoi toi t'es pas admin enculé", ephemeral=True)
        return

    # Récupérer le rôle "Muted"
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role, reason="Unmute manuel par un admin")

    # Si l'utilisateur est mute en vocal, on enlève le mute
    if member.voice and member.voice.mute:
        await member.edit(mute=False, reason="Unmute vocal manuel par un admin")

    # Confirmer le unmute à l'admin
    await interaction.response.send_message(f"{member.mention} a été démute. Bienvenue à nouveau dans le monde des vivants.")

bot.run('')