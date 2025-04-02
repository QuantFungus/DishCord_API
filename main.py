import discord
import asyncio
import os
import logging
import textwrap
import io  # Used for exporting favorites as a file
from discord.ext import bridge
from dotenv import load_dotenv
import openai
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")

# Store data in-memory with type annotations for clarity
user_preferences: Dict[str, Dict[str, str]] = {}
favorite_recipes: Dict[str, Dict[str, str]] = {}
last_message: Dict[str, str] = {}
last_query: Dict[str, str] = {}

# Configure OpenAI
openai.api_key = os.getenv('GPT_TOKEN')
GPT_MODEL = "gpt-4o-mini"  # Update as needed

def chunk_by_lines(text: str, max_size: int = 2000) -> List[str]:
    """
    Splits the text into chunks of up to `max_size` characters without breaking lines.
    """
    lines = text.split('\n')
    chunks = []
    current_chunk = ""

    for line in lines:
        # If the line itself is too long, break it up.
        while len(line) > max_size:
            chunks.append(line[:max_size])
            line = line[max_size:]
        if len(current_chunk) + len(line) + 1 <= max_size:
            current_chunk = line if not current_chunk else current_chunk + "\n" + line
        else:
            chunks.append(current_chunk)
            current_chunk = line

    if current_chunk:
        chunks.append(current_chunk)
    return chunks

@client.listen()
async def on_ready():
    logging.info(f"Logged in as {client.user.name}")

@client.bridge_command(description="Ping, pong!")
async def ping(ctx: bridge.BridgeApplicationContext):
    # Calculate latency in milliseconds
    latency = int(client.latency * 1000)
    await ctx.respond(f"Pong! Bot replied in {latency} ms")

@client.bridge_command(description="Displays commands DishCord bot is capable of")
async def options(ctx: bridge.BridgeApplicationContext):
    commands_text = textwrap.dedent("""
    /setup_preferences <flavor> <dish> <diet> - Set your preferences.
    /display_preferences - Display your current preferences.
    /recipe <ingredients> - Generate a recipe based on your ingredients.
    /save_recipe - Save the most recent recipe to your favorites.
    /show_favorites - Display all saved recipes.
    /remove_recipe <title> - Remove a saved recipe.
    /export_favorites - Export all favorite recipes as a text file.
    /ask <query> - Ask a question to ChatGPT.
    /meal_plan - Generate a weekly meal plan based on your preferences and favorites.
    """)
    await ctx.respond(commands_text)

@client.bridge_command(description="Setup user preferences")
async def setup_preferences(ctx: bridge.BridgeApplicationContext, flavor: str, dish: str, diet: str):
    """Store user preferences for personalized suggestions."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = {"flavor": flavor, "dish": dish, "diet": diet}
    await ctx.respond(
        f"Preferences saved!\n**Flavor:** {flavor}\n**Dish:** {dish}\n**Diet:** {diet}"
    )

@client.bridge_command(description="Display user preferences")
async def display_preferences(ctx: bridge.BridgeApplicationContext):
    """Display user preferences."""
    user_id = str(ctx.author.id)
    if user_id not in user_preferences:
        await ctx.respond("You don't have any preferences yet.")
        return

    prefs = user_preferences[user_id]
    await ctx.respond(
        f"Your preferences:\n**Flavor:** {prefs.get('flavor', '')}\n**Dish:** {prefs.get('dish', '')}\n**Diet:** {prefs.get('diet', '')}"
    )

async def get_chatgpt_response(query: str) -> str:
    """
    Asynchronously fetch a response from ChatGPT using OpenAI's API.
    Uses asyncio.to_thread to avoid blocking the event loop.
    """
    def sync_chat_call() -> str:
        response = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content

    return await asyncio.to_thread(sync_chat_call)

@client.bridge_command(description="Generate a recipe based on ingredients")
async def recipe(ctx: bridge.BridgeApplicationContext, *, ingredients: str):
    """Generate a recipe using the provided ingredients."""
    await ctx.defer()
    user_id = str(ctx.author.id)
    prefs = user_preferences.get(user_id, {"flavor": "", "dish": "", "diet": ""})
    
    query = (
        f"Give me a recipe with the following ingredients: {ingredients}.\n"
        "If possible, include my personal preferences (only if they naturally fit the recipe). "
        f"Flavor: {prefs['flavor']}\nDish: {prefs['dish']}\nDiet: {prefs['diet']}\n"
    )

    try:
        response_text = await get_chatgpt_response(query)
    except Exception as e:
        logging.error("Error fetching recipe: %s", e)
        await ctx.respond("Sorry, I encountered an error while generating the recipe.")
        return

    # Save the response for later use (e.g., saving favorites)
    last_query[user_id] = ingredients
    last_message[user_id] = response_text

    for chunk in chunk_by_lines(response_text):
        await ctx.send(chunk)

@client.bridge_command(description="Save a recipe to your favorites")
async def save_recipe(ctx: bridge.BridgeApplicationContext):
    """Save the most recent recipe to the user's favorites."""
    user_id = str(ctx.author.id)
    if user_id not in last_message:
        await ctx.respond("No previously generated recipe!")
        return

    if user_id not in favorite_recipes:
        favorite_recipes[user_id] = {}

    favorite_recipes[user_id][last_query[user_id]] = last_message[user_id]
    await ctx.respond("Recipe saved to your favorites!")

