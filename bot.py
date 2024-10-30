import discord
from discord.ext import commands
from discord import app_commands
from music_player import play_music, stop_music, leave_voice_channel
import asyncio
from datetime import datetime, timedelta
import signal
import sys
from pile_ou_face import pile_ou_face

# Charger le token depuis config.txt
with open("config.txt", "r") as file:
    TOKEN = file.read().strip()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionnaire pour garder la trace des tâches de mute actives
mute_tasks = {}

# Fonction pour enregistrer les logs des commandes
def log_command(command_name, user, args, success=True):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Succès" if success else "Échec"
    with open("log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] Commande: {command_name}, Utilisateur: {user}, Arguments: {args}, Statut: {status}\n")

# Fonction pour log au démarrage et à l'arrêt
def log_event(event_name, reason=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] Événement: {event_name}, Raison: {reason}\n")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot connecté en tant que {bot.user}')
    log_event("Démarrage", "Bot connecté et prêt")

# Fonction pour log l'arrêt du bot
def on_shutdown(reason=""):
    log_event("Arrêt", reason)
    print("Bot arrêté.")
    sys.exit(0)

# Attacher les signaux pour capturer les arrêts manuels et les arrêts forcés
signal.signal(signal.SIGINT, lambda sig, frame: on_shutdown("Arrêt manuel (Ctrl+C)"))
signal.signal(signal.SIGTERM, lambda sig, frame: on_shutdown("Arrêt forcé ou redémarrage"))

# Capture des exceptions non gérées pour log en cas de crash
def handle_exception(loop, context):
    reason = context.get("exception", context["message"])
    log_event("Arrêt", f"Crash: {reason}")
    loop.default_exception_handler(context)

# Appliquer le gestionnaire d'exceptions à la boucle d'événements
loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)

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
    try:
        await pile_ou_face(interaction)
        log_command("pileouface", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("pileouface", interaction.user, [], success=False)

# Commande slash pour jouer de la musique
@bot.tree.command(name="play", description="Joue de la musique depuis une URL YouTube.")
async def play_command(interaction: discord.Interaction, url: str):
    try:
        await play_music(interaction, url)
        log_command("play", interaction.user, [url], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("play", interaction.user, [url], success=False)

# Commande slash pour arrêter la musique
@bot.tree.command(name="stop", description="Arrête la musique en cours.")
async def stop_command(interaction: discord.Interaction):
    try:
        await stop_music(interaction)
        log_command("stop", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("stop", interaction.user, [], success=False)

# Commande slash pour quitter le canal vocal
@bot.tree.command(name="leave", description="Fait quitter le canal vocal au bot.")
async def leave_command(interaction: discord.Interaction):
    try:
        await leave_voice_channel(interaction)
        log_command("leave", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("leave", interaction.user, [], success=False)

# Commande slash pour mute un utilisateur (texte + vocal)
@bot.tree.command(name="tg", description="Mute un utilisateur temporairement en texte et vocal (Admin seulement).")
@app_commands.describe(member="L'utilisateur à mute", duration="Durée en minutes")
async def tg_command(interaction: discord.Interaction, member: discord.Member, duration: int):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Tu veux quoi toi t'es pas admin enculé", ephemeral=True)
            log_command("tg", interaction.user, [member.name, duration], success=False)
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
        log_command("tg", interaction.user, [member.name, duration], success=True)

    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("tg", interaction.user, [member.name, duration], success=False)

# Commande slash pour unmute un utilisateur
@bot.tree.command(name="untg", description="Enlève le mute d'un utilisateur (Admin seulement).")
@app_commands.describe(member="L'utilisateur à unmute")
async def untg_command(interaction: discord.Interaction, member: discord.Member):
    try:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Tu veux quoi toi t'es pas admin enculé", ephemeral=True)
            log_command("untg", interaction.user, [member.name], success=False)
            return

        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if mute_role in member.roles:
            await member.remove_roles(mute_role, reason="Unmute manuel par un admin")
        if member.voice and member.voice.mute:
            await member.edit(mute=False, reason="Unmute vocal manuel par un admin")

        if member.id in mute_tasks:
            mute_tasks[member.id].cancel()
            mute_tasks.pop(member.id, None)

        await interaction.response.send_message(f"{member.mention} Je t'ai remis la connexion mais fais gaffe à toi, sinon Thanatos se met en colère")
        log_command("untg", interaction.user, [member.name], success=True)

    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("untg", interaction.user, [member.name], success=False)

bot.run(TOKEN)