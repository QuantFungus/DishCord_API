import discord
import asyncio
import aiohttp
import os
import json
from discord.ext import bridge
from dotenv import load_dotenv
from openai import OpenAI

PREF_FILE = "user_prefs.json"

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")
user_preferences = {}  # Store user preferences in-memory
favorite_recipes = {}  # Store users' favorite recipes

GPTclient = OpenAI(api_key=os.environ.get('GPT_TOKEN'))

@client.listen()

def load_user_preferences():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_preferences():
    with open(PREF_FILE, "w") as f:
        json.dump(user_preferences, f)

user_preferences = load_user_preferences()

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

@client.bridge_command(description="Update preferences and save them persistently")
async def persistent_preferences(ctx, flavor: str, dish: str, diet: str):
    """Update preferences and save them to a JSON file for persistence."""
    user_id = str(ctx.author.id)
    user_preferences[user_id] = {
        "flavor": flavor,
        "favorite_dish": dish,
        "diet": diet
    }
    save_user_preferences()
    await ctx.respond(f"Preferences updated and saved!")
    
@client.bridge_command(description="Get cooking tips to improve your culinary skills")
async def cooking_tips(ctx, skill_level: str):
    """Provide cooking tips based on skill level ('beginner', 'intermediate', 'advanced')."""
    await ctx.defer()
    if skill_level.lower() not in ["beginner", "intermediate", "advanced"]:
        await ctx.respond("Invalid skill level! Choose 'beginner', 'intermediate', or 'advanced'.")
        return
    query = (
        f"Provide some cooking tips for a {skill_level} cook. "
        "Focus on techniques, tools, and best practices to improve culinary skills."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Get a random general cooking tip")
async def random_cooking_tip(ctx):
    """Get a single random cooking tip."""
    await ctx.defer()
    query = "Give me one random cooking tip that can be useful to home cooks."
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Find alternatives for a given ingredient")
async def ingredient_alternatives(ctx, *, ingredient: str):
    """Suggest alternative ingredients or synonyms that can be used in a recipe."""
    await ctx.defer()
    query = (
        f"Suggest alternatives or substitutes for {ingredient}. "
        "Include flavor profile and how they impact the recipe."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Get synonyms for an ingredient")
async def ingredient_synonyms(ctx, *, ingredient: str):
    """Provide synonyms or different names of a given ingredient (useful for global recipes)."""
    await ctx.defer()
    query = (
        f"List synonyms or regional names for the ingredient: {ingredient}. "
        "Note any differences in usage or flavor."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Generate a categorized shopping list from favorite recipes")
async def categorized_shopping_list(ctx):
    """Generate a categorized shopping list based on the user's favorite recipes."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes to generate a shopping list from.")
        return

    query = (
        "From the following recipes: "
        f"{', '.join(favorite_recipes[user_id])}, "
        "generate a shopping list categorized by sections (e.g., Produce, Dairy, Meats, Pantry). "
        "List ingredients under their respective categories."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(f"Here is your categorized shopping list:\n{response}")

@client.bridge_command(description="Show a sample of categories used in shopping lists")
async def shopping_list_categories(ctx):
    """Display sample categories used in the categorized shopping list."""
    categories = ["Produce", "Dairy", "Meats", "Seafood", "Bakery", "Pantry", "Frozen"]
    await ctx.respond("Sample shopping list categories: " + ", ".join(categories))

@client.bridge_command(description="Rewrite a given recipe's instructions with a chosen complexity")
async def rewrite_instructions(ctx, complexity: str, *, recipe: str):
    """
    Rewrite the given recipe instructions.
    complexity='simplify' to make them more beginner-friendly,
    complexity='detail' to add more detailed steps and explanations.
    """
    await ctx.defer()
    if complexity.lower() not in ["simplify", "detail"]:
        await ctx.respond("Invalid complexity level! Choose 'simplify' or 'detail'.")
        return
    query = (
        f"Rewrite the instructions of the following recipe: {recipe}. "
        f"Please {complexity} the instructions to make it more suitable for the intended audience."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Show how to use rewrite_instructions command")
async def rewrite_help(ctx):
    """Explain how to use the rewrite_instructions command."""
    await ctx.respond("Use '!rewrite_instructions simplify <recipe>' or '!rewrite_instructions detail <recipe>'.")

@client.bridge_command(description="Estimate the cost of a given recipe")
async def estimate_cost(ctx, *, recipe: str):
    """Estimate the approximate cost to prepare the given recipe."""
    await ctx.defer()
    query = (
        f"Analyze the following recipe: {recipe}. "
        "List the approximate cost of the ingredients and provide a total estimated cost. "
        "Use general market prices and specify the currency (e.g., USD)."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Suggest cost-saving tips for a given recipe")
async def cost_saving_tips(ctx, *, recipe: str):
    """Suggest ways to reduce the cost of a given recipe."""
    await ctx.defer()
    query = (
        f"Suggest cost-saving tips for the following recipe: {recipe}. "
        "Include ingredient substitutions or buying in bulk."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Suggest a beverage pairing for a given recipe")
async def beverage_pairing(ctx, *, recipe: str):
    """Suggest a suitable beverage (wine, beer, non-alcoholic) to pair with the given recipe."""
    await ctx.defer()
    query = (
        f"For the following recipe: {recipe}, "
        "suggest a beverage pairing. Include reasoning behind the choice and possible alternatives."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Suggest non-alcoholic beverage pairings for a given recipe")
async def non_alcoholic_pairing(ctx, *, recipe: str):
    """Suggest non-alcoholic beverages to complement the given recipe."""
    await ctx.defer()
    query = (
        f"For the following recipe: {recipe}, "
        "suggest a non-alcoholic beverage pairing. Mention the flavor notes that match well."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)


async def main_bot():
    print("Bot is starting...")
    await client.start(PyCordBot().TOKEN)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main_bot()))
