import discord
from discord.ext import commands
from discord import app_commands  # Importez app_commands pour les commandes slash
from music_player import play_music, stop_music, leave_voice_channel  # Importez les fonctions de musique
import asyncio
import random  # Ajoutez cette ligne si ce n'est pas déjà fait

# Importez la fonction depuis le fichier pile_ou_face
from pile_ou_face import pile_ou_face

# Créez une instance de bot
intents = discord.Intents.default()
intents.messages = True  # Assurez-vous que les messages sont activés
intents.message_content = True  # Activer le message content intent (si nécessaire)
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()  # Synchronise les commandes slash avec Discord
    print(f'Bot connecté en tant que {bot.user}')

@bot.event
async def on_message(message):
    # Ignorer les messages du bot lui-même
    if message.author == bot.user:
        return

    # Vérifiez si le message contient "ping"
    if "ping" in message.content.lower():
        await message.channel.send("Pong! 🏓")

    if "pong" in message.content.lower():
        await message.channel.send("Bon tg")

    # Vérifiez si le message contient "joris"
    if "joris" in message.content.lower():
        await message.reply("Qu'il repose en paix 🪦😢")

    # Vérifiez si le message contient "ta gueule", "tagueule" ou "tg"
    if any(phrase in message.content.lower() for phrase in ["ta gueule", "tagueule", "tg"]):
        await message.reply("Toi ferme la 😡")

    # Assurez-vous d'appeler cette ligne pour traiter les commandes
    await bot.process_commands(message)

# Commande pile ou face en slash
@bot.tree.command(name="pileouface", description="Lance une pièce pour pile ou face")
async def pileouface_command(interaction: discord.Interaction):
    await pile_ou_face(interaction)  # Appelle la fonction du fichier pile_ou_face.py


# Commande pour jouer de la musique
@bot.command(name='play')
async def play_command(ctx, *, url: str):
    await play_music(ctx, url)

# Commande pour arrêter la musique
@bot.command(name='stop')
async def stop_command(ctx):
    await stop_music(ctx)

# Commande pour faire quitter le canal vocal au bot
@bot.command(name='leave')
async def leave_command(ctx):
    await leave_voice_channel(ctx)

# Remplacez 'YOUR_TOKEN' par votre token de bot
bot.run('MTA2NTU5MjM5Nzk0NzQ4NjMxOQ.GI3-F6.EN3876xlZRKhN8VS6_ImLpSQm3NpghSfAFKn8k')  # Remplacez par votre token