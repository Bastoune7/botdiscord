import random
import asyncio
import discord

async def pile_ou_face(interaction: discord.Interaction):
    # Envoyer le premier message en réponse directe via l'interaction
    await interaction.response.send_message("Attention prêt ?")
    await asyncio.sleep(1)

    # Utiliser interaction.channel.send() pour envoyer les autres messages normalement
    channel = interaction.channel

    for i in range(3, 0, -1):
        await channel.send(str(i))
        await asyncio.sleep(0.5)

    # Choisir aléatoirement entre "pile" et "face"
    result = random.choice(["pile", "face"])
    await channel.send(f"{result.capitalize()} !")