import json
import discord
from discord.ext import commands
import os

# Définition du chemin du fichier JSON
DATA_PATH = "darkweb/data/users.json"
ALLOWED_GUILDS = [1355821337322590299]


def load_users():
    """Charge les données des utilisateurs depuis le fichier JSON ou initialise un dictionnaire vide."""
    if not os.path.exists(DATA_PATH):
        return {} # Si le fichier n'existe pas, on retourne un tableau vide

    try:
        with open(DATA_PATH, 'r', encoding="utf-8") as file:
            data = file.read().strip()
            return json.loads(data) if data else {} # Retourne un tableau vide si le fichier est existant mais vide
    except json.JSONDecodeError:
        print("[ERREUR] Fichier users.json corrompu, il sera réinitialisé.")
        return{} # En cas d'erreur JSON on retourne un tableau vide


def save_users(users):
    """Sauvegarde les données des utilisateurs dans le fichier JSON."""
    with open(DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4, ensure_ascii=False)


def create_user(member: discord.Member):
    """Crée une fiche utilisateur par défaut."""
    return {
        "id": member.id,
        "pseudo_darkweb": f"H4ck3r_{member.id % 1000}",
        "personal_data": {
            "name": member.name,
            "surname": "Unknown",
            "items": []
        },
        "money": 1000,
        "xp": 0,
        "level": 1,
        "hacks_received": 0,
        "hacks_successful_received": 0,
        "hacks_attempted": 0,
        "hacks_successful": 0,
        "contracts_active": [],
        "contracts_completed": []
    }


async def check_users(bot):
    """Vérifie et met à jour les utilisateurs dans users.json lors du démarrage du bot."""
    users = load_users()
    for guild in bot.guilds:
        if guild.id in ALLOWED_GUILDS:  # Vérifie que le serveur est autorisé
            for member in guild.members:
                if not member.bot and str(member.id) not in users:
                    users[str(member.id)] = create_user(member)

    save_users(users)


class UserManager(commands.Cog):
    """Cog pour gérer les utilisateurs du Dark Web."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await check_users(self.bot)
        print("[DarkWeb] Vérification des utilisateurs terminée.")


async def setup(bot):
    await bot.add_cog(UserManager(bot))
