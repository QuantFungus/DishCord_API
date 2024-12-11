import discord
import asyncio
import os
import random
from discord.ext import bridge, commands
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.all()

bot = commands.Bot(command_prefix='/')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def set_preferences(ctx, flavor: str, dietary_restrictions: str):
    if not flavor or not dietary_restrictions:
        await ctx.send("Please provide valid flavor and dietary restriction inputs.")
        return
    await ctx.send(f"Preferences saved: Flavor - {flavor}, Dietary Restrictions - {dietary_restrictions}")

bot.run('YOUR_DISCORD_TOKEN')

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")
user_preferences = {}  # Store user preferences in-memory
favorite_recipes = {}  # Store users' favorite recipes
last_message = {} # Stores last message for purpose of storing recipe
last_query = {} # Stores last query for purpose of storing recipe

GPTclient = OpenAI(api_key=os.environ.get('GPT_TOKEN'))

def generate_recipe_test(ingredients):
    tags = ["easy", "spicy", "quick", "low-calorie"]
    recipe = f"Recipe using {', '.join(ingredients)}: Delicious Dish"
    tag = random.choice(tags)
    return f"{recipe} (Tag: {tag})"

def generate_recipe_test(ingredients, quick: bool = False):
    tags = ["easy", "spicy", "low-calorie"]
    if quick: tags.append("quick")
    recipe = f"Recipe using {', '.join(ingredients)}: Delicious Dish"
    return f"{recipe} (Tag: {', '.join(tags)})"

def generate_recipe_with_nutrition(ingredients):
    nutrition = {"calories": 250, "protein": 15, "carbs": 30, "fat": 10}
    recipe = generate_recipe_test(ingredients)
    return f"{recipe}\nNutrition: {nutrition}"

@bot.command_test()
async def recipe(ctx, *ingredients):
    if not ingredients:
        await ctx.send("Please provide ingredients.")
        return
    recipe = generate_recipe_test(ingredients)
    await ctx.send(recipe)

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
    query: str = f"Give me a recipe with the following ingredients: {ingredients}."

    flavor: str = ""
    dish: str = ""
    diet: str = ""
    user_id = str(ctx.author.id)
    if user_id in user_preferences:
        flavor: str = user_preferences[user_id]["flavor"]
        dish: str = user_preferences[user_id]["favorite_dish"]
        diet: str = user_preferences[user_id]["diet"]
    query += f"""
    If possible, include my personal preferences. Do not include them if they deviate too far from the
    recipe. For example, if I like savory and bitter flavors but the recipe asks for sweet candy, it's
    not necessary to include savory and bitter flavors.
    Flavors: {flavor}
    Dishes: {dish}
    Diet: {diet}
    """

    response = get_chatgpt_response(query)
    user_id = str(ctx.author.id)
    last_query[user_id] = ingredients
    last_message[user_id] = response

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
        print(favorite_recipes[user_id])
        recipes = favorite_recipes[user_id].keys()
        await ctx.respond(f"Your favorite recipes:\n{recipes}")
    else:
        await ctx.respond("You don't have any favorite recipes yet.")

@client.bridge_command(description="Ask a question to ChatGPT")
async def ask(ctx, *, query: str):
    response = get_chatgpt_response(query)
    await ctx.respond(response)

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
