import sqlite3
import os

def init_database():
    """Initialize the database with recipes and ingredients tables"""

    # Ensure database directory exists
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect("database/app.db")
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # Recipes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        instructions TEXT NOT NULL,
        prep_time INTEGER,
        cook_time INTEGER,
        servings INTEGER,
        difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
        cuisine_type TEXT,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Ingredients table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT
    )
    """)

    # Recipe-Ingredient junction table (many-to-many relationship)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS recipe_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_id INTEGER NOT NULL,
        quantity TEXT,
        unit TEXT,
        notes TEXT,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
        UNIQUE(recipe_id, ingredient_id)
    )
    """)

    # Starred recipes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS starred_recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        user_id INTEGER DEFAULT 1,
        starred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(recipe_id, user_id)
    )
    """)

    # Create indexes for better query performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipe_name ON recipes(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ingredient_name ON ingredients(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient ON recipe_ingredients(ingredient_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_starred_recipes_user ON starred_recipes(user_id)")

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_database()
