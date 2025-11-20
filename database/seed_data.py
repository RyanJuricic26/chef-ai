"""
Sample data to seed the database with recipes
"""
import sqlite3
from init_db import init_database

def seed_recipes():
    """Add sample recipes to the database"""

    # Initialize database first
    init_database()

    conn = sqlite3.connect("database/app.db")
    cur = conn.cursor()

    # Sample recipes
    recipes = [
        {
            "name": "Classic Spaghetti Carbonara",
            "description": "Creamy Italian pasta dish with eggs, cheese, and pancetta",
            "instructions": "1. Cook spaghetti according to package directions. 2. Fry pancetta until crispy. 3. Mix eggs and parmesan. 4. Combine hot pasta with pancetta, then mix in egg mixture off heat. 5. Season with black pepper and serve.",
            "prep_time": 10,
            "cook_time": 20,
            "servings": 4,
            "difficulty": "medium",
            "cuisine_type": "Italian",
            "ingredients": [
                {"name": "spaghetti", "quantity": "400", "unit": "g", "category": "pasta"},
                {"name": "eggs", "quantity": "4", "unit": "whole", "category": "dairy"},
                {"name": "parmesan cheese", "quantity": "100", "unit": "g", "category": "dairy"},
                {"name": "pancetta", "quantity": "150", "unit": "g", "category": "meat"},
                {"name": "black pepper", "quantity": "1", "unit": "tsp", "category": "spice"},
            ]
        },
        {
            "name": "Chicken Stir Fry",
            "description": "Quick and healthy Asian-inspired chicken and vegetable stir fry",
            "instructions": "1. Cut chicken into strips and marinate in soy sauce. 2. Heat oil in wok. 3. Stir fry chicken until cooked. 4. Add vegetables and stir fry. 5. Add sauce and serve over rice.",
            "prep_time": 15,
            "cook_time": 15,
            "servings": 4,
            "difficulty": "easy",
            "cuisine_type": "Asian",
            "ingredients": [
                {"name": "chicken breast", "quantity": "500", "unit": "g", "category": "meat"},
                {"name": "soy sauce", "quantity": "3", "unit": "tbsp", "category": "condiment"},
                {"name": "bell peppers", "quantity": "2", "unit": "whole", "category": "vegetable"},
                {"name": "onion", "quantity": "1", "unit": "whole", "category": "vegetable"},
                {"name": "garlic", "quantity": "3", "unit": "cloves", "category": "vegetable"},
                {"name": "ginger", "quantity": "1", "unit": "tbsp", "category": "spice"},
                {"name": "vegetable oil", "quantity": "2", "unit": "tbsp", "category": "oil"},
                {"name": "rice", "quantity": "2", "unit": "cups", "category": "grain"},
            ]
        },
        {
            "name": "Caprese Salad",
            "description": "Simple Italian salad with tomatoes, mozzarella, and basil",
            "instructions": "1. Slice tomatoes and mozzarella. 2. Arrange on plate alternating tomato and cheese. 3. Add fresh basil leaves. 4. Drizzle with olive oil and balsamic vinegar. 5. Season with salt and pepper.",
            "prep_time": 10,
            "cook_time": 0,
            "servings": 2,
            "difficulty": "easy",
            "cuisine_type": "Italian",
            "ingredients": [
                {"name": "tomatoes", "quantity": "4", "unit": "whole", "category": "vegetable"},
                {"name": "mozzarella cheese", "quantity": "250", "unit": "g", "category": "dairy"},
                {"name": "fresh basil", "quantity": "1", "unit": "bunch", "category": "herb"},
                {"name": "olive oil", "quantity": "3", "unit": "tbsp", "category": "oil"},
                {"name": "balsamic vinegar", "quantity": "2", "unit": "tbsp", "category": "condiment"},
                {"name": "salt", "quantity": "1", "unit": "tsp", "category": "spice"},
                {"name": "black pepper", "quantity": "1", "unit": "tsp", "category": "spice"},
            ]
        },
        {
            "name": "Beef Tacos",
            "description": "Mexican-style tacos with seasoned ground beef",
            "instructions": "1. Brown ground beef in pan. 2. Add taco seasoning and water. 3. Simmer until thickened. 4. Warm tortillas. 5. Assemble tacos with beef and toppings.",
            "prep_time": 10,
            "cook_time": 15,
            "servings": 4,
            "difficulty": "easy",
            "cuisine_type": "Mexican",
            "ingredients": [
                {"name": "ground beef", "quantity": "500", "unit": "g", "category": "meat"},
                {"name": "taco seasoning", "quantity": "2", "unit": "tbsp", "category": "spice"},
                {"name": "tortillas", "quantity": "8", "unit": "whole", "category": "grain"},
                {"name": "lettuce", "quantity": "1", "unit": "cup", "category": "vegetable"},
                {"name": "tomatoes", "quantity": "2", "unit": "whole", "category": "vegetable"},
                {"name": "cheddar cheese", "quantity": "200", "unit": "g", "category": "dairy"},
                {"name": "sour cream", "quantity": "1", "unit": "cup", "category": "dairy"},
            ]
        },
        {
            "name": "Mushroom Risotto",
            "description": "Creamy Italian rice dish with mushrooms and parmesan",
            "instructions": "1. Sauté mushrooms and set aside. 2. Toast rice in butter. 3. Add wine and let absorb. 4. Gradually add warm broth, stirring constantly. 5. Stir in mushrooms, butter, and parmesan. 6. Season and serve.",
            "prep_time": 15,
            "cook_time": 30,
            "servings": 4,
            "difficulty": "hard",
            "cuisine_type": "Italian",
            "ingredients": [
                {"name": "arborio rice", "quantity": "300", "unit": "g", "category": "grain"},
                {"name": "mushrooms", "quantity": "400", "unit": "g", "category": "vegetable"},
                {"name": "chicken broth", "quantity": "1", "unit": "liter", "category": "liquid"},
                {"name": "white wine", "quantity": "150", "unit": "ml", "category": "liquid"},
                {"name": "onion", "quantity": "1", "unit": "whole", "category": "vegetable"},
                {"name": "garlic", "quantity": "2", "unit": "cloves", "category": "vegetable"},
                {"name": "parmesan cheese", "quantity": "100", "unit": "g", "category": "dairy"},
                {"name": "butter", "quantity": "50", "unit": "g", "category": "dairy"},
                {"name": "olive oil", "quantity": "2", "unit": "tbsp", "category": "oil"},
            ]
        }
    ]

    for recipe_data in recipes:
        # Insert recipe
        cur.execute("""
            INSERT INTO recipes (name, description, instructions, prep_time, cook_time, servings, difficulty, cuisine_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recipe_data["name"],
            recipe_data["description"],
            recipe_data["instructions"],
            recipe_data["prep_time"],
            recipe_data["cook_time"],
            recipe_data["servings"],
            recipe_data["difficulty"],
            recipe_data["cuisine_type"]
        ))

        recipe_id = cur.lastrowid

        # Insert ingredients and link to recipe
        for ing_data in recipe_data["ingredients"]:
            # Insert or get ingredient
            cur.execute("""
                INSERT OR IGNORE INTO ingredients (name, category)
                VALUES (?, ?)
            """, (ing_data["name"], ing_data["category"]))

            cur.execute("SELECT id FROM ingredients WHERE name = ?", (ing_data["name"],))
            ingredient_id = cur.fetchone()[0]

            # Link ingredient to recipe
            cur.execute("""
                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit)
                VALUES (?, ?, ?, ?)
            """, (recipe_id, ingredient_id, ing_data["quantity"], ing_data["unit"]))

    conn.commit()
    conn.close()
    print(f"Successfully added {len(recipes)} recipes to the database!")


if __name__ == "__main__":
    seed_recipes()
