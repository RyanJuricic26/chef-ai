# fetch_utils.py
from typing import List, Dict, Any
import json


def format_recipe_for_llm(recipe: Dict[str, Any]) -> str:
    """
    Format a recipe dictionary into a readable string for LLM processing

    Args:
        recipe: Recipe dictionary from database

    Returns:
        Formatted recipe string
    """
    ingredients_list = []
    for ing in recipe.get('ingredients', []):
        quantity = ing.get('quantity', '')
        unit = ing.get('unit', '')
        name = ing.get('ingredient_name', '')
        available = ing.get('is_available')

        ing_str = f"{quantity} {unit} {name}".strip()
        if available is not None:
            ing_str += " [AVAILABLE]" if available else " [MISSING]"

        ingredients_list.append(ing_str)

    match_info = ""
    if 'match_percentage' in recipe:
        match_info = f"\nMatch: {recipe['match_percentage']:.1f}% ({recipe['matched_ingredients']}/{recipe['total_ingredients']} ingredients)"

    url_info = ""
    if recipe.get('url'):
        url_info = f"\nURL: {recipe['url']}"

    return f"""
Recipe: {recipe['name']}
Description: {recipe.get('description', 'N/A')}
Difficulty: {recipe.get('difficulty', 'N/A')}
Prep Time: {recipe.get('prep_time', 'N/A')} min
Cook Time: {recipe.get('cook_time', 'N/A')} min
Servings: {recipe.get('servings', 'N/A')}
Cuisine: {recipe.get('cuisine_type', 'N/A')}{match_info}{url_info}

Ingredients:
{chr(10).join(f"  - {ing}" for ing in ingredients_list)}

Instructions:
{recipe.get('instructions', 'N/A')}
""".strip()


def parse_user_ingredients(user_input: str) -> List[str]:
    """
    Parse user input to extract ingredient names

    Args:
        user_input: Raw user input string

    Returns:
        List of ingredient names
    """
    # Split by commas, newlines, or 'and'
    import re
    ingredients = re.split(r'[,\n]|\sand\s', user_input.lower())

    # Clean up each ingredient
    cleaned = []
    for ing in ingredients:
        # Remove common words and clean
        ing = ing.strip()
        # Remove articles and quantity words
        for word in ['a ', 'an ', 'the ', 'some ', 'any ']:
            if ing.startswith(word):
                ing = ing[len(word):]

        if ing:
            cleaned.append(ing.strip())

    return cleaned


def filter_recipes_by_threshold(recipes: List[Dict[str, Any]], threshold: float = 50.0) -> List[Dict[str, Any]]:
    """
    Filter recipes by match percentage threshold

    Args:
        recipes: List of recipes with match_percentage
        threshold: Minimum match percentage (default 50%)

    Returns:
        Filtered list of recipes
    """
    return [r for r in recipes if r.get('match_percentage', 0) >= threshold]


def rank_recipes(recipes: List[Dict[str, Any]], user_preferences: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Rank recipes based on match percentage and user preferences

    Args:
        recipes: List of recipes to rank
        user_preferences: Optional dict with preferences like difficulty, cuisine_type, max_time

    Returns:
        Sorted list of recipes
    """
    def score_recipe(recipe):
        score = recipe.get('match_percentage', 0)

        if user_preferences:
            # Bonus for preferred difficulty
            if user_preferences.get('difficulty') == recipe.get('difficulty'):
                score += 10

            # Bonus for preferred cuisine
            if user_preferences.get('cuisine_type') == recipe.get('cuisine_type'):
                score += 10

            # Penalty for recipes that take too long
            max_time = user_preferences.get('max_time')
            if max_time:
                total_time = (recipe.get('prep_time', 0) or 0) + (recipe.get('cook_time', 0) or 0)
                if total_time > max_time:
                    score -= 20

        return score

    return sorted(recipes, key=score_recipe, reverse=True)


def create_recipe_summary(recipes: List[Dict[str, Any]], limit: int = 5) -> str:
    """
    Create a summary of top recipes for LLM context

    Args:
        recipes: List of recipes
        limit: Maximum number of recipes to include

    Returns:
        Summary string
    """
    if not recipes:
        return "No recipes found."

    summary_parts = [f"Found {len(recipes)} recipe(s). Top {min(limit, len(recipes))} matches:\n"]

    for i, recipe in enumerate(recipes[:limit], 1):
        match_info = ""
        if 'match_percentage' in recipe:
            match_info = f" (Match: {recipe['match_percentage']:.1f}%)"

        summary_parts.append(f"{i}. {recipe['name']}{match_info}")
        summary_parts.append(f"   - {recipe.get('description', 'No description')}")
        summary_parts.append(f"   - Difficulty: {recipe.get('difficulty', 'N/A')}, "
                            f"Time: {(recipe.get('prep_time', 0) or 0) + (recipe.get('cook_time', 0) or 0)} min")
        summary_parts.append("")

    return "\n".join(summary_parts)
