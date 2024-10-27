import discord
import yt_dlp
import asyncio
from discord.ext import commands

# Fonction pour obtenir l'URL de l'audio YouTube
async def get_youtube_audio_url(search):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch1:',  # Rechercher la première vidéo correspondant aux termes
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=False)
        return info['url'] if 'url' in info else None

# Commande pour jouer de la musique
async def play_music(ctx, url):
    voice_client = ctx.guild.voice_client

    # Vérifier si le bot est connecté à un canal vocal
    if not voice_client:
        if ctx.author.voice:
            voice_client = await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Vous devez être connecté à un canal vocal pour jouer de la musique.")
            return

    # Charger l'URL audio et jouer
    audio_url = await get_youtube_audio_url(url)
    if audio_url:
        voice_client.stop()  # Arrêter la musique actuelle (si une musique est en cours de lecture)
        voice_client.play(discord.FFmpegPCMAudio(audio_url), after=lambda e: print(f"Erreur dans la lecture de l'audio : {e}") if e else None)
        await ctx.send(f"Lecture de votre musique : {url}")
    else:
        await ctx.send("La vidéo demandée n'a pas pu être trouvée ou extraite.")

async def stop_music(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Musique arrêtée.")
    else:
        await ctx.send("Aucune musique n'est actuellement en lecture.")

async def leave_voice_channel(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await ctx.send("Bot déconnecté du canal vocal.")
    else:
        await ctx.send("Le bot n'est connecté à aucun canal vocal.")