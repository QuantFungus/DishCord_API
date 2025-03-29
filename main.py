import discord
import asyncio
import aiohttp
import os
import json
import time
from discord.ext import bridge
from dotenv import load_dotenv
from openai import OpenAI
from functools import lru_cache

PREF_FILE = "user_prefs.json"
FEEDBACK_FILE = "user_feedback.log"

load_dotenv()

class PyCordBot(bridge.Bot):
    TOKEN = os.getenv("DISCORD_TOKEN")
    intents = discord.Intents.all()

client = PyCordBot(intents=PyCordBot.intents, command_prefix="!")
user_preferences = {}  # Store user preferences in-memory
favorite_recipes = {}  # Store users' favorite recipes

GPTclient = OpenAI(api_key=os.environ.get('GPT_TOKEN'))

@client.listen()

@lru_cache(maxsize=50)
def cached_chatgpt_response(query: str):
    """Caches responses to improve performance"""
    start_time = time.time()
    
    completion = GPTclient.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ]
    )
    
    elapsed_time = round(time.time() - start_time, 2)
    print(f"Response time: {elapsed_time}s")  # ✅ Log response time
    
    return completion.choices[0].message['content']

def load_user_preferences():
    if os.path.exists(PREF_FILE):
        with open(PREF_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_preferences():
    with open(PREF_FILE, "w") as f:
        json.dump(user_preferences, f)

user_preferences = load_user_preferences()

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")

def log_feedback(user_id: str, feedback: str):
    with open(FEEDBACK_FILE, "a") as f:
        f.write(f"User: {user_id}, Feedback: {feedback}\n")

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

@client.bridge_command(description="Set or update your favorite cuisines")
async def set_favorite_cuisines(ctx, *, cuisines: str):
    """Store a list of the user's favorite cuisines (comma-separated)."""
    await ctx.defer()
    user_id = str(ctx.author.id)
    cuisine_list = [c.strip() for c in cuisines.split(",") if c.strip()]
    if user_id not in user_preferences:
        user_preferences[user_id] = {}
    user_preferences[user_id]["favorite_cuisines"] = cuisine_list
    save_user_preferences()
    await ctx.respond(f"Your favorite cuisines have been updated: {', '.join(cuisine_list)}")

@client.bridge_command(description="Suggest a recipe based on your favorite cuisines")
async def cuisine_suggestions(ctx):
    """Suggest a recipe that matches the user's stored favorite cuisines."""
    await ctx.defer()
    user_id = str(ctx.author.id)
    if user_id not in user_preferences or "favorite_cuisines" not in user_preferences[user_id]:
        await ctx.respond("No favorite cuisines found. Please set them using '!set_favorite_cuisines'.")
        return
    cuisines = user_preferences[user_id]["favorite_cuisines"]
    query = (
        f"Suggest a recipe that combines or highlights these cuisines: {', '.join(cuisines)}. "
        "Focus on flavor profiles and authenticity where possible."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

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

@client.bridge_command(description="Save all recipes from a meal plan")
async def save_meal_plan(ctx, *, meal_plan: str):
    """Save all meal plan recipes to the user's favorites."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes:
        favorite_recipes[user_id] = []

    recipes = meal_plan.split("\n")  # Assume meal plan lists recipes line by line
    favorite_recipes[user_id].extend(recipes)
    save_favorite_recipes()
    
    await ctx.respond(f"All meal plan recipes have been saved to your favorites!")

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
    
@client.bridge_command(description="Search your saved recipes by ingredient")
async def search_by_ingredient(ctx, *, ingredient: str):
    """Find favorite recipes containing a specific ingredient."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes.")
        return

    matching_recipes = [recipe for recipe in favorite_recipes[user_id] if ingredient.lower() in recipe.lower()]
    
    if matching_recipes:
        await ctx.respond(f"Recipes containing '{ingredient}':\n" + "\n".join(matching_recipes))
    else:
        await ctx.respond(f"No recipes found containing '{ingredient}'.")

@client.bridge_command(description="Generate a meal plan using your favorite recipes")
async def favorite_meal_plan(ctx):
    """Create a meal plan using only the user's saved favorite recipes."""
    await ctx.defer()
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes saved.")
        return

    query = (
        f"Create a weekly meal plan using only these favorite recipes: {', '.join(favorite_recipes[user_id])}. "
        "Ensure variety and balanced nutrition."
    )

    response = await get_chatgpt_response(query)
    await ctx.respond(f"Here is your personalized meal plan:\n{response}")

@client.bridge_command(description="Exclude certain allergens or ingredients from all future suggestions")
async def set_allergens(ctx, *, allergens: str):
    """
    Store user-defined allergens to be excluded from recipe suggestions.
    Usage example: !set_allergens peanuts, shellfish
    """
    await ctx.defer()
    user_id = str(ctx.author.id)
    allergen_list = [a.strip().lower() for a in allergens.split(",") if a.strip()]

    if user_id not in user_preferences:
        user_preferences[user_id] = {}

    user_preferences[user_id]["allergens"] = allergen_list
    save_user_preferences()
    await ctx.respond(f"Allergens set! I will avoid: {', '.join(allergen_list)}")

@client.bridge_command(description="Generate a recipe with allergens excluded")
async def allergen_safe_recipe(ctx, *, ingredients: str):
    """
    Generate a recipe that avoids any user-defined allergens.
    Usage: !allergen_safe_recipe chicken, mushrooms
    """
    await ctx.defer()
    user_id = str(ctx.author.id)
    allergens = user_preferences.get(user_id, {}).get("allergens", [])

    query = (
        f"Create a recipe using these ingredients: {ingredients}, but strictly avoid: {', '.join(allergens)}. "
        "Ensure the final recipe does not contain these allergens."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Start a short cooking quiz to test your knowledge")
async def cooking_quiz(ctx):
    """
    Presents a short cooking quiz to the user.
    Usage: !cooking_quiz
    """
    await ctx.defer()
    questions = [
        ("What is the Maillard reaction?", "A chemical reaction between amino acids and reducing sugars that gives browned food its flavor."),
        ("Name one method to thicken a sauce without cornstarch or flour.", "Reducing the sauce by simmering it to evaporate liquid."),
        ("At what temperature does water typically boil at sea level (in Celsius)?", "100°C")
    ]
    # Pick a random question
    import random
    question, correct_answer = random.choice(questions)

    await ctx.respond(f"Cooking Quiz!\nQuestion: {question}\nAnswer below, then compare with `!reveal_answer`.")

    # Store correct answer in user prefs (temporary usage)
    user_id = str(ctx.author.id)
    user_preferences[user_id]["quiz_answer"] = correct_answer
    save_user_preferences()

@client.bridge_command(description="Reveal the correct answer to the cooking quiz")
async def reveal_answer(ctx):
    """Reveal the correct quiz answer stored in user preferences."""
    user_id = str(ctx.author.id)

    if user_id not in user_preferences or "quiz_answer" not in user_preferences[user_id]:
        await ctx.respond("No quiz answer found. Start a quiz with `!cooking_quiz`.")
        return

    correct_answer = user_preferences[user_id].pop("quiz_answer")
    save_user_preferences()
    await ctx.respond(f"The correct answer is: {correct_answer}")

@client.bridge_command(description="Suggest seasonal recipes based on the current month")
async def suggest_seasonal_recipes(ctx):
    """Suggest recipes that use produce in season for the current month."""
    await ctx.defer()
    # Get the current month number (1-12)
    current_month = time.localtime().tm_mon
    # Determine the seasonal produce based on the month
    if 3 <= current_month <= 5:
        produce = "spring vegetables (asparagus, peas), strawberries"
    elif 6 <= current_month <= 8:
        produce = "summer fruits (berries, stone fruits), corn"
    elif 9 <= current_month <= 11:
        produce = "autumn produce (squash, apples), root vegetables"
    else:
        produce = "winter vegetables (brussels sprouts), citrus fruits"
    # Prompt the assistant with a query about seasonal recipes
    query = f"Suggest a recipe using {produce}. Explain the seasonal benefits."
    response = await get_chatgpt_response(query)
    await ctx.respond(response)
    # End of suggest_seasonal_recipes command

@client.bridge_command(description="Get a personalized recipe recommendation based on your preferences")
async def smart_recommendations(ctx):
    """Use user preferences (flavor, favorite_dish, diet) to provide a tailored recipe suggestion."""
    await ctx.defer()
    user_id = str(ctx.author.id)
    if user_id not in user_preferences:
        await ctx.respond("No preferences found. Please set them using '!setup_preferences'.")
        return
    prefs = user_preferences[user_id]
    flavor = prefs.get("flavor", "no specific flavor")
    dish = prefs.get("favorite_dish", "any dish")
    diet = prefs.get("diet", "no dietary restrictions")
    query = (
        f"Suggest a {diet} recipe with a {flavor} flavor profile. "
        f"Ideally, it should resemble a {dish} dish."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Provide an advanced, step-by-step cooking tutorial for a dish")
async def advanced_cooking_tutorial(ctx, *, dish: str):
    """Provide a detailed cooking tutorial for advanced users."""
    await ctx.defer()
    # Additional advanced tips to be appended
    advanced_tips = [
        "Use a kitchen scale for precise measurements.",
        "Consider the Maillard reaction for better browning.",
        "Temperature control is crucial for sauce consistency."
    ]
    tips_str = " ".join(advanced_tips)
    query = (
        f"Give an advanced, step-by-step cooking tutorial for {dish}. "
        "Include precise techniques, timing, and tips to master the dish. "
        f"Additionally, incorporate these tips: {tips_str}"
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Share a saved recipe with another user")
async def share_recipe(ctx, user: discord.Member, *, recipe_name: str):
    """Share a saved recipe with another Discord user."""
    sender_id = str(ctx.author.id)

    if sender_id not in favorite_recipes or not favorite_recipes[sender_id]:
        await ctx.respond("You don't have any favorite recipes.")
        return

    if recipe_name in favorite_recipes[sender_id]:
        await user.send(f"{ctx.author.name} has shared a recipe with you: {recipe_name}")
        await ctx.respond(f"Recipe '{recipe_name}' has been shared with {user.mention}!")
    else:
        await ctx.respond(f"Recipe '{recipe_name}' not found in your favorites.")

recipe_tags = {}  # Dictionary to store recipe tags

@client.bridge_command(description="Tag a saved recipe for better organization")
async def tag_recipe(ctx, recipe_name: str, tag: str):
    """Allow users to add custom tags to saved recipes."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or recipe_name not in favorite_recipes[user_id]:
        await ctx.respond(f"Recipe '{recipe_name}' not found in your favorites.")
        return

    if user_id not in recipe_tags:
        recipe_tags[user_id] = {}

    if recipe_name not in recipe_tags[user_id]:
        recipe_tags[user_id][recipe_name] = []

    recipe_tags[user_id][recipe_name].append(tag)
    await ctx.respond(f"Tagged '{recipe_name}' with '{tag}'.")

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

@client.bridge_command(description="Submit feedback for the bot or recipes")
async def submit_feedback(ctx, *, feedback: str):
    """Allows users to submit feedback which is logged locally."""
    user_id = str(ctx.author.id)
    log_feedback(user_id, feedback)
    await ctx.respond("Thank you for your feedback! It has been recorded.")

@client.bridge_command(description="Show a summary of recent feedback (Admin only)")
async def show_feedback(ctx, limit: int = 5):
    """Show the most recent feedback entries. Admin only."""
    # This is a mock admin check. In a real scenario, check roles or IDs.
    if str(ctx.author.id) != "YOUR_ADMIN_USER_ID_HERE":
        await ctx.respond("You are not authorized to view feedback.")
        return

    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r") as f:
            lines = f.readlines()
        recent_feedback = lines[-limit:] if len(lines) > 0 else []
        if recent_feedback:
            formatted = "".join(recent_feedback)
            await ctx.respond(f"Recent feedback:\n{formatted}")
        else:
            await ctx.respond("No feedback recorded yet.")
    else:
        await ctx.respond("No feedback file found.")

@client.bridge_command(description="Remove a recipe from your favorites")
async def remove_recipe(ctx, *, recipe_name: str):
    """Remove a recipe from the user's favorites."""
    user_id = str(ctx.author.id)

    if user_id not in favorite_recipes or not favorite_recipes[user_id]:
        await ctx.respond("You don't have any favorite recipes.")
        return

    if recipe_name in favorite_recipes[user_id]:
        favorite_recipes[user_id].remove(recipe_name)
        save_favorite_recipes()
        await ctx.respond(f"Recipe '{recipe_name}' has been removed from your favorites.")
    else:
        await ctx.respond(f"Recipe '{recipe_name}' not found in your favorites.")

@client.bridge_command(description="Bookmark a recipe with optional tags")
async def bookmark_recipe(ctx, recipe: str, *, tags: str = ""):
    """Save a recipe to the user's favorites with optional tags."""
    user_id = str(ctx.author.id)
    if user_id not in favorite_recipes:
        favorite_recipes[user_id] = []
    if recipe not in favorite_recipes[user_id]:
        favorite_recipes[user_id].append(recipe)

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if user_id not in recipe_tags:
            recipe_tags[user_id] = {}
        recipe_tags[user_id][recipe] = tag_list

    await ctx.respond(f"Recipe bookmarked! Tags: {tags if tags else 'None'}")
    
@client.bridge_command(description="Suggest a seasonal recipe")
async def seasonal_recipe(ctx):
    """Suggest recipes using produce in season for the current month."""
    await ctx.defer()
    month = time.localtime().tm_mon
    seasonal_map = {
        (12, 1, 2): "root vegetables, citrus",
        (3, 4, 5): "asparagus, peas, strawberries",
        (6, 7, 8): "corn, tomatoes, berries",
        (9, 10, 11): "pumpkin, apples, squash"
    }
    for months, produce in seasonal_map.items():
        if month in months:
            break

    query = f"Suggest a recipe using the following seasonal produce: {produce}"
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

@client.bridge_command(description="Get an advanced tutorial for a dish")
async def advanced_tutorial(ctx, *, dish: str):
    """Get a detailed, pro-level tutorial for a given dish."""
    await ctx.defer()
    query = (
        f"Give me an advanced tutorial for preparing {dish}. "
        "Include precise measurements, cooking techniques, timing, and tips used by professional chefs."
    )
    response = await get_chatgpt_response(query)
    await ctx.respond(response)

async def main_bot():
    print("Bot is starting...")
    await client.start(PyCordBot().TOKEN)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(main_bot()))
