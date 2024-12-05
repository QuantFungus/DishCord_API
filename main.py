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
    
@client.bridge_command(description="Generate a recipe with prep time")
async def recipe_with_prep_time(ctx, ingredients: str, prep_time: int):
    """Generate a recipe based on ingredients and desired preparation time."""
    await ctx.defer()

    # Validate preparation time
    if prep_time <= 0:
        await ctx.respond("Invalid prep time! Please provide a positive number.")
        return

    query = (
        f"Give me a recipe with the following ingredients: {ingredients}. "
        f"It should be prepared within {prep_time} minutes."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(response)
    
@client.bridge_command(description="Generate a diet-specific recipe")
async def diet_recipe(ctx, diet_type: str, *, ingredients: str):
    """Generate a recipe tailored to a specific diet type."""
    await ctx.defer()

    # Validate diet type input
    valid_diets = ["vegetarian", "vegan", "keto", "paleo", "gluten-free"]
    if diet_type.lower() not in valid_diets:
        await ctx.respond("Invalid diet type! Choose from 'vegetarian', 'vegan', 'keto', 'paleo', or 'gluten-free'.")
        return

    query = (
        f"Create a {diet_type} recipe using the following ingredients: {ingredients}. "
        "Please ensure the recipe meets the dietary guidelines."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Generate a recipe with a calorie limit")
async def recipe_with_calories(ctx, ingredients: str, max_calories: int):
    """Generate a recipe based on ingredients and calorie limit."""
    await ctx.defer()

    # Validate calorie input
    if max_calories <= 0:
        await ctx.respond("Please provide a positive calorie limit.")
        return

    query = (
        f"Give me a recipe with the following ingredients: {ingredients}. "
        f"The recipe should have a maximum of {max_calories} calories."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Generate a recipe with nutritional breakdown")
async def recipe_with_nutrition(ctx, *, ingredients: str):
    """Generate a recipe and include detailed nutritional information."""
    await ctx.defer()

    query = (
        f"Generate a recipe using the following ingredients: {ingredients}. "
        "Provide a detailed nutritional breakdown including calories, protein, fat, carbs, and other macros."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Fetch nutritional details of a single ingredient")
async def ingredient_nutrition(ctx, *, ingredient: str):
    """Fetch nutritional information of a single ingredient."""
    await ctx.defer()

    query = f"Provide the nutritional details for the ingredient: {ingredient}."
    response = await get_chatgpt_response(query)
    await ctx.respond(response)
    
@client.bridge_command(description="Generate meal prep recipes")
async def meal_prep(ctx, *, ingredients: str):
    """Generate meal prep recipes for the week."""
    await ctx.defer()

    query = (
        f"Create meal prep recipes using the following ingredients: {ingredients}. "
        "The recipes should provide enough servings for a week's worth of meals, "
        "include storage instructions, and be easy to reheat."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Generate a meal prep recipe for specific storage durations")
async def meal_prep_with_duration(ctx, ingredients: str, duration: int):
    """Generate meal prep recipes based on storage duration."""
    await ctx.defer()

    if duration <= 0:
        await ctx.respond("Invalid storage duration! Please provide a positive number.")
        return

    query = (
        f"Create meal prep recipes using the following ingredients: {ingredients}. "
        f"The meals should last for {duration} days in storage."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Tag recipes with difficulty, flavors, and time")
async def tag_recipe(ctx, recipe: str):
    """Add tags to a recipe for better categorization."""
    await ctx.defer()

    query = (
        f"Analyze the following recipe: {recipe}. "
        "Provide tags such as difficulty level, predominant flavors, and estimated preparation time."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(f"Recipe Tags:\n{response}")

@client.bridge_command(description="Search recipes by tag")
async def search_by_tag(ctx, *, tag: str):
    """Search for favorite recipes by tag."""
    user_id = str(ctx.author.id)
    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes yet.")
        return

    matched_recipes = [
        recipe for recipe in favorite_recipes[user_id] if tag.lower() in recipe.lower()
    ]

    if matched_recipes:
        recipes = "\n".join(matched_recipes)
        await ctx.respond(f"Recipes matching tag '{tag}':\n{recipes}")
    else:
        await ctx.respond(f"No recipes found with the tag '{tag}'.")

@client.bridge_command(description="Generate a weekly meal plan")
async def weekly_meal_plan(ctx, *, ingredients: str):
    """Generate a weekly meal plan based on ingredients."""
    await ctx.defer()

    query = (
        f"Create a weekly meal plan using the following ingredients: {ingredients}. "
        "Each meal should be unique, balanced, and meet general dietary guidelines. "
        "Provide meal names and a brief description for each day of the week."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Rate a recipe in your favorites")
async def rate_recipe(ctx, recipe_name: str, rating: int):
    """Allow users to rate their favorite recipes."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes to rate.")
        return

    # Validate rating
    if rating < 1 or rating > 5:
        await ctx.respond("Please provide a rating between 1 and 5.")
        return

    for recipe in favorite_recipes[user_id]:
        if recipe_name in recipe:
            if "ratings" not in recipe:
                recipe["ratings"] = []
            recipe["ratings"].append(rating)
            avg_rating = sum(recipe["ratings"]) / len(recipe["ratings"])
            await ctx.respond(f"Recipe '{recipe_name}' rated! Average Rating: {avg_rating:.2f}")
            return

    await ctx.respond(f"Recipe '{recipe_name}' not found in your favorites.")

@client.bridge_command(description="Generate a shopping list from your favorite recipes")
async def generate_shopping_list(ctx):
    """Generate a shopping list based on user's favorite recipes."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes to generate a shopping list from.")
        return

    query = (
        "Generate a comprehensive shopping list from the following recipes: "
        f"{', '.join(favorite_recipes[user_id])}. "
        "List the ingredients in quantities for a week's worth of meals."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(f"Here is your shopping list:\n{response}")

@client.bridge_command(description="Suggest a random themed recipe")
async def random_recipe(ctx, theme: str):
    """Suggest a random recipe based on a given theme (e.g., 'Italian', 'Dessert', 'Comfort Food')."""
    await ctx.defer()
    query = (
        f"Suggest a random {theme} recipe. "
        "Provide a short description and the key ingredients."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="List popular recipe themes")
async def list_themes(ctx):
    """List some popular recipe themes for inspiration."""
    themes = [
        "Italian", "Mexican", "Thai", "Chinese", "Mediterranean",
        "Dessert", "Vegan Brunch", "Comfort Food", "Holiday Special"
    ]
    formatted_themes = ", ".join(themes)
    await ctx.respond(f"Popular themes: {formatted_themes}")

@client.bridge_command(description="Translate a given recipe into another language")
async def translate_recipe(ctx, language: str, *, recipe: str):
    """Translate the provided recipe text into the specified language (e.g., 'Spanish', 'French')."""
    await ctx.defer()
    query = (
        f"Translate the following recipe into {language}: {recipe}. "
        "Ensure that the cooking terms and ingredients are accurately translated."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="List supported languages for translation")
async def list_languages(ctx):
    """List some languages supported for recipe translation."""
    languages = [
        "Spanish", "French", "German", "Italian", "Portuguese",
        "Japanese", "Korean", "Chinese (Mandarin)", "Hindi"
    ]
    formatted_langs = ", ".join(languages)
    await ctx.respond(f"Supported languages: {formatted_langs}")


async def main_bot():
    print("Bot is starting...")
    await client.start(PyCordBot().TOKEN)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main_bot()))
