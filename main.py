import discord
import asyncio
import aiohttp
import os
from discord.ext import bridge
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")
user_preferences = {}  # Store user preferences in-memory
favorite_recipes = {}  # Store users' favorite recipes

GPTclient = OpenAI(api_key=os.environ.get('GPT_TOKEN'))

@client.listen()
async def on_ready():
    print(f"Logged in as {client.user.name}")

@client.bridge_command(description="Ping, pong!")
async def ping(ctx):
    latency = (str(client.latency)).split('.')[1][1:3]
    await ctx.respond(f"Pong! Bot replied in {latency} ms")
    
@client.bridge_command(description="Setup user preferences")
async def setup_preferences(ctx, flavor: str, dish: str, diet: str):
    """Store user preferences for personalized suggestions."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = {
        "flavor": flavor,
        "favorite_dish": dish,
        "diet": diet
    }
    await ctx.respond(f"Preferences saved! Flavor: {flavor}, Dish: {dish}, Diet: {diet}")

@client.bridge_command(description="Generate a recipe based on ingredients")
async def recipe(ctx, *, ingredients: str):
    """Generate a recipe using the provided ingredients."""
    await ctx.defer()
    query = f"Give me a recipe with the following ingredients: {ingredients}"
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Save a recipe to your favorites")
async def save_recipe(ctx, *, recipe: str):
    """Save a recipe to the user's favorites."""
    user_id = str(ctx.author.id)
    if user_id not in favorite_recipes:
        favorite_recipes[user_id] = []
    favorite_recipes[user_id].append(recipe)
    await ctx.respond(f"Recipe saved to your favorites!")

@client.bridge_command(description="Show all your favorite recipes")
async def show_favorites(ctx):
    """Display all the favorite recipes of the user."""
    user_id = str(ctx.author.id)
    if user_id in favorite_recipes and favorite_recipes[user_id]:
        recipes = "\n".join(favorite_recipes[user_id])
        await ctx.respond(f"Your favorite recipes:\n{recipes}")
    else:
        await ctx.respond("You don't have any favorite recipes yet.")

@client.bridge_command(description="Ask a question to ChatGPT")
async def ask(ctx, *, query: str):
    await ctx.defer()  # Defer response to let users know the bot is working.
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

async def get_chatgpt_response(query: str) -> str:
    
    completion = GPTclient.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ]
    )

    return completion.choices[0].message['content']

@client.bridge_command(description="Generate a recipe based on ingredients and weight goal")
async def recipe_with_goal(ctx, ingredients: str, goal: str):
    """Generate a recipe using ingredients and weight management goal."""
    await ctx.defer()

    # Validate goal input
    if goal.lower() not in ["gain", "lose", "maintain"]:
        await ctx.respond("Invalid goal! Please choose from 'gain', 'lose', or 'maintain'.")
        return

    query = (
        f"Give me a recipe with the following ingredients: {ingredients}. "
        f"The user is trying to {goal} weight."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(response)

async def main_bot():
    print("Bot is starting...")
    await client.start(PyCordBot().TOKEN)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main_bot()))
