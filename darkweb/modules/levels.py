import json
import os
import logging

# Fichier JSON contenant les niveaux
LEVELS_PATH = "darkweb/data/levels.json"

# Logger
logger = logging.getLogger("darkweb")

def load_levels():
    """Charge les données des niveaux depuis levels.json ou génère une erreur si le fichier est vide."""
    if not os.path.exists(LEVELS_PATH):
        logger.error("[ERROR] users.json file not found. (creating a temporary empty board until bot restart.)")
        return {}

    try:
        with open(LEVELS_PATH, 'r', encoding="utf-8") as file:
            data = file.read().strip()
            if not data:
                logger.error("[ERROR] file users.json is empty. (creating a temporary empty board until bot restart.)")
                return {}
            return json.loads(data)
    except json.JSONDecodeError:
        logger.error("[ERROR] file users.json is corrupt. (creating a temporary empty board until bot restart.)")
        return {}

def get_level_data(level):
    """Retourne les informations d'un niveau donné."""
    levels = load_levels()
    return levels.get(str(level), None)

async def check_levels():
    """Vérifie que levels.json est bien chargé."""
    levels = load_levels()
    if not levels:
        logger.critical("[ERROR CRITICAL] No level data! Check levels.json.")
    else:
        logger.info(f"[CHECK] {len(levels)} levels loaded with success.")