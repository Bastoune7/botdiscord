import json
import logging

USERS_PATH = "darkweb/data/users.json"
LOG_FILE = "darkweb/darkweb.log"
logger = logging.getLogger("darkweb")


def get_money(user_id):
    """Retourne l'argent d'un utilisateur."""
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as file:
            users = json.load(file)
        return users.get(str(user_id), {}).get("money", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error(f"[ERROR] Impossible de charger users.json pour récupérer l'argent de {user_id}.")
        return 0


def update_money(user_id, amount):
    """Met à jour l'argent d'un utilisateur."""
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as file:
            users = json.load(file)

        if str(user_id) not in users:
            logger.error(f"[ERROR] Utilisateur {user_id} introuvable.")
            return False

        users[str(user_id)]["money"] = max(0, users[str(user_id)]["money"] + amount)

        with open(USERS_PATH, "w", encoding="utf-8") as file:
            json.dump(users, file, indent=4)

        logger.info(f"[TRANSACTION] {amount} ajouté à {user_id}. Nouveau solde: {users[str(user_id)]['money']}.")
        return True
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error(f"[ERROR] Impossible de mettre à jour l'argent de {user_id}.")
        return False


def transfer_money(from_id, to_id, amount):
    """Transfère de l'argent entre deux utilisateurs si possible."""
    if amount <= 0:
        logger.warning(f"[WARNING] Tentative de transfert invalide de {amount} de {from_id} à {to_id}.")
        return False

    if get_money(from_id) < amount:
        logger.warning(f"[WARNING] {from_id} n'a pas assez d'argent pour transférer {amount} à {to_id}.")
        return False

    if update_money(from_id, -amount) and update_money(to_id, amount):
        logger.info(f"[TRANSFER] {amount} transféré de {from_id} à {to_id}.")
        return True

    logger.error(f"[ERROR] Échec du transfert de {amount} de {from_id} à {to_id}.")
    return False