@client.bridge_command(description="Show all your favorite recipes")
async def show_favorites(ctx: bridge.BridgeApplicationContext):
    """Display all saved favorite recipes."""
    user_id = str(ctx.author.id)
    if user_id in favorite_recipes and favorite_recipes[user_id]:
        recipe_titles = "\n".join(f"- {title}" for title in favorite_recipes[user_id].keys())
        await ctx.respond(f"Your favorite recipes:\n{recipe_titles}")
    else:
        await ctx.respond("You don't have any favorite recipes yet.")

@client.bridge_command(description="Remove a favorite recipe")
async def remove_recipe(ctx: bridge.BridgeApplicationContext, *, title: str):
    """Remove a saved favorite recipe using the recipe title."""
    user_id = str(ctx.author.id)
    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes yet.")
        return

    if title in favorite_recipes[user_id]:
        del favorite_recipes[user_id][title]
        await ctx.respond(f"Removed favorite recipe: {title}")
    else:
        await ctx.respond("No favorite recipe found with that title!")

@client.bridge_command(description="Export your favorite recipes to a text file")
async def export_favorites(ctx: bridge.BridgeApplicationContext):
    """Export all your saved favorite recipes as a text file attachment."""
    user_id = str(ctx.author.id)
    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes to export!")
        return

    output = io.StringIO()
    output.write("Favorite Recipes:\n")
    output.write("=" * 40 + "\n\n")
    for title, recipe in favorite_recipes[user_id].items():
        output.write(f"Recipe: {title}\n{'-' * 20}\n{recipe}\n\n")
    output.seek(0)

    file = discord.File(fp=output, filename="favorite_recipes.txt")
    await ctx.respond("Here are your exported favorite recipes:", file=file)

@client.bridge_command(description="Generate a weekly meal plan based on your preferences and favorites")
async def meal_plan(ctx: bridge.BridgeApplicationContext):
    """Generate a weekly meal plan for the upcoming week, including breakfast, lunch, and dinner for each day, plus a grocery list."""
    await ctx.defer()
    user_id = str(ctx.author.id)
    prefs = user_preferences.get(user_id, {"flavor": "", "dish": "", "diet": ""})
    favorites = favorite_recipes.get(user_id, {})

    query = (
        "Create a detailed weekly meal plan for the upcoming week (Monday to Sunday). "
        "Each day should include recipes for breakfast, lunch, and dinner. "
    )
    
    if prefs:
        query += (
            f"Consider the following user preferences: Flavor: {prefs.get('flavor', '')}, "
            f"Dish: {prefs.get('dish', '')}, Diet: {prefs.get('diet', '')}. "
        )
    
    if favorites:
        # List favorite recipe titles to incorporate if they fit naturally
        favorite_list = "\n".join(f"- {title}" for title in favorites.keys())
        query += (
            "If possible, incorporate the following favorite recipes where appropriate:\n"
            f"{favorite_list}\n"
        )
    
    query += "At the end, include a consolidated grocery shopping list for the week."

    try:
        response_text = await get_chatgpt_response(query)
    except Exception as e:
        logging.error("Error generating meal plan: %s", e)
        await ctx.respond("Sorry, I encountered an error while generating your meal plan.")
        return

    for chunk in chunk_by_lines(response_text):
        await ctx.send(chunk)


@client.bridge_command(description="Ask a question to ChatGPT")
async def ask(ctx: bridge.BridgeApplicationContext, *, query: str):
    """Ask a question to ChatGPT and get a response."""
    await ctx.defer()
    try:
        response_text = await get_chatgpt_response(query)
    except Exception as e:
        logging.error("Error fetching answer: %s", e)
        await ctx.respond("Sorry, I encountered an error while processing your question.")
        return

    for chunk in chunk_by_lines(response_text):
        await ctx.send(chunk)

async def main_bot():
    logging.info("Bot is starting...")
    await client.start(client.TOKEN)

if __name__ == "__main__":
    asyncio.run(main_bot())