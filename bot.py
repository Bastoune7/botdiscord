import discord
from discord.ext import commands, tasks
from discord import app_commands
from music_player import play_music, stop_music, leave_voice_channel
import asyncio
from datetime import datetime, timedelta
import signal
import sys
import subprocess
import os
import shutil
import zipfile
from pile_ou_face import pile_ou_face
from mcstatus import MinecraftServer
from queue import Queue
import aiofiles

# Charger le token depuis config.txt
with open("config.txt", "r") as file:
    TOKEN = file.read().strip()

# Initialiser le bot et les intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

## VARIABLE GÉNÉRALES
BACKUP_PATH = "C:/Backup/Kulmatiski's server Backup"
SERVER_PATH = "../../minecraft server java"
bastien_mention = "<@337903281999314944>"
mute_tasks = {}
log_queue = asyncio.Queue()
server_process = None  # Processus du serveur Minecraft
LOG_FILE = "server.log" #Fichier de log du serveur minecraft
BOT_LOG_FILE = "log.log" #Fichier de log des événements et commandes du bot
backup_interval = timedelta(hours=24) #Intervalle par défaut des sauvegardes automatiques
last_backup_time = None


### Fonctions de journalisation ###

def log_command(command_name, user, args, success=True):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Succès" if success else "Échec"
    with open(BOT_LOG_FILE, "a") as log_file:
        log_file.write(
            f"[{timestamp}] Commande: {command_name}, Utilisateur: {user}, Arguments: {args}, Statut: {status}\n")

