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

# Nouvelle fonction pour démarrer le serveur Minecraft dans un sous-processus séparé
def start_minecraft_server():
    global server_process
    server_process = subprocess.Popen(
        ['start', 'powershell', '-Command', 'start_server.bat'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True
    )

# Fonction pour surveiller les logs du serveur
async def monitor_server_logs(interaction):
    if server_process is None or server_process.stdout is None:
        await interaction.followup.send("Impossible de lire les logs du serveur.")
        return

    await asyncio.sleep(5)  # Attendre pour laisser le serveur démarrer

    async with interaction.channel.typing():
        logs = []  # Stocker les lignes de logs ici
        while server_process.poll() is None:  # Tant que le serveur est en cours d'exécution
            line = server_process.stdout.readline() if server_process.stdout else ""
            logs.append(line)  # Ajouter chaque ligne lue aux logs

            if "Done" in line:  # Si le serveur est prêt
                await interaction.followup.send("Le serveur Minecraft est maintenant en ligne et accessible ! 🟢")
                return  # Quitter la fonction si le serveur a démarré correctement

            await asyncio.sleep(1)

        # Si on arrive ici, le serveur n’a pas démarré correctement
        if logs:
            error_logs = ''.join(logs)  # Joindre tous les logs en une seule chaîne
            await interaction.followup.send(f"Le serveur a échoué à démarrer. Logs:\n{error_logs}")

# Commande pour démarrer le serveur Minecraft
@bot.tree.command(name="start_minecraft", description="Démarre le serveur Minecraft.")
async def start_minecraft(interaction: discord.Interaction):
    global server_process
    await interaction.response.defer()

    if server_process is not None and server_process.poll() is None:
        await interaction.followup.send("Le serveur est déjà en cours d'exécution !")
        return

    try:
        start_minecraft_server()  # Démarrer le serveur dans un sous-processus
        await interaction.followup.send("Démarrage du serveur Minecraft...")

        # Lancer une tâche pour surveiller les logs et envoyer un message quand le serveur est prêt
        asyncio.create_task(monitor_server_logs(interaction))
    except Exception as e:
        await interaction.followup.send(f"Erreur lors du démarrage du serveur : {str(e)}")

# Commande pour arrêter le serveur Minecraft
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
        server_process = None  # Réinitialiser `server_process` pour éviter les erreurs lors du redémarrage
        await interaction.followup.send("Le serveur Minecraft a été arrêté.")
    except Exception as e:
        await interaction.followup.send(f"Erreur lors de l'arrêt du serveur : {str(e)}")

# Le reste de votre code inchangé

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot connecté en tant que {bot.user}')
    log_event("Démarrage", "Bot connecté et prêt")

# Lancer le bot
bot.run(TOKEN)