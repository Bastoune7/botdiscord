import discord
from discord.ext import commands
from discord import app_commands
from music_player import play_music, stop_music, leave_voice_channel
import asyncio
from datetime import datetime
import signal
import sys
import subprocess
import os
from pile_ou_face import pile_ou_face

# Charger le token depuis config.txt
with open("config.txt", "r") as file:
    TOKEN = file.read().strip()

# Initialiser le bot et les intents
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
        log_file.write(
            f"[{timestamp}] Commande: {command_name}, Utilisateur: {user}, Arguments: {args}, Statut: {status}\n")


# Fonction pour log au démarrage et à l'arrêt
def log_event(event_name, reason=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] Événement: {event_name}, Raison: {reason}\n")


# Dictionnaire pour garder la trace du processus du serveur
server_process = None


# Fonction pour lire les premières lignes du log du serveur
async def monitor_server_logs(interaction):
    await asyncio.sleep(5)  # Temps pour le serveur de démarrer la création de logs
    log_file = os.path.join("logs", "latest.log")

    # Lire les premières lignes jusqu'à "Done"
    async with interaction.channel.typing():
        while server_process.poll() is None:
            try:
                with open(log_file, "r") as f:
                    logs = f.readlines()
                    if any("Done" in line for line in logs):
                        await interaction.followup.send(
                            "Le serveur Minecraft est maintenant en ligne et accessible ! 🟢")
                        break
                    else:
                        await interaction.followup.send("".join(logs[-10:]))  # Envoyer les dernières lignes du log
                        await asyncio.sleep(5)  # Attendre avant de renvoyer les logs

            except Exception as e:
                await interaction.followup.send("Erreur lors de la lecture des logs.")


@bot.tree.command(name="start_minecraft", description="Démarre le serveur Minecraft.")
async def start_minecraft(interaction: discord.Interaction):
    global server_process
    await interaction.response.defer()

    if server_process is not None and server_process.poll() is None:
        await interaction.followup.send("Le serveur est déjà en cours d'exécution !")
        return

    try:
        # Lancer le script batch pour démarrer le serveur
        server_process = subprocess.Popen(
            ["cmd.exe", "/C", "start", "start_server.bat"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True
        )
        await interaction.followup.send("Démarrage du serveur Minecraft...")

        # Lancer le suivi des logs pour indiquer quand le serveur est prêt
        await monitor_server_logs(interaction)
    except Exception as e:
        await interaction.followup.send(f"Erreur lors du démarrage du serveur : {str(e)}")


@bot.tree.command(name="stop_minecraft", description="Arrête le serveur Minecraft.")
async def stop_minecraft(interaction: discord.Interaction):
    global server_process
    await interaction.response.defer()

    if server_process is None or server_process.poll() is not None:
        await interaction.followup.send("Le serveur n'est pas en cours d'exécution.")
        return

    try:
        server_process.terminate()
        server_process.wait()
        server_process = None
        await interaction.followup.send("Le serveur Minecraft a été arrêté.")
    except Exception as e:
        await interaction.followup.send(f"Erreur lors de l'arrêt du serveur : {str(e)}")


@bot.tree.command(name="restart_minecraft", description="Redémarre le serveur Minecraft.")
async def restart_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()
    await stop_minecraft(interaction)
    await asyncio.sleep(5)  # Attendre un moment avant de redémarrer
    await start_minecraft(interaction)


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


# Commande pour muter un membre
@bot.tree.command(name="tg", description="Mute un utilisateur pendant une durée spécifiée.")
@app_commands.describe(user="L'utilisateur à muter", duration="Durée du mute en secondes",
                       message="Message à envoyer à l'utilisateur")
async def tg_command(interaction: discord.Interaction, user: discord.Member, duration: int, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.",
                                                ephemeral=True)
        return

    await interaction.response.send_message(f"{user.mention} a été mute pendant {duration} secondes.")
    mute_tasks[user.id] = asyncio.create_task(mute_user(user, duration, message))


async def mute_user(user: discord.Member, duration: int, message: str):
    # Muter l'utilisateur
    await user.edit(voice_channel=None)  # Muter en le déconnectant temporairement
    await user.send(message)
    await asyncio.sleep(duration)
    await unmute_user(user)


async def unmute_user(user: discord.Member):
    # Rétablir l'utilisateur
    await user.edit(voice_channel=user.voice.channel)


@bot.tree.command(name="untg", description="Démute un utilisateur.")
@app_commands.describe(user="L'utilisateur à démuter")
async def untg_command(interaction: discord.Interaction, user: discord.Member):
    if user.id in mute_tasks:
        mute_tasks[user.id].cancel()
        del mute_tasks[user.id]
        await user.edit(voice_channel=None)  # Assurer qu'il est démute
        await interaction.response.send_message(f"{user.mention} a été démute.")
    else:
        await interaction.response.send_message(f"{user.mention} n'est pas muté.")


# Lancer le bot
bot.run(TOKEN)