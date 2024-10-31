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
from mcstatus import MinecraftServer
from queue import Queue

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
log_queue = Queue()

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

# Fonction pour démarrer le serveur Minecraft dans un sous-processus
async def start_minecraft_server():
    global server_process
    try:
        # Utiliser asyncio.create_subprocess_shell pour le lancement asynchrone
        server_process = await asyncio.create_subprocess_shell(
            "start powershell -NoExit -Command .\\start_server.bat",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        asyncio.create_task(monitor_logs())  # Surveiller les logs de façon asynchrone
    except Exception as e:
        print(f"Erreur lors du lancement du serveur Minecraft : {str(e)}")

# Fonction asynchrone pour surveiller les logs sans bloquer le bot
async def monitor_logs():
    if server_process.stdout:
        while True:
            line = await server_process.stdout.readline()
            if not line:
                break
            log_queue.put(line.decode().strip())  # Convertir en texte et ajouter à la file d'attente
            print(line.decode().strip())
            await asyncio.sleep(0.1)  # Pause courte pour éviter une surcharge CPU

async def monitor_server_logs(interaction):
    await interaction.followup.send("Surveillance des logs du serveur...")
    while True:
        log_line = log_queue.get()  # Récupère la ligne de log depuis la file d'attente
        if "Done" in log_line:
            await interaction.followup.send("Le serveur Minecraft est maintenant en ligne et accessible ! 🟢")
            break
        elif "Error" in log_line or "Exception" in log_line:
            await interaction.followup.send(f"Erreur détectée dans le log : {log_line}")
            break
        await asyncio.sleep(1)

@bot.tree.command(name="start_minecraft", description="Démarre le serveur Minecraft.")
async def start_minecraft(interaction: discord.Interaction):
    global server_process
    await interaction.response.defer()

    if server_process is not None and server_process.poll() is None:
        await interaction.followup.send("Le serveur est déjà en cours d'exécution !")
        return

    try:
        start_minecraft_server()
        await interaction.followup.send("Démarrage du serveur Minecraft...")

        # Surveiller les logs et confirmer le démarrage
        asyncio.create_task(monitor_server_logs(interaction))
    except Exception as e:
        await interaction.followup.send(f"Erreur lors du démarrage du serveur : {str(e)}")


# Fonction pour arrêter le serveur Minecraft
@bot.tree.command(name="stop_minecraft", description="Arrête le serveur Minecraft.")
async def stop_minecraft(interaction):
    global server_process
    await interaction.response.defer()

    if server_process is not None and server_process.poll() is None:
        try:
            # Envoyer la commande "stop" au serveur
            server_process.stdin.write("stop\n".encode())
            await server_process.stdin.drain()
            await interaction.followup.send("Le serveur Minecraft a été arrêté.")
            await server_process.wait()
            server_process = None  # Réinitialiser le processus
        except Exception as e:
            await interaction.followup.send(f"Erreur lors de l'arrêt du serveur : {str(e)}")
    else:
        await interaction.followup.send("Le serveur Minecraft n'est pas en cours d'exécution.")


@bot.tree.command(name="restart_minecraft", description="Redémarre le serveur Minecraft.")
async def restart_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()
    await stop_minecraft(interaction)
    await asyncio.sleep(5)  # Attendre un moment avant de redémarrer
    await start_minecraft(interaction)

@bot.tree.command(name="check_minecraft", description="Vérifie si le serveur Minecraft est en ligne.")
async def check_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()

    if server_process is None or server_process.poll() is not None:
        await interaction.followup.send("Le serveur Minecraft n'est pas en cours d'exécution.")
        return

    # Vérification de la connexion au serveur
    try:
        server = MinecraftServer("localhost", 10586)  # Assurez-vous d'utiliser l'IP et le port corrects
        status = server.status()  # Cette méthode va lancer une requête au serveur
        await interaction.followup.send("Le serveur Minecraft est en cours d'exécution et est en ligne ! 🟢")
    except Exception as e:
        await interaction.followup.send(f"Le serveur ne semble pas en ligne : {str(e)}")


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