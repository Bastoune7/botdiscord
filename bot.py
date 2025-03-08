#------------------------------------------------
#   BOT RÉALISÉ PAR BASTIEN KULMATISKI
#
#   V0.2
#------------------------------------------------


#------------------------------------------------
#   DÉPENDANCES
#------------------------------------------------

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
from mcrcon import MCRcon
import json



# Initialiser le bot et les intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)



#------------------------------------------------
#   VARIABLES GÉNÉRALES
#------------------------------------------------

BACKUP_PATH = "C:/Backup/Kulmatiski's server Backup"
SERVER_PATH = "C:/minecraft_server_java"
SERVER_IP = MinecraftServer("localhost", 10586)
RCON_HOST = "90.70.168.221"
RCON_PORT = 10587
bastien_mention = "<@337903281999314944>"
mute_tasks = {}
log_queue = asyncio.Queue()
server_process = None  # Processus du serveur Minecraft
LOG_FILE = "server.log" #Fichier de log du serveur minecraft
BOT_LOG_FILE = "log.log" #Fichier de log des événements et commandes du bot
backup_interval = timedelta(hours=24) #Intervalle par défaut des sauvegardes automatiques
last_backup_time = None
# Charger le token depuis config.txt
with open("config.txt", "r") as file:
    TOKEN = file.read().strip()
# Charger le pass rcon depuis rcon.txt
with open("rcon.txt", "r") as file:
    RCON_PASS = file.read().strip()



#------------------------------------------------
#   JOURNALISATION
#------------------------------------------------

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



#------------------------------------------------
#   COMMANDES JOURNALISATION
#------------------------------------------------

@bot.tree.command(name="log_bot", description="Envoie le dernier log du bot.")
async def log_bot(interaction: discord.Interaction):
    await interaction.response.defer()

    log_file_path = os.path.join("log.log")

    if os.path.exists(log_file_path):
        try:
            await interaction.followup.send(file=discord.File(log_file_path))
            log_command("log_bot", interaction.user, [], success=True)
        except Exception as e:
            await interaction.followup.send("❌ Erreur lors de l'envoi du fichier: le fichier log est bien présent mais je ne suis pas capable de l'envoyer. (problème de droit ... ?)")
            log_command("log_bot", interaction.user, [], success=False, error=str(e))
    else:
        await interaction.followup.send("❌ Le fichier latest.log est introuvable.")
        log_command("log_bot", interaction.user, [], success=False, error="File not found")



#------------------------------------------------
#   GESTION SERVEUR MINECRAFT
#------------------------------------------------

async def start_minecraft_server():
    global server_process
    try:
        java_path = r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe"
        server_java_path = SERVER_PATH+"/server.jar"

        with open(LOG_FILE, "w") as log_file:
            server_process = subprocess.Popen(
                [java_path, "-Xmx1024M", "-Xms1024M", "-jar", server_java_path, "nogui"],
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.PIPE,
                cwd=SERVER_PATH
            )

        await asyncio.sleep(3)  # Attend un peu pour voir si ça crashe

        if server_process.poll() is not None:
            raise RuntimeError("Le processus du serveur Minecraft s'est arrêté immédiatement.")

        return True
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur : {e}")
        return False

async def stop_minecraft_server():
    """Arrête le serveur Minercaft en envoyant la commande 'stop'"""
    global server_process
    try:
        if server_process and server_process.poll() is None:
            # Envoie la commande 'stop' au processus du serveur
            server_process.stdin.write(b"stop\n")
            server_process.stdin.flush()
            server_process.wait()  # Attend la fin du processus
            server_process = None
            return True
        return False
    except Exception as e:
        print(f"Erreur lors de l'arrêt du serveur : {e}")
        return False

async def check_minecraft_status():
    """Vérifie si le serveur Minecraft est en ligne."""
    try:
        status = SERVER_IP.status()
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



#------------------------------------------------
#   COMMANDES GESTION SERVEUR MINECRAFT
#------------------------------------------------

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
        await interaction.followup.send("❌ Échec de l'arrêt du serveur Minecraft. Le serveur n'est peut-être pas en ligne...")
        log_command("stop_minecraft", interaction.user, [], success=False)

