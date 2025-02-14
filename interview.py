import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("Please set the DISCORD_TOKEN environment variable.")

print(DISCORD_TOKEN)
