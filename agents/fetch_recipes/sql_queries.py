# sql_queries.py
import sqlite3
from typing import List, Dict, Any

DB_PATH = "database/app.db"

def get_all_recipes() -> List[Dict[str, Any]]:
    """
    Fetch all recipes from the database with their ingredients

    Returns:
        List of recipe dictionaries with ingredients included
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all recipes
    cur.execute("""
        SELECT
            id, name, description, instructions,
            prep_time, cook_time, servings, difficulty, cuisine_type, url
        FROM recipes
        ORDER BY name
    """)

    recipes = []
    for row in cur.fetchall():
        recipe = dict(row)
        recipe_id = recipe['id']

        # Get ingredients for this recipe
        cur.execute("""
            SELECT
                i.name as ingredient_name,
                i.category,
                ri.quantity,
                ri.unit,
                ri.notes
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = ?
            ORDER BY i.name
        """, (recipe_id,))

        recipe['ingredients'] = [dict(ing) for ing in cur.fetchall()]
        recipes.append(recipe)

    conn.close()
    return recipes


def get_recipes_by_ingredients(ingredient_names: List[str]) -> List[Dict[str, Any]]:
    """
    Find recipes that can be made with the given ingredients

    Args:
        ingredient_names: List of ingredient names the user has

    Returns:
        List of recipe dictionaries with match percentage
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Create placeholders for the IN clause
    placeholders = ','.join('?' * len(ingredient_names))

    # Get recipes and calculate match percentage
    cur.execute(f"""
        SELECT
            r.id, r.name, r.description, r.instructions,
            r.prep_time, r.cook_time, r.servings, r.difficulty, r.cuisine_type, r.url,
            COUNT(DISTINCT ri.ingredient_id) as total_ingredients,
            SUM(CASE
                WHEN LOWER(i.name) IN ({placeholders}) THEN 1
                ELSE 0
            END) as matched_ingredients
        FROM recipes r
        JOIN recipe_ingredients ri ON r.id = ri.recipe_id
        JOIN ingredients i ON ri.ingredient_id = i.id
        GROUP BY r.id
        ORDER BY matched_ingredients DESC, total_ingredients ASC
    """, [name.lower() for name in ingredient_names])

    recipes = []
    for row in cur.fetchall():
        recipe = dict(row)
        recipe_id = recipe['id']

        # Calculate match percentage
        if recipe['total_ingredients'] > 0:
            recipe['match_percentage'] = (recipe['matched_ingredients'] / recipe['total_ingredients']) * 100
        else:
            recipe['match_percentage'] = 0

        # Get all ingredients for this recipe
        cur.execute("""
            SELECT
                i.name as ingredient_name,
                i.category,
                ri.quantity,
                ri.unit,
                ri.notes,
                CASE
                    WHEN LOWER(i.name) IN ({}) THEN 1
                    ELSE 0
                END as is_available
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = ?
            ORDER BY is_available DESC, i.name
        """.format(placeholders), [name.lower() for name in ingredient_names] + [recipe_id])

        recipe['ingredients'] = [dict(ing) for ing in cur.fetchall()]
        recipes.append(recipe)

    conn.close()
    return recipes


def search_recipes_by_name(search_term: str) -> List[Dict[str, Any]]:
    """
    Search for recipes by name or description

    Args:
        search_term: The term to search for

    Returns:
        List of matching recipe dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    search_pattern = f"%{search_term}%"

    cur.execute("""
        SELECT
            id, name, description, instructions,
            prep_time, cook_time, servings, difficulty, cuisine_type, url
        FROM recipes
        WHERE LOWER(name) LIKE LOWER(?)
           OR LOWER(description) LIKE LOWER(?)
           OR LOWER(cuisine_type) LIKE LOWER(?)
        ORDER BY name
    """, (search_pattern, search_pattern, search_pattern))

    recipes = []
    for row in cur.fetchall():
        recipe = dict(row)
        recipe_id = recipe['id']

        # Get ingredients for this recipe
        cur.execute("""
            SELECT
                i.name as ingredient_name,
                i.category,
                ri.quantity,
                ri.unit,
                ri.notes
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = ?
            ORDER BY i.name
        """, (recipe_id,))

        recipe['ingredients'] = [dict(ing) for ing in cur.fetchall()]
        recipes.append(recipe)

    conn.close()
    return recipes