def log_event(event_name, reason=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(BOT_LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] Événement: {event_name}, Raison: {reason}\n")

# Fonction utilitaire pour écrire simplement dans le log
def write_simple_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(BOT_LOG_FILE, "a") as log:
        log.write(f"[{timestamp}] {message}\n")

### Fonctions de gestion du serveur Minecraft ###

async def start_minecraft_server():
    global server_process
    try:
        # Démarrer le serveur Minecraft
        with open(LOG_FILE, "w") as log_file:
            server_process = subprocess.Popen(
                ["java", "-Xmx1024M", "-Xms1024M", "-jar", "server.jar", "nogui"],
                stdout=log_file,
                stderr=log_file,
                shell=True
            )
        return True
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur : {e}")
        return False

async def stop_minecraft_server():
    """Arrête le serveur Minercaft en envoyant la commande 'stop'"""
    global server_process
    try:
        if server_process and server_process.poll() is None:
            server_process.terminate()
            server_process.wait()
            server_process = None
            return True
        return False
    except Exception as e:
        print(f"Erreur lors de l'arrêt du serveur : {e}")
        return False

async def check_minecraft_status():
    """Vérifie si le serveur Minecraft est en ligne."""
    try:
        server = MinecraftServer("localhost", 10586)
        status = server.status()
        return True, status
    except Exception as e:
        return False, str(e)

async def monitor_logs():
    """Surveille les logs de server.log pour l'état"""
    try:
        async with aiofiles.open("server.log", mode="r") as log_file:
            await log_file.seek(0, os.SEEK_END) #Aller à la fin du fichier
            while True:
                log_line = await log_file.readline()
                if not log_line:
                    await asyncio.sleep(0.1) #Attendre si pas de nouvelles lignes
                    continue

                log_message = log_line.strip()
                print(log_message) #Afficher dans la console
                await log_queue.put(log_message) #Ajouter à la file d'attente
    except Exception as e:
        print(f"Erreur lors de la surveillance des logs : {e}")

async def monitor_server_logs(interaction):
    """Envoie les notifications Discord en fonction des logs."""
    await interaction.followup.send("Surveillance des logs du serveur...")
    try:
        while True:
            log_line = await log_queue.get()
            if "Done" in log_line:
                await interaction.followup.send("Le serveur Minecraft est maintenant en ligne et accessible ! 🟢")
                break
            elif "Error" in log_line or "Exception" in log_line:
                await interaction.followup.send(f"🔴 Erreur détectée dans le log : {log_line}")
                break
    except Exception as e:
        await interaction.followup.send(f"Erreur lors de la surveillance des logs : {e}")

def get_last_successful_backup_time():
    if not os.path.exists(BOT_LOG_FILE):
        return None

    with open(BOT_LOG_FILE, "r") as log:
        lines = log.readlines()

    for line in reversed(lines):
        if "Backup completed successfully" in line:
            timestamp = line.split("]")[0][1:] #Extraction de l'horadatage
            return datetime.strftime(timestamp, "%Y-%m-%d %H:%M:%S")
    return None

### Commandes de gestion du serveur Minecraft ###

@bot.tree.command(name="start_minecraft", description="Démarre le serveur Minecraft.")
async def start_minecraft(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Vous n'avez pas les permissions pour exécuter cette commande.")
        return

    await interaction.response.defer()
    success = await start_minecraft_server()
    if success:
        await interaction.followup.send("✅ Serveur Minecraft démarré avec succès.")
        log_command("start_minecraft", interaction.user, [], success=True)

    else:
        await interaction.followup.send("❌ Échec du démarrage du serveur Minecraft.")
        log_command("start_minecraft", interaction.user, [], success=False)

@bot.tree.command(name="stop_minecraft", description="Arrête le serveur minecraft.")
async def stop_minecraft(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Vous n'avez pas les permissions pour exécuter cette commande.")
        return
    await interaction.response.defer()
    success = await stop_minecraft_server()
    if success:
        await interaction.followup.send("✅ Serveur Minecraft arrêté avec succès.")
        log_command("stop_minecraft", interaction.user, [], success=True)
    else:
        await interaction.followup.send("❌ Échec de l'arrêt du serveur Minecraft.")
        log_command("stop_minecraft", interaction.user, [], success=False)

@bot.tree.command(name="restart_minecraft", description="Redémarre le serveur Minecraft.")
async def restart_minecraft(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Vous n'avez pas les permissions pour exécuter cette commande.")
        return
    await interaction.response.defer()
    success_stop = await stop_minecraft_server()
    await asyncio.sleep(5)
    success_start = await start_minecraft_server()

    if success_stop and success_start:
        await interaction.followup.send("✅ Serveur Minecraft redémarré avec succès.")
        log_command("restart_minecraft", interaction.user, [], success=True)
    else:
        await interaction.followup.send("❌ Échec du redémarrage du serveur Minecraft.")
        log_command("restart_minecraft", interaction.user, [], success=False)

    @bot.tree.command(name="check_minecraft", description="Vérifie si le serveur Minecraft est en ligne.")
    async def check_minecraft(interaction: discord.Interaction):
        await interaction.response.defer()
        is_online, status = await check_minecraft_status()
        if is_online:
            await interaction.followup.send("🟢 Le serveur Minecraft est en ligne !")
        else:
            await interaction.followup.send(f"🔴 Le serveur Minecraft est hors ligne. Raison : {status}")
        log_command("check_minecraft", interaction.user, [], success=is_online)

        #Commande /backup_now
        @bot.command()
        async def backup_now(ctx):
            global last_backup_time

            if not ctx.author.guild_permissions.administrator:
                await ctx.send(f"Je suis désolé, mais tu n'as pas la permission de faire une backup. Si besoin tu peux tout de même demander à {bastien_mention}")
                return

            now = datetime.now()
            if last_backup_time and now - last_backup_time < timedelta(minutes=5):
                await ctx.send("Je suis désolé, mais une sauvegarde a été faite il y a moins de 5min. Pour éviter le blinder le serveur de backup je ne vais donc pas l'exécuter. Toutefois si c'est un bug, il faut le signaler.")

            backup_name = f"mc-{now.strftime('%Y-%m-%d').zip}"
            backup_path = os.path.join(BACKUP_PATH, backup_name)

            try:
                write_simple_log("Starting backup process...")

                # Création du dossier de sauvegarde si nécessaire
                os.makedirs(BACKUP_PATH, exist_ok=True)

                #Création de l'archive zip
                with zipfile.ZipFile(backup_path, 'w') as backup_zip:
                    for foldername, subfolders, filenames in os.walk(SERVER_PATH):
                        for filename in filenames:
                            file_path = os.path.join(foldername, filename)
                            arcname = os.path.relpath(file_path, SERVER_PATH)
                            backup_zip.write(file_path, arcname)

                write_simple_log("Backup completed successfully !")
                last_backup_time = now
                await ctx.send("Sauvegarde du serveur minecraft effectuée avec succès !")

            except Exception as e:
                write_simple_log(f"Backup failed: {e}")
                await ctx.send(f"Échec de la sauvegarde du serveur minecraft. Euh, {bastien_mention} faudrait checker stp 🙃")
@bot.command()
async def backup_schedule(ctx, interval_hours: int):
    if str(ctx.author.mention) != bastien_mention:
        await ctx.send(f"🫤 Je suis désolé, seul {bastien_mention} peut modifier la planification des sauvegardes du serveur minecraft...")

    global BACKUP_INTERVAL
    BACKUP_INTERVAL = timedelta(hours=interval_hours)
    auto_backup.change_interval(seconds=BACKUP_INTERVAL.total_seconds())
    await ctx.send(f"Planification des sauvegardes modifiée: toutes les {interval_hours} heures.")

@bot.command()
async def backup_status(ctx):
    global last_backup_time
    last_backup_time = get_last_successful_backup_time()
    status = "non définie" if not last_backup_time else last_backup_time.strftime("%Y-%m-%d %H:%M:%S")
    await ctx.send(f"Dernière sauvegarde réussie : {status}\nIntervalle des sauvegardes : {BACKUP_INTERVAL}.")
@bot.command()
async def disable_backup(ctx):
    if str(ctx.author.mention) != bastien_mention:
        await ctx.send(f"🫤 Je suis désolé, seul {bastien_mention} peut désactiver les sauvegardes automatiques.")
        return

    auto_backup.stop()
    await ctx.send("Les sauvegardes automatiques ont été désactivées.")

# Tâche automatique pour les sauvegardes
@tasks.loop(hours=24)
async def auto_backup():
    global last_backup_time

    now = datetime.now()
    if last_backup_time and now - last_backup_time < BACKUP_INTERVAL:
        return

    backup_name = f"mc-auto-{now.strftime('%Y-%m-%d')}.zip"
    backup_path = os.path.join(BACKUP_PATH, backup_name)

    try:
        write_simple_log("Starting automatic backup process.")

        # Création du dossier de sauvegarde si nécessaire
        os.makedirs(BACKUP_PATH, exist_ok=True)

        # Création de l'archive ZIP
        with zipfile.ZipFile(backup_path, 'w') as backup_zip:
            for foldername, subfolders, filenames in os.walk(SERVER_PATH):
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    arcname = os.path.relpath(file_path, SERVER_PATH)
                    backup_zip.write(file_path, arcname)

        write_simple_log("Automatic Backup completed successfully.")
        last_backup_time = now

    except Exception as e:
        write_simple_log(f"Automatic Backup failed: {e}")



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
        await message.reply("Oh mon pepscen d'amour 🥰")
    elif any(phrase in message.content.lower() for phrase in ["ta gueule", "tagueule", "tg"]):
        await message.reply("Toi ferme la 😡")

    await bot.process_commands(message)

### Commandes musiques et autres ###

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
        interaction.response.send_message("Ok j'arrive... 🎵", ephemeral=True)
        log_command("play", interaction.user, [url], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("play", interaction.user, [url], success=False)

@bot.tree.command(name="stop", description="Arrête la musique en cours.")
async def stop_command(interaction: discord.Interaction):
    try:
        await stop_music(interaction)
        interaction.response.send_message("Ok j'arrête ! 🙃", ephemeral=True)
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
    # Vérifie si l'utilisateur ciblé est le bot lui-même
    if user == bot.user:
        # Redirige le mute vers l'utilisateur ayant exécuté la commande
        await interaction.response.send_message(
            f"😏 Oh non, {interaction.user.mention}, tu as essayé de me mute... mais c'est toi qui prends un tg !"
        )
        duration = 20  # Fixe la durée à 20 secondes
        mute_tasks[interaction.user.id] = asyncio.create_task(
            mute_user(interaction.user, duration, "Ne joue pas avec moi. 😎")
        )
        return

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            f"Ah la honte, {interaction.user.mention} essaie de /tg {user.mention} alors qu'il est même pas modo 🤣🫵🏻"
        )
        return

    await interaction.response.send_message(
        f"{user.mention} s'est mangé un tg pendant {duration} secondes. 🤫"
    )
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
        await interaction.response.send_message(f"{user.mention}, ça y est tu as le droit de reparler 😄")
    else:
        await interaction.response.send_message(f"{user.mention} n'a pas mangé de tg 🤓")

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