@bot.tree.command(name="restart_minecraft", description="Redémarre le serveur Minecraft.")
async def restart_minecraft(interaction: discord.Interaction):
    global server_process
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Vous n'avez pas les permissions pour exécuter cette commande.")
        return
    await interaction.response.defer()
    success_stop = await stop_minecraft_server()

    if server_process:
        while server_process.poll() is None:
            await asyncio.sleep(1)  # Attend que le processus se termine
        server_process = None  # Réinitialise la variable du processus

    success_start = await start_minecraft_server()
    if success_stop and success_start:
        await interaction.followup.send("✅ Serveur Minecraft redémarré avec succès.")
        log_command("restart_minecraft", interaction.user, [], success=True)
    else:
        await interaction.followup.send("❌ Échec du redémarrage du serveur Minecraft. Le serveur est-il bien lancé ?")
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

@bot.tree.command(name="log_minecraft", description="Envoie le dernier log du serveur Minecraft.")
async def log_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()

    log_file_path = os.path.join(SERVER_PATH, "logs", "latest.log")

    if os.path.exists(log_file_path):
        try:
            await interaction.followup.send(file=discord.File(log_file_path))
            log_command("log_minecraft", interaction.user, [], success=True)
        except Exception as e:
            await interaction.followup.send("❌ Erreur lors de l'envoi du fichier: le fichier log est bien présent mais je ne suis pas capable de l'envoyer. (problème de droit ... ?)")
            log_command("log_minecraft", interaction.user, [], success=False, error=str(e))
    else:
        await interaction.followup.send("❌ Le fichier latest.log est introuvable.")
        log_command("log_minecraft", interaction.user, [], success=False, error="File not found")


@bot.tree.command(name="who_play_minecraft", description="Liste les joueurs actuellement en ligne sur le serveur Minecraft.")
async def joueurs_minecraft(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        # Récupère le statut du serveur
        status = SERVER_IP.status()

        # Si des joueurs sont en ligne
        if status.players.online > 0:
            online_players = status.players.sample  # Liste des joueurs en ligne
            players = ", ".join([player.name for player in online_players])  # Extraction des noms

            # Adaptation de la phrase selon le nombre de joueurs
            if status.players.online == 1:
                await interaction.followup.send(f"Le joueur en ligne est : {players}")
            else:
                await interaction.followup.send(f"Les joueurs en ligne sont : {players}")

            log_command("who_play_minecraft", interaction.user, [], success=True)
        else:
            await interaction.followup.send("Aucun joueur n'est actuellement en ligne.")
            log_command("who_play_minecraft", interaction.user, [], success=True)

    except Exception as e:
        await interaction.followup.send("❌ Impossible de récupérer la liste des joueurs en ligne. Tu peux vérifier l'état du serveur avec '/check_minecraft'.")
        log_command("who_play_minecraft", interaction.user, [], success=False)



#------------------------------------------------
#   COMMANDE BACKUP SERVEUR MINECRAFT
#------------------------------------------------

@bot.command()
async def backup_now(ctx):
    global last_backup_time

    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f"Je suis désolé, mais tu n'as pas la permission de faire une backup. Si besoin tu peux tout de même demander à {bastien_mention}")
        return

    now = datetime.now()
    if last_backup_time and now - last_backup_time < timedelta(minutes=5):
        await ctx.send("⚠️ Je suis désolé, mais la dernière backup aurait été faite il y a moins de 5min. Pour éviter de saturer le stockage des sauvegardes, je ne vais pas aller au bout de ta requête. Si ta sauvegarde est importante, attend 5min ! 😉")

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
        await ctx.send("✅ Sauvegarde du serveur minecraft effectuée avec succès !")

    except Exception as e:
        write_simple_log(f"Backup failed: {e}")
        await ctx.send(f"Échec de la sauvegarde du serveur minecraft. {bastien_mention} faudrait checker stp 🙃")

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


#------------------------------------------------
#   STATS SERVEUR MINECRAFT
#------------------------------------------------

# Fonction pour calculer le ratio K/D
def calculate_kd_ratio(kills, deaths):
    if deaths == 0:
        return kills  # Si le joueur n'a jamais été tué, son ratio est son nombre de kills
    return kills / deaths

