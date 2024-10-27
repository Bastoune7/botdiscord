import random
import asyncio

async def pile_ou_face(ctx):
    # Préparez la réponse
    await ctx.send("Attention prêt ?")
    await asyncio.sleep(1)  # Attendre 1 seconde

    for i in range(3, 0, -1):
        await ctx.send(str(i))
        await asyncio.sleep(0.5)  # Attendre 1 seconde

    # Choisir aléatoirement entre "pile" et "face"
    result = random.choice(["pile", "face"])
    await ctx.send(f"{result.capitalize()} !")