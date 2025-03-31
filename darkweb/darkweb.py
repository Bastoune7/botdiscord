from discord.ext import commands
import darkweb.modules.users as users  # Importation du module de gestion des utilisateurs
import logging

# Log system
LOG_FILE = "darkweb/darkweb.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("darkweb") # Creating a global logger


async def setup_darkweb(bot):
    """initialise le module DarkWeb"""
    await users.check_users(bot) # Vérifie et met à jour les utilisateurs au démarrage

    logger.info("[CHECK] DarkWeb initialisation completed")
    print("[DarkWeb] Initialisation terminée.")