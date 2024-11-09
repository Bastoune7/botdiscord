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

# Dictionnaires et file d'attente pour la gestion des tâches et des logs
mute_tasks = {}
log_queue = asyncio.Queue()
server_process = None  # Processus du serveur Minecraft

### Fonctions de journalisation ###

def log_command(command_name, user, args, success=True):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Succès" if success else "Échec"
    with open("log.txt", "a") as log_file:
        log_file.write(
            f"[{timestamp}] Commande: {command_name}, Utilisateur: {user}, Arguments: {args}, Statut: {status}\n")

def log_event(event_name, reason=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("log.txt", "a") as log_file:
        log_file.write(f"[{timestamp}] Événement: {event_name}, Raison: {reason}\n")

### Fonctions de gestion du serveur Minecraft ###

async def start_minecraft_server():
    global server_process
    try:
        server_process = await asyncio.create_subprocess_shell(
            "start powershell -NoExit -Command .\\start_server.bat",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        asyncio.create_task(monitor_logs())
    except Exception as e:
        print(f"Erreur lors du lancement du serveur Minecraft : {str(e)}")

async def monitor_logs():
    global server_process
    if server_process.stdout:
        while True:
            log_line = await server_process.stdout.readline()
            if not log_line:
                break
            log_message = log_line.decode("utf-8").strip()
            await log_queue.put(log_message)
            print(log_message)
            if "Done" in log_message:
                print("Serveur Minecraft démarré avec succès !")
                break
            await asyncio.sleep(0.1)

async def monitor_server_logs(interaction):
    await interaction.followup.send("Surveillance des logs du serveur...")
    while True:
        log_line = await log_queue.get()
        if "Done" in log_line:
            await interaction.followup.send("Le serveur Minecraft est maintenant en ligne et accessible ! 🟢")
            break
        elif "Error" in log_line or "Exception" in log_line:
            await interaction.followup.send(f"Erreur détectée dans le log : {log_line}")
            break


async def stop_minecraft(interaction):
    await interaction.response.defer()

    try:
        # Vérifier si le serveur Minecraft est en ligne
        server = MinecraftServer("localhost", 10586)  # Remplacez par l'IP et le port de votre serveur
        status = server.status()  # Si le serveur est en ligne, cette ligne renvoie un statut

        # Si le serveur est en ligne, on tente de l'arrêter
        if status:
            global server_process
            if server_process is not None and server_process.stdin:
                server_process.stdin.write("stop\n".encode())
                await server_process.stdin.drain()
                await interaction.followup.send("Le serveur Minecraft a été arrêté.")
                await server_process.wait()
                server_process = None
            else:
                # Si `server_process` n'est pas défini, on suppose que le serveur est lancé indépendamment
                await interaction.followup.send("🛑 Oups... Le serveur minecraft a été lancé avant que je ne sois moi même lancé... Ce qui signifie que je ne suis pas en mesure de l'arrêter puisque ça n'est pas moi qui ai lancé le serveur ! Envoie un message à Bastien pour qu'il règle ça ou connecte toi en RCON au serveur pour accéder à ces fonctionnalités sans m'utiliser 😉")
                # Envoyez la commande "stop" via une requête réseau ou d'autres moyens configurés pour le serveur
                # Par exemple, en utilisant RCON si configuré sur le serveur Minecraft
                # TODO: Ajoutez ici une requête réseau ou via un script pour stopper le serveur externe

        else:
            await interaction.followup.send("Le serveur Minecraft n'est pas en cours d'exécution.")

    except Exception as e:
        await interaction.followup.send(f"Erreur lors de l'arrêt du serveur : {str(e)}")

### Commandes de gestion du serveur Minecraft ###

@bot.tree.command(name="start_minecraft", description="Démarre le serveur Minecraft.")
async def start_minecraft(interaction: discord.Interaction):
    global server_process
    await interaction.response.defer()

    # Check if server was not already started (ouais je parle en anglais maintenant)
    if server_process is not None and server_process.returncode is None:
        await interaction.followup.send("Le serveur est déjà en cours d'exécution !")
        return

    #Start the server and check the log (asynchrone)
    try:
        await start_minecraft_server()
        await interaction.followup.send("Démarrage du serveur Minecraft...")
        await asyncio.create_task(monitor_server_logs(interaction))
    except Exception as e:
        await interaction.followup.send(f"Erreur lors du démarrage du serveur : {str(e)}")

@bot.tree.command(name="stop_minecraft", description="Arrête le serveur Minecraft.")
async def stop_minecraft_command(interaction):
    await stop_minecraft(interaction)

@bot.tree.command(name="restart_minecraft", description="Redémarre le serveur Minecraft.")
async def restart_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()
    await stop_minecraft(interaction)
    await asyncio.sleep(5)
    await start_minecraft(interaction)

@bot.tree.command(name="check_minecraft", description="Vérifie si le serveur Minecraft est en ligne.")
async def check_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        server = MinecraftServer("localhost", 10586)
        status = server.status()
        await interaction.followup.send("Le serveur Minecraft est en cours d'exécution et est en ligne ! 🟢")
    except Exception as e:
        await interaction.followup.send(f"Le serveur ne semble pas en ligne : {str(e)}")

### Commandes et événements de bot ###

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot connecté en tant que {bot.user}')
    log_event("Démarrage", "Bot connecté et prêt")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "ping" in message.content.lower():
        await message.channel.send("Pong! 🏓")
    elif "pong" in message.content.lower():
        await message.channel.send("Bon tg")
    elif "joris" in message.content.lower():
        await message.reply("Qu'il repose en paix 🪦😢")
    elif any(phrase in message.content.lower() for phrase in ["ta gueule", "tagueule", "tg"]):
        await message.reply("Toi ferme la 😡")

    await bot.process_commands(message)

### Commandes diverses ###

@bot.tree.command(name="pileouface", description="Lance une pièce pour pile ou face")
async def pileouface_command(interaction: discord.Interaction):
    try:
        await pile_ou_face(interaction)
        log_command("pileouface", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("pileouface", interaction.user, [], success=False)

@bot.tree.command(name="play", description="Joue de la musique depuis une URL YouTube.")
async def play_command(interaction: discord.Interaction, url: str):
    try:
        await play_music(interaction, url)
        log_command("play", interaction.user, [url], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("play", interaction.user, [url], success=False)

@bot.tree.command(name="stop", description="Arrête la musique en cours.")
async def stop_command(interaction: discord.Interaction):
    try:
        await stop_music(interaction)
        log_command("stop", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("stop", interaction.user, [], success=False)

@bot.tree.command(name="leave", description="Fait quitter le canal vocal au bot.")
async def leave_command(interaction: discord.Interaction):
    try:
        await leave_voice_channel(interaction)
        log_command("leave", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("leave", interaction.user, [], success=False)

### Commandes de gestion des utilisateurs ###

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
    await user.edit(voice_channel=None)
    await user.send(message)
    await asyncio.sleep(duration)
    await unmute_user(user)

async def unmute_user(user: discord.Member):
    await user.edit(voice_channel=user.voice.channel)

@bot.tree.command(name="untg", description="Démute un utilisateur.")
@app_commands.describe(user="L'utilisateur à démuter")
async def untg_command(interaction: discord.Interaction, user: discord.Member):
    if user.id in mute_tasks:
        mute_tasks[user.id].cancel()
        del mute_tasks[user.id]
        await user.edit(voice_channel=None)
        await interaction.response.send_message(f"{user.mention} a été démute.")
    else:
        await interaction.response.send_message(f"{user.mention} n'est pas muté.")

### Gestion des signaux et exceptions ###

def on_shutdown(reason=""):
    log_event("Arrêt", reason)
    print("Bot arrêté.")
    sys.exit(0)

signal.signal(signal.SIGINT, lambda sig, frame: on_shutdown("Arrêt manuel (Ctrl+C)"))
signal.signal(signal.SIGTERM, lambda sig, frame: on_shutdown("Arrêt forcé ou redémarrage"))

def handle_exception(loop, context):
    reason = context.get("exception", context["message"])
    log_event("Arrêt", f"Crash: {reason}")
    loop.default_exception_handler(context)

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)

# Lancer le bot
bot.run(TOKEN)