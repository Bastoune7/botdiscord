import json
import logging
import discord
from discord.ext import commands
import os

# Définition du chemin du fichier JSON
DATA_PATH = "darkweb/data/users.json"
LOG_FILE = "darkweb/darkweb.log"
ALLOWED_GUILDS = [1355821337322590299]

# Log System
logger = logging.getLogger("darkweb")

def load_users():
    """Charge les données des utilisateurs depuis le fichier JSON ou initialise un dictionnaire vide."""
    if not os.path.exists(DATA_PATH):
        logger.error("[ERROR] users.json file not found. (creating a temporary empty board until bot restart.)")
        return {} # Si le fichier n'existe pas, on retourne un tableau vide

    try:
        with open(DATA_PATH, 'r', encoding="utf-8") as file:
            data = file.read().strip()
            return json.loads(data) if data else {} # Retourne un tableau vide si le fichier est existant mais vide
    except json.JSONDecodeError:
        logger.error("[ERROR] file users.json is corrupt. It will be reset.")
        return{} # En cas d'erreur JSON on retourne un tableau vide


def save_users(users):
    """Sauvegarde les données des utilisateurs dans le fichier JSON."""
    with open(DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4, ensure_ascii=False)
    logger.info("[UPDATE] update users.json file.")


def create_user(member: discord.Member):
    """Crée une fiche utilisateur par défaut."""
    new_user = {
        "id": member.id,
        "pseudo_darkweb": f"H4ck3r_{member.id % 1000}",
        "personal_data": {
            "name": member.name,
            "surname": "Unknown",
            "items": []
        },
        "money": 1000,
        "xp": 0,
        "level": 0,
        "hacks_received": 0,
        "hacks_successful_received": 0,
        "hacks_attempted": 0,
        "hacks_successful": 0,
        "contracts_active": [],
        "contracts_completed": []
    }
    logger.info(f"[UPDATE] New user added : {member.name} (ID: {member.id} )")
    return new_user


async def check_users(bot):
    """Vérifie et met à jour les utilisateurs dans users.json lors du démarrage du bot."""
    users = load_users()
    for guild in bot.guilds:
        if guild.id in ALLOWED_GUILDS:  # Vérifie que le serveur est autorisé
            for member in guild.members:
                if not member.bot and str(member.id) not in users:
                    users[str(member.id)] = create_user(member)

    save_users(users)
    logger.info(f"[CHECK] Users check up completed")