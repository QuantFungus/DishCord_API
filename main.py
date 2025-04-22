import discord
import asyncio
import os
import logging
import textwrap
import io
import random
import json
from discord.ext import bridge
from dotenv import load_dotenv
import openai

# -------------------- Configuration --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

DATA_FILE = os.getenv('DATA_FILE', 'bot_data.json')

# Load or initialize persistent storage
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
else:
    data = {
        "prefs": {},            # user_id -> { flavor, dish, diet }
        "recipes": {},          # user_id -> { title -> recipe_text }
        "last_query": {},       # user_id -> last ingredients
        "last_msg": {}          # user_id -> last generated recipe text
    }


def save_data():
    """Write the current data dict back to disk."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# -------------------- Bot Setup --------------------
class PyCordBot(bridge.Bot):
    """Custom Bot class using discord.py Bridge."""
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents)

# OpenAI configuration
openai.api_key = os.getenv('GPT_TOKEN')
GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-4o-mini')

# -------------------- Utilities --------------------
def chunk_by_lines(text: str, max_size: int = 2000):
    """
    Split `text` into chunks up to max_size characters without breaking lines.
    """
    lines = text.split('\n')
    chunks = []
    current = ""
    for line in lines:
        while len(line) > max_size:
            chunks.append(line[:max_size])
            line = line[max_size:]
        if len(current) + len(line) + 1 <= max_size:
            current = line if not current else current + '\n' + line
        else:
            chunks.append(current)
            current = line
    if current:
        chunks.append(current)
    return chunks

async def make_embed(title: str, fields: dict):
    """Create a Discord Embed from title and a dict of fields."""
    embed = discord.Embed(title=title, color=discord.Color.blurple())
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed

async def get_chatgpt_response(query: str) -> str:
    """
    Fetch a response from OpenAI GPT in a thread to avoid blocking.
    """
    def sync_call():
        resp = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        )
        return resp.choices[0].message.content
    return await asyncio.to_thread(sync_call)

# -------------------- Events --------------------
@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_application_command_error(ctx, error):
    if isinstance(error, bridge.MissingRequiredArgument):
        await ctx.respond("❗ Missing argument. Check command usage.")
    else:
        logging.exception(error)
        await ctx.respond("❗ An unexpected error occurred. The issue has been logged.")

# -------------------- Commands --------------------
@client.bridge_command(description="Ping the bot and get latency.")
async def ping(ctx):
    latency_ms = int(client.latency * 1000)
    await ctx.respond(f"Pong! 🏓 Latency: {latency_ms}ms")

@client.bridge_command(description="List available commands.")
async def options(ctx):
    commands_text = textwrap.dedent("""
    /setup_preferences <flavor> <dish> <diet>  • Set or update your preferences
    /display_preferences                 • Show your saved preferences
    /clear_preferences                   • Remove your saved preferences

    /recipe <ingredients>                • Generate a recipe
    /save_recipe                         • Save last recipe
    /show_favorites                      • List saved recipes
    /remove_recipe <title>               • Delete a favorite
    /clear_favorites                     • Remove all favorites
    /export_favorites                    • Download favorites as text file
    /random_recipe                       • Show a random favorite

    /meal_plan                           • Create a weekly meal plan
    /ask <query>                         • Ask ChatGPT any question
    """)
    await ctx.respond(f"```\n{commands_text}```")

# Preferences
@client.bridge_command(description="Save or update your flavor/dish/diet preferences.")
async def setup_preferences(ctx, flavor: str, dish: str, diet: str):
    uid = str(ctx.author.id)
    data['prefs'][uid] = {'Flavor': flavor, 'Dish': dish, 'Diet': diet}
    save_data()
    embed = await make_embed("✅ Preferences Saved", data['prefs'][uid])
    await ctx.respond(embed=embed)

@client.bridge_command(description="Show your current preferences.")
async def display_preferences(ctx):
    uid = str(ctx.author.id)
    prefs = data['prefs'].get(uid)
    if not prefs:
        return await ctx.respond("You have no preferences set. Use /setup_preferences.")
    embed = await make_embed("📝 Your Preferences", prefs)
    await ctx.respond(embed=embed)

@client.bridge_command(description="Clear your saved preferences.")
async def clear_preferences(ctx):
    uid = str(ctx.author.id)
    if data['prefs'].pop(uid, None):
        save_data()
        await ctx.respond("✅ Preferences cleared.")
    else:
        await ctx.respond("You had no preferences to clear.")

# Recipe management
@client.bridge_command(description="Generate a recipe from ingredients.")
async def recipe(ctx, *, ingredients: str):
    await ctx.defer()
    uid = str(ctx.author.id)
    prefs = data['prefs'].get(uid, {})

    query = f"Create a recipe using: {ingredients}."
    if prefs:
        pref_list = ", ".join(f"{k}: {v}" for k, v in prefs.items())
        query += f"\nConsider these preferences: {pref_list}."

    try:
        text = await get_chatgpt_response(query)
    except Exception as e:
        logging.error("Recipe error: %s", e)
        return await ctx.respond("❗ Error generating recipe.")

    data['last_query'][uid] = ingredients
    data['last_msg'][uid] = text
    save_data()

    for chunk in chunk_by_lines(text):
        await ctx.send(chunk)

@client.bridge_command(description="Save your last generated recipe.")
async def save_recipe(ctx):
    uid = str(ctx.author.id)
    title = data['last_query'].get(uid)
    text = data['last_msg'].get(uid)
    if not title or not text:
        return await ctx.respond("No recent recipe to save.")

    data['recipes'].setdefault(uid, {})[title] = text
    save_data()
    await ctx.respond(f"✅ Saved recipe: **{title}**")

@client.bridge_command(description="List your saved favorite recipes.")
async def show_favorites(ctx):
    uid = str(ctx.author.id)
    favs = data['recipes'].get(uid, {})
    if not favs:
        return await ctx.respond("You have no favorite recipes.")
    titles = "\n".join(f"• {t}" for t in favs)
    await ctx.respond(f"**Your Favorites:**\n{titles}")

@client.bridge_command(description="Remove one favorite recipe.")
async def remove_recipe(ctx, *, title: str):
    uid = str(ctx.author.id)
    if data['recipes'].get(uid, {}).pop(title, None):
        save_data()
        await ctx.respond(f"✓ Removed: **{title}**")
    else:
        await ctx.respond("Recipe not found in your favorites.")

@client.bridge_command(description="Clear all favorite recipes.")
async def clear_favorites(ctx):
    uid = str(ctx.author.id)
    if data['recipes'].pop(uid, None) is not None:
        save_data()
        await ctx.respond("✅ All favorites cleared.")
    else:
        await ctx.respond("You had no favorites to clear.")

@client.bridge_command(description="Export favorites as a text file.")
async def export_favorites(ctx):
    uid = str(ctx.author.id)
    favs = data['recipes'].get(uid)
    if not favs:
        return await ctx.respond("You have no favorites to export.")

    buf = io.StringIO()
    buf.write("Your Favorite Recipes:\n\n")
    for title, txt in favs.items():
        buf.write(f"== {title} ==\n{txt}\n\n")
    buf.seek(0)

    await ctx.send("📄 Here is your favorites file:", file=discord.File(buf, "favorites.txt"))

@client.bridge_command(description="Show a random favorite recipe.")
async def random_recipe(ctx):
    uid = str(ctx.author.id)
    favs = data['recipes'].get(uid, {})
    if not favs:
        return await ctx.respond("No favorites to choose from.")
    title = random.choice(list(favs))
    await ctx.respond(f"🎲 **{title}**\n{favs[title]}")

# Meal plan & general ask
@client.bridge_command(description="Generate a weekly meal plan.")
async def meal_plan(ctx):
    await ctx.defer()
    uid = str(ctx.author.id)
    prefs = data['prefs'].get(uid, {})
    favs = data['recipes'].get(uid, {})

    query = (
        "Create a weekly meal plan (Mon–Sun) with breakfast, lunch, dinner."
    )
    if prefs:
        pref_str = ", ".join(f"{k}: {v}" for k, v in prefs.items())
        query += f" Consider preferences: {pref_str}."
    if favs:
        fav_list = ", ".join(favs.keys())
        query += f" Include favorite recipes when possible: {fav_list}."
    query += " Provide a consolidated grocery list at the end."

    try:
        plan = await get_chatgpt_response(query)
    except Exception as e:
        logging.error("Meal plan error: %s", e)
        return await ctx.respond("❌ Error generating meal plan.")

    for chunk in chunk_by_lines(plan):
        await ctx.send(chunk)

@client.bridge_command(description="Ask ChatGPT any question.")
async def ask(ctx, *, question: str):
    await ctx.defer()
    try:
        answer = await get_chatgpt_response(question)
    except Exception as e:
        logging.error("Ask error: %s", e)
        return await ctx.respond("❗ Error processing your question.")
    for chunk in chunk_by_lines(answer):
        await ctx.send(chunk)

# -------------------- Main --------------------
async def main_bot():
    logging.info("Starting bot...")
    await client.start(PyCordBot.TOKEN)

if __name__ == '__main__':
    asyncio.run(main_bot())