import discord
import asyncio
import random
import time
import aiohttp
import os

from discord.ext import bridge
from dotenv import load_dotenv

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")

@client.listen()
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.bridge_command(description="Ping, pong!")
async def ping(ctx):
    latency = (str(client.latency)).split('.')[1][1:3]
    await ctx.respond(f"Pong! Bot replied in {latency} ms")

async def main_bot():
    print("Bot is starting...")
    await client.start(PyCordBot().TOKEN)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main_bot()))