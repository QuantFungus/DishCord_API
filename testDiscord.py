# Just here to test the env variable for your DISCORD_TOKEN which should run without error

import discord
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the Discord token from environment variable
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("Please set the DISCORD_TOKEN environment variable.")

print(DISCORD_TOKEN)

class TestBot(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.close()  # Immediately close after successful login

intents = discord.Intents.default()
client = TestBot(intents=intents)

try:
    client.run(DISCORD_TOKEN)
except discord.errors.LoginFailure:
    print("Invalid Discord token. Please check your .env file.")
