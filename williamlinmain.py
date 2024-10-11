import discord
import asyncio
import os
from discord.ext import bridge
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define the bot class using bridge.Bot
class PyCordBot(bridge.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TOKEN = os.getenv("DISCORD_TOKEN")

    async def on_ready(self):
        print(f"Logged in as {self.user.name}")

# Create bot instance with required intents and command prefix
intents = discord.Intents.all()
client = PyCordBot(command_prefix="!", intents=intents)

# Define a command using bridge_command decorator
@client.bridge_command(description="Ping, pong!")
async def ping(ctx):
    latency_ms = round(client.latency * 1000)  # Convert latency to milliseconds
    await ctx.respond(f"Pong! Bot replied in {latency_ms} ms")

# Main function to run the bot
async def main():
    print("Bot is starting...")
    await client.start(client.TOKEN)

# Entry point for the bot
if __name__ == "__main__":
    asyncio.run(main())
