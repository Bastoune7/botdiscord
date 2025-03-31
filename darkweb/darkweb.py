import asyncio

from discord.ext import commands
import darkweb.modules.users as users  # Importation du module de gestion des utilisateurs
import darkweb.modules.levels as levels # Importation du module de gestion des levels
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

    await asyncio.gather(
        users.check_users(bot), # Vérifie les utilisateurs
        levels.check_levels() # Vérifie les niveaux
    )

    logger.info("[CHECK] DarkWeb initialisation completed")
    print("[DarkWeb] Initialisation terminée.")