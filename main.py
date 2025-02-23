import discord
import asyncio
import os
import random
import logging
import textwrap
from discord.ext import bridge, commands
from dotenv import load_dotenv
from openai import OpenAI
import re

logging.basicConfig(level=logging.INFO)

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = str(os.getenv("DISCORD_TOKEN"))
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")
user_preferences = {}  # Store user preferences in-memory
favorite_recipes = {}  # Store users' favorite recipes
last_message = {}  # Stores last message for purpose of storing recipe
last_query = {}  # Stores last query for purpose of storing recipe

GPTclient = OpenAI(api_key=os.environ.get('GPT_TOKEN'))

# Helper Functions
def split_into_sentences(text: str):
    """
    Splits the text into sentences based on '.', '?', or '!'
    followed by whitespace or the end of the string.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return sentences

def chunk_text_by_sentence(text: str, chunk_size: int = 2000):
    """
    Splits text into chunks of no more than `chunk_size` characters,
    ensuring we do not break any sentences.
    """
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence to current_chunk exceeds the limit, push current_chunk to chunks and start a new one.
        if len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if not current_chunk:
                current_chunk = sentence
            else:
                current_chunk += " " + sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

@client.listen()
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.bridge_command(description="Ping, pong!")
async def ping(ctx):
    latency = (str(client.latency)).split('.')[1][1:3]
    await ctx.respond(f"Pong! Bot replied in {latency} ms")

@client.bridge_command(description="Displays commands DishCord bot is capable of")
async def options(ctx):
    commands_text = textwrap.dedent("""
    /setup_preferences <flavor> <dish> <diet> - Set your preferences.
    /recipe <ingredients> [--quick] [--meal_prep] - Generate a recipe.
    /save_recipe - Save the most recent recipe to your favorites.
    /show_favorites - Display all saved recipes.
    """)
    await ctx.respond(commands_text)

@client.bridge_command(description="Setup user preferences")
async def setup_preferences(ctx, flavor: str, dish: str, diet: str):
    """Store user preferences for personalized suggestions."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = {
        "flavor": flavor,
        "favorite_dish": dish,
        "diet": diet
    }
    await ctx.respond(
        f"Preferences saved! \n**Flavor:** {flavor}\n**Dish:** {dish}\n**Diet:** {diet}"
    )

@client.bridge_command(description="Display user preferences")
async def display_preferences(ctx):
    """Display user preferences."""
    user_id = str(ctx.author.id)

    if user_id not in user_preferences:
        await ctx.respond("You don't have any preferences yet.")
        return

    flavor: str = user_preferences[user_id]["flavor"]
    dish: str = user_preferences[user_id]["favorite_dish"]
    diet: str = user_preferences[user_id]["diet"]
    await ctx.respond(
        f"Displaying preferences! \n**Flavor:** {flavor}\n**Dish:** {dish}\n**Diet:** {diet}"
    )

@client.bridge_command(description="Generate a recipe based on ingredients")
async def recipe(ctx, *, ingredients: str):
    """Generate a recipe using the provided ingredients."""
    await ctx.defer()
    query: str = f"Give me a recipe with the following ingredients: {ingredients}."

    flavor: str = ""
    dish: str = ""
    diet: str = ""
    user_id = str(ctx.author.id)
    if user_id in user_preferences:
        flavor = user_preferences[user_id]["flavor"]
        dish = user_preferences[user_id]["favorite_dish"]
        diet = user_preferences[user_id]["diet"]

    query += f"""
    If possible, include my personal preferences. Do not include them if they deviate too far from the
    recipe. For example, if I like savory and bitter flavors but the recipe asks for sweet candy, it's
    not necessary to include savory and bitter flavors.
    Flavors: {flavor}
    Dishes: {dish}
    Diet: {diet}
    """

    response = get_chatgpt_response(query)

    # Save message history
    last_query[user_id] = ingredients
    last_message[user_id] = response

    chunks = chunk_text_by_sentence(response, 2000)
    for chunk in chunks:
        await ctx.send(chunk)

@client.bridge_command(description="Save a recipe to your favorites")
async def save_recipe(ctx):
    """Save a recipe to the user's favorites."""
    user_id = str(ctx.author.id)

    if user_id not in last_message:
        await ctx.respond("No previously generated recipe!")
        return

    if user_id not in favorite_recipes:
        favorite_recipes[user_id] = {}

    favorite_recipes[user_id][last_query[user_id]] = last_message[user_id]
    await ctx.respond("Recipe saved to your favorites!")

@client.bridge_command(description="Show all your favorite recipes")
async def show_favorites(ctx):
    """Display all the favorite recipes of the user."""
    user_id = str(ctx.author.id)
    if user_id in favorite_recipes and favorite_recipes[user_id]:
        recipes = list(favorite_recipes[user_id].keys())
        recipe_list = "\n".join(recipes)
        await ctx.respond(f"Your favorite recipes:\n{recipe_list}")
    else:
        await ctx.respond("You don't have any favorite recipes yet.")

@client.bridge_command(description="Ask a question to ChatGPT")
async def ask(ctx, *, query: str):
    await ctx.defer()  # Defer the response to avoid interaction expiration
    response = get_chatgpt_response(query)

    chunks = chunk_text_by_sentence(response, 2000)
    for chunk in chunks:
        await ctx.send(chunk)

def get_chatgpt_response(query: str) -> str:
    completion = GPTclient.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ]
    )
    return completion.choices[0].message.content

async def main_bot():
    print("Bot is starting...")
    await client.start(PyCordBot().TOKEN)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main_bot()))
