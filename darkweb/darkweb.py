from discord.ext import commands
import darkweb.modules.users as users  # Importation du module de gestion des utilisateurs

async def setup_darkweb(bot):
    """initialise le module DarkWeb"""
    await users.check_users(bot) # Vérifie et met à jour les utilisateurs au démarrage
    print("[DarkWeb] Initialisation terminée.")