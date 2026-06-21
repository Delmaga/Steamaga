"""
Point d'entrée du bot Discord Steam.

Lancement :
    python main.py

Variables d'environnement requises (fichier .env, voir .env.example) :
    DISCORD_TOKEN=xxxxx
"""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

import database as db

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} commande(s) slash synchronisée(s).")
    except Exception as e:
        print(f"Erreur de synchronisation des commandes : {e}")


async def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN manquant. Crée un fichier .env à partir de .env.example."
        )
    db.init_db()
    async with bot:
        await bot.load_extension("cogs.steam_commands")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