# Fonction pour récupérer l'UUID d'un joueur depuis usercache.json
def get_uuid(username, usercache_path=SERVER_PATH+"/usercache.json"):
    try:
        with open(usercache_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        for user in user_data:
            if user["name"].lower() == username.lower():
                return user["uuid"]
    except Exception as e:
        print(f"Erreur lors de la récupération de l'UUID : {str(e)}")

    return None  # Joueur introuvable

# Fonction pour récupérer les stats du joueur depuis le fichier UUID.json
def get_player_stats(uuid, stats_path=SERVER_PATH+"/world/stats"):
    stats_file = os.path.join(stats_path, f"{uuid}.json")

    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)

        # Récupération des statistiques
        kills = stats_data["stats"]["minecraft:custom"].get("minecraft:player_kills", 0)
        deaths = stats_data["stats"]["minecraft:custom"].get("minecraft:deaths", 0)
        playtime_ticks = stats_data["stats"]["minecraft:custom"].get("minecraft:play_time", 0)

        playtime_hours = (playtime_ticks / 20) / 3600  # Convertit les ticks en heures

        return kills, deaths, playtime_hours
    except FileNotFoundError:
        return None, None, None  # Pas de stats trouvées
    except Exception as e:
        print(f"Erreur lors de la lecture des stats : {str(e)}")
        return None, None, None

# Fonction pour récupérer le nombre de blocs minés
def get_blocks_mined(uuid, block_type, stats_path=SERVER_PATH+"/world/stats"):
    stats_file = os.path.join(stats_path, f"{uuid}.json")

    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)

        blocks_mined = stats_data["stats"]["minecraft:mined"].get(block_type, 0)
        return blocks_mined
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Erreur lors de la lecture des blocs minés : {str(e)}")
        return None

# Commande Discord
@bot.tree.command(name="stats_minecraft", description="Affiche les statistiques d'un joueur du serveur Minecraft.")
async def stats_minecraft(interaction: discord.Interaction, player_name: str):
    await interaction.response.defer()

    try:
        uuid = get_uuid(player_name)
        if not uuid:
            await interaction.followup.send(f"❌ Joueur {player_name} introuvable dans le usercache.")
            return

        kills, deaths, playtime = get_player_stats(uuid)
        if kills is None:
            await interaction.followup.send(f"❌ Impossible de récupérer les statistiques de {player_name}.")
            return

        kd_ratio = calculate_kd_ratio(kills, deaths)

        mined_diamonds = get_blocks_mined(uuid, "minecraft:deepslate_diamond_ore") + get_blocks_mined(uuid, "minecraft:diamond_ore")
        mined_iron = get_blocks_mined(uuid, "minecraft:iron_ore") + get_blocks_mined(uuid, "minecraft:deepslate_iron_ore")

        response = (
            f"**Statistiques de {player_name}:**\n"
            f"⏱️ Temps de jeu : {playtime:.2f} heures\n"
            f"🗡️ Kills : {kills}\n"
            f"⚰️ Morts : {deaths}\n"
            f"☠️ Ratio K/D : {kd_ratio:.2f}" + "  (1< = plus de kill que de mort 💪)\n"
            f"💎 Diamants minés : {mined_diamonds if mined_diamonds is not None else 0}\n"
            f"⛏️ Fer miné : {mined_iron if mined_iron is not None else 0}\n"
        )

        await interaction.followup.send(response)

    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de la récupération des statistiques de {player_name}: {str(e)}")



#------------------------------------------------
#   COMMANDES ET ÉVÉNEMENTS DU BOT
#------------------------------------------------

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



#------------------------------------------------
#   COMMANDES MUSIQUES
#------------------------------------------------

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



#------------------------------------------------
#   COMMANDES GESTION DES UTILISATEURS
#------------------------------------------------

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



#------------------------------------------------
#   AUTRES COMMANDES
#------------------------------------------------

@bot.tree.command(name="pileouface", description="Lance une pièce pour pile ou face")
async def pileouface_command(interaction: discord.Interaction):
    try:
        await pile_ou_face(interaction)
        log_command("pileouface", interaction.user, [], success=True)
    except Exception as e:
        await interaction.response.send_message("Erreur lors de l'exécution de la commande.", ephemeral=True)
        log_command("pileouface", interaction.user, [], success=False)



#------------------------------------------------
#   GESTION DES SIGNAUX ET EXCEPTIONS
#------------------------------------------------

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