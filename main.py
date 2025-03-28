import discord
import asyncio
import os
import random
import logging
import textwrap
from discord.ext import bridge, commands
from dotenv import load_dotenv
from openai import OpenAI

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
name = {} # Just here for testing

GPTclient = OpenAI(api_key=os.environ.get('GPT_TOKEN'))

@client.listen()
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.bridge_command(description="Ping, pong!")
async def ping(ctx):
    latency = (str(client.latency)).split('.')[1][1:3]
    await ctx.respond(f"Pong! Bot replied in {latency} ms")

@client.bridge_command(description="Displays commands DishCord bot is capable of")
async def options(ctx):
    commands = textwrap.dedent("""
    /setup_preferences <flavor> <dish> <diet> - Set your preferences.
    /recipe <ingredients> [--quick] [--meal_prep] - Generate a recipe.
    /save_recipe - Save the most recent recipe to your favorites.
    /show_favorites - Display all saved recipes.
    """)
    await ctx.respond(commands)

@client.bridge_command(description="Setup user preferences")
async def setup_preferences(ctx, flavor: str, dish: str, diet: str):
    """Store user preferences for personalized suggestions."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = {
        "flavor": flavor,
        "favorite_dish": dish,
        "diet": diet
    }
    await ctx.respond(f"Preferences saved! \n**Flavor:** {flavor}\n**Dish:** {dish}\n**Diet:** {diet}")

@client.bridge_command(description="Display user preferences")
async def display_preferences(ctx):
    """Display user preferences."""
    user_id = str(ctx.author.id)

    if not user_id in user_preferences:
        await ctx.respond("You don't have any preferences yet.")

    flavor: str = user_preferences[user_id]["flavor"]
    dish: str = user_preferences[user_id]["favorite_dish"]
    diet: str = user_preferences[user_id]["diet"]
    await ctx.respond(f"Displaying preferences! \n**Flavor:** {flavor}\n**Dish:** {dish}\n**Diet:** {diet}")

@client.bridge_command(description="Generate a recipe based on ingredients")
async def recipe(ctx, *, ingredients: str):
    """Generate a recipe using the provided ingredients."""
    await ctx.defer()
    
    flavor, dish, diet = "", "", ""
    user_id = str(ctx.author.id)
    if user_id in user_preferences:
        flavor = user_preferences[user_id].get("flavor", "None")
        dish = user_preferences[user_id].get("favorite_dish", "None")
        diet = user_preferences[user_id].get("diet", "None")
    
    query = f"""
    Create a **concise** and **structured** recipe using the following ingredients: {ingredients}.
    Please follow this format:
    - **Dish Name**: Provide a creative and appropriate dish name.
    - **Ingredients**: List required ingredients (avoid redundancy).
    - **Instructions**: Give a **step-by-step** short guide (concise but clear).
    - **Nutritional Information**: If possible, estimate calories and macronutrients.
    
    User Preferences:
    - **Flavor Preferences**: {flavor}
    - **Favorite Dishes**: {dish}
    - **Dietary Restrictions**: {diet}
    
    Ensure the response is **under 2000 characters** and uses **Markdown formatting**.
    """
    
    response = get_chatgpt_response(query)
    user_id = str(ctx.author.id)
    last_query[user_id] = ingredients
    last_message[user_id] = response
    
    # Send response in chunks if necessary
    for i in range(0, len(response), 2000):
        await ctx.send(response[i:i+2000])

@client.bridge_command(description="Save a recipe to your favorites")
async def save_recipe(ctx):
    """Save a recipe to the user's favorites."""
    user_id = str(ctx.author.id)

    if user_id not in last_message:
        await ctx.respond("No previously generated recipe!")

    if user_id not in favorite_recipes:
        favorite_recipes[user_id] = []
    favorite_recipes[user_id][last_query[user_id]] = last_message[user_id]
    await ctx.respond(f"Recipe saved to your favorites!")

@client.bridge_command(description="Show all your favorite recipes")
async def show_favorites(ctx):
    """Display all the favorite recipes of the user."""
    user_id = str(ctx.author.id)
    if user_id in favorite_recipes and favorite_recipes[user_id]:
        recipes = favorite_recipes[user_id].keys()
        await ctx.respond(f"Your favorite recipes:\n{recipes}")
    else:
        await ctx.respond("You don't have any favorite recipes yet.")

@client.bridge_command(description="Recommend a recipe related to input")
async def recommend(ctx, recipe: str):
    """Generates a recipe based off an idea rather than ingredients"""
    
    flavor, dish, diet = "", "", ""
    user_id = str(ctx.author.id)
    if user_id in user_preferences:
        flavor = user_preferences[user_id].get("flavor", "None")
        dish = user_preferences[user_id].get("favorite_dish", "None")
        diet = user_preferences[user_id].get("diet", "None")

    query = f"""
    Create a **concise** and **structured** recipe using the following recipe: {recipe}.
    Please follow this format:
    - **Dish Name**: Provide a creative and appropriate dish name.
    - **Ingredients**: List required ingredients (avoid redundancy).
    - **Instructions**: Give a **step-by-step** short guide (concise but clear).
    - **Nutritional Information**: If possible, estimate calories and macronutrients.
    
    User Preferences:
    - **Flavor Preferences**: {flavor}
    - **Favorite Dishes**: {dish}
    - **Dietary Restrictions**: {diet}
    
    Ensure the response is **under 2000 characters** and uses **Markdown formatting**.
    """
    
    response = get_chatgpt_response(query)
    user_id = str(ctx.author.id)
    last_query[user_id] = recipe
    last_message[user_id] = response
    
    # Send response in chunks if necessary
    for i in range(0, len(response), 2000):
        await ctx.send(response[i:i+2000])

@client.bridge_command(description="nametest")
async def nametest(ctx):
    """dev cmd for testing local storage."""
    user_id = str(ctx.author.id)
    if user_id in name:
        await ctx.respond(f"Your 'name' is: {name[user_id]}.")
    else:
        await ctx.respond("Sorry, but there's no 'name' in the system! Please type your name in the chat.")

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            msg = await client.wait_for("message", timeout=30.0, check=check)  # Wait for user input
            name[user_id] = msg.content  # Save name
            await ctx.send(f"Thanks! Your 'name' has been set to: {name[user_id]}.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond! Try again.")

@client.bridge_command(description="Ask a question to ChatGPT")
async def ask(ctx, *, query: str):
    await ctx.defer()  # Defer the response to avoid interaction expiration
    response = get_chatgpt_response(query)
    
    # Split response into chunks of 2000 characters
    for i in range(0, len(response), 2000):
        await ctx.send(response[i:i+2000])

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
