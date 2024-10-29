import discord
from discord.ext import commands
from discord import app_commands
from music_player import play_music, stop_music, leave_voice_channel
import asyncio
from pile_ou_face import pile_ou_face

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot connecté en tant que {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if "ping" in message.content.lower():
        await message.channel.send("Pong! 🏓")

    if "pong" in message.content.lower():
        await message.channel.send("Bon tg")

    if "joris" in message.content.lower():
        await message.reply("Qu'il repose en paix 🪦😢")

    if any(phrase in message.content.lower() for phrase in ["ta gueule", "tagueule", "tg"]):
        await message.reply("Toi ferme la 😡")

    await bot.process_commands(message)

# Commande pile ou face en slash
@bot.tree.command(name="pileouface", description="Lance une pièce pour pile ou face")
async def pileouface_command(interaction: discord.Interaction):
    await pile_ou_face(interaction)

# Commande slash pour jouer de la musique
@bot.tree.command(name="play", description="Joue de la musique depuis une URL YouTube.")
async def play_command(interaction: discord.Interaction, url: str):
    await play_music(interaction, url)

# Commande slash pour arrêter la musique
@bot.tree.command(name="stop", description="Arrête la musique en cours.")
async def stop_command(interaction: discord.Interaction):
    await stop_music(interaction)

# Commande slash pour quitter le canal vocal
@bot.tree.command(name="leave", description="Fait quitter le canal vocal au bot.")
async def leave_command(interaction: discord.Interaction):
    await leave_voice_channel(interaction)

bot.run('')