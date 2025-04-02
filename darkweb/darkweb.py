import asyncio
from discord.ext import commands
import darkweb.modules.users as users  # Importation du module de gestion des utilisateurs
import darkweb.modules.levels as levels # Importation du module de gestion des levels
import darkweb.modules.economy as economy # Importation du module de gestion de l'économie

import logging
import json
import itertools
import sys



# Log system
LOG_FILE = "darkweb/darkweb.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logger = logging.getLogger("darkweb") # Creating a global logger


# Charger les utilisateurs pour vérifier s'ils sont des hackers
def is_hacker(user_id):
    with open("darkweb/data/users.json", "r", encoding="utf-8") as file:
        users = json.load(file)
    return str(user_id) in users and users[str(user_id)].get("level", 0) > 0



async def setup_darkweb(bot):
    logger.info("[CHECK] DarkWeb initialisation started")
    print("[DarkWeb] Initialisation started.")

    await asyncio.gather(
        users.check_users(bot), # Vérifie les utilisateurs
        levels.check_levels() # Vérifie les niveaux
    )

    logger.info("[CHECK] DarkWeb initialisation completed")
    print("[DarkWeb] Initialisation completed.")

    ############# TEST #############

    @bot.command(name="accessdarkweb")  # Une commande cachée
    async def secret_hack(ctx):
        if not is_hacker(ctx.author.id):
            await ctx.message.delete()
            await ctx.author.send("⚠️⛔️BZZTT BZZTT ‼️ Tu vas un peu trop vite là... 😁 Attend un peu ton tour viendra 😉")
            return
        try:
            # 🔹 Essayer d'envoyer un MP
            await ctx.author.send(f"🔓 {ctx.author.mention}, accès au DarkWeb validé.")
        except discord.HTTPException:  # 🔥 Catcher une erreur plus large si les MP sont désactivés
            await ctx.send("❌ Impossible d'envoyer un message privé. Vérifie tes paramètres de confidentialité.")

        # 🔹 Supprimer le message de commande après l'envoi du MP ou en cas d'erreur
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass  # Éviter une erreur si le bot ne peut pas supprimer le message
    #bot.add_command(secret_hack)

    @bot.command()
    async def fake_type(ctx):
        """Simule une animation de frappe dans le chat Discord avant d'envoyer un message."""

        loading_frames = ["|", "/", "--", "\\"]
        message = await ctx.reply("🟠 Requesting access to the DarkWeb...")  # Message initial
        await asyncio.sleep(0.5)

        for _ in range(4):  # Nombre d'itérations de l'animation
            for frame in loading_frames:
                await message.edit(content=f"{frame} 🟠Requesting access to the DarkWeb...")  # Modifie le message
                await asyncio.sleep(0.1)  # Pause entre chaque frame

        await message.edit(content="**🟢 Access Granted**")  # Message final

#### TEST MONNAIE ####
    @bot.command(name="getmoney")
    async def getmoney(ctx, user_id: int):
        """Commande pour vérifier l'argent d'un utilisateur."""
        money = economy.get_money(user_id)
        await ctx.send(f"L'utilisateur {user_id} a {money} crédits.")

    @bot.command(name="transfer")
    async def transfer(ctx, from_id: int, to_id: int, amount: int):
        """Commande pour transférer de l'argent entre deux utilisateurs."""
        success = economy.transfer_money(from_id, to_id, amount)
        if success:
            await ctx.send(f"💸 Transfert de {amount} crédits de {from_id} à {to_id} réussi !")
        else:
            await ctx.send(f"❌ Échec du transfert : fonds insuffisants.")
    ############# TEST #############