# sql_queries.py
import sqlite3
from typing import Dict, Any, Optional
from .config import DB_PATH


def save_recipe_to_database(recipe_data: Dict[str, Any]) -> Optional[int]:
    """
    Save a recipe to the database along with its ingredients.
    
    Args:
        recipe_data: Recipe dictionary with all fields and ingredients list
        
    Returns:
        Recipe ID if successful, None if error
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Insert recipe
        cur.execute("""
            INSERT INTO recipes (
                name, description, instructions,
                prep_time, cook_time, servings,
                difficulty, cuisine_type, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recipe_data.get("name", ""),
            recipe_data.get("description"),
            recipe_data.get("instructions", ""),
            recipe_data.get("prep_time", 0),
            recipe_data.get("cook_time", 0),
            recipe_data.get("servings"),
            recipe_data.get("difficulty"),
            recipe_data.get("cuisine_type"),
            recipe_data.get("url", "")
        ))
        
        recipe_id = cur.lastrowid
        
        # Process ingredients
        ingredients = recipe_data.get("ingredients", [])
        for ing in ingredients:
            ingredient_name = ing.get("name", "").strip()
            if not ingredient_name:
                continue
            
            # Get or create ingredient
            cur.execute("""
                SELECT id FROM ingredients WHERE LOWER(name) = LOWER(?)
            """, (ingredient_name,))
            
            result = cur.fetchone()
            if result:
                ingredient_id = result[0]
                # Update category if provided and different
                if ing.get("category"):
                    cur.execute("""
                        UPDATE ingredients SET category = ? WHERE id = ?
                    """, (ing.get("category"), ingredient_id))
            else:
                # Insert new ingredient
                cur.execute("""
                    INSERT INTO ingredients (name, category)
                    VALUES (?, ?)
                """, (ingredient_name, ing.get("category")))
                ingredient_id = cur.lastrowid
            
            # Link recipe to ingredient
            cur.execute("""
                INSERT OR REPLACE INTO recipe_ingredients
                (recipe_id, ingredient_id, quantity, unit)
                VALUES (?, ?, ?, ?)
            """, (
                recipe_id,
                ingredient_id,
                ing.get("quantity"),
                ing.get("unit")
            ))
        
        conn.commit()
        return recipe_id
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise Exception(f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


def delete_recipe_from_database(recipe_id: int) -> bool:
    """
    Delete a recipe from the database.
    Due to CASCADE constraints, this will also delete:
    - All recipe_ingredients entries for this recipe
    - All starred_recipes entries for this recipe
    
    Args:
        recipe_id: ID of the recipe to delete
        
    Returns:
        True if successful, False if recipe not found
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check if recipe exists
        cur.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
        if not cur.fetchone():
            return False
        
        # Delete recipe (CASCADE will handle related records)
        cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise Exception(f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()
