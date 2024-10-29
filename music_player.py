import discord
import yt_dlp
import asyncio

async def get_youtube_audio_url(search):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch1:',
        'quiet': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=False)
        return info['url'] if 'url' in info else None

# Commande pour jouer de la musique
async def play_music(interaction: discord.Interaction, url):
    voice_client = interaction.guild.voice_client

    if not voice_client:
        if interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
        else:
            await interaction.response.send_message("Vous devez être connecté à un canal vocal pour jouer de la musique.", ephemeral=True)
            return

    audio_url = await get_youtube_audio_url(url)
    if audio_url:
        voice_client.stop()
        voice_client.play(discord.FFmpegPCMAudio(audio_url), after=lambda e: print(f"Erreur dans la lecture de l'audio : {e}") if e else None)
        await interaction.response.send_message(f"Lecture de votre musique : {url}")
    else:
        await interaction.response.send_message("La vidéo demandée n'a pas pu être trouvée ou extraite.", ephemeral=True)

# Commande pour arrêter la musique
async def stop_music(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Musique arrêtée.")
    else:
        await interaction.response.send_message("Aucune musique n'est actuellement en lecture.", ephemeral=True)

# Commande pour faire quitter le canal vocal au bot
async def leave_voice_channel(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Bot déconnecté du canal vocal.")
    else:
        await interaction.response.send_message("Le bot n'est connecté à aucun canal vocal.", ephemeral=True)