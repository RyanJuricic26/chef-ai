import os
import sys
import sqlite3

import streamlit as st
from dotenv import load_dotenv

# --- Fix import path: add project root to Python path ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# --- Load environment variables from the project root .env ---
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from agents.fetch_recipes.config import DB_PATH

st.set_page_config(page_title="Recipe Library", page_icon="📚", layout="wide")

st.title("📚 Recipe Library")
st.write("Browse all your recipes and star your favorites!")

def load_starred_recipes():
    """Load starred recipes from database"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get all starred recipe IDs for default user (user_id=1)
    cur.execute("SELECT recipe_id FROM starred_recipes WHERE user_id = 1")
    starred_ids = {row[0] for row in cur.fetchall()}

    conn.close()
    return starred_ids


def save_star_to_db(recipe_id, is_starred):
    """Save or remove star in database"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if is_starred:
        # Add star
        cur.execute("""
            INSERT OR IGNORE INTO starred_recipes (recipe_id, user_id)
            VALUES (?, 1)
        """, (recipe_id,))
    else:
        # Remove star
        cur.execute("""
            DELETE FROM starred_recipes
            WHERE recipe_id = ? AND user_id = 1
        """, (recipe_id,))

    conn.commit()
    conn.close()


# Initialize session state for starred recipes
if "starred_recipes" not in st.session_state:
    # Load starred recipes from database
    st.session_state.starred_recipes = load_starred_recipes()


def get_all_recipes():
    """Fetch all recipes from the database with their details"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id, name, description, instructions,
            prep_time, cook_time, servings, difficulty,
            cuisine_type, url, created_at
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


def toggle_star(recipe_id):
    """Toggle starred status for a recipe"""
    if recipe_id in st.session_state.starred_recipes:
        st.session_state.starred_recipes.remove(recipe_id)
        save_star_to_db(recipe_id, False)
    else:
        st.session_state.starred_recipes.add(recipe_id)
        save_star_to_db(recipe_id, True)


# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")

    # Show starred only
    show_starred_only = st.checkbox("⭐ Show starred only", value=False)

    st.markdown("---")

    # Difficulty filter
    difficulty_filter = st.multiselect(
        "Difficulty",
        options=["easy", "medium", "hard"],
        default=[]
    )

    # Cuisine filter
    cuisine_filter = st.multiselect(
        "Cuisine Type",
        options=["Italian", "Asian", "American", "Mexican", "French", "Other"],
        default=[]
    )

    # Time filter
    max_time = st.slider(
        "Max Total Time (minutes)",
        min_value=0,
        max_value=180,
        value=180,
        step=15
    )

    st.markdown("---")
    st.caption(f"⭐ {len(st.session_state.starred_recipes)} recipes starred")

# Fetch all recipes
try:
    all_recipes = get_all_recipes()
except Exception as e:
    st.error(f"❌ Error loading recipes: {str(e)}")
    st.stop()

# Apply filters
filtered_recipes = all_recipes

# Filter by starred
if show_starred_only:
    filtered_recipes = [r for r in filtered_recipes if r['id'] in st.session_state.starred_recipes]

# Filter by difficulty
if difficulty_filter:
    filtered_recipes = [r for r in filtered_recipes if r.get('difficulty') in difficulty_filter]

# Filter by cuisine
if cuisine_filter:
    filtered_recipes = [r for r in filtered_recipes if r.get('cuisine_type') in cuisine_filter]

# Filter by time
filtered_recipes = [
    r for r in filtered_recipes
    if (r.get('prep_time') or 0) + (r.get('cook_time') or 0) <= max_time
]

# Display count
st.markdown(f"**Showing {len(filtered_recipes)} of {len(all_recipes)} recipes**")

# Search box
search_query = st.text_input("🔎 Search recipes by name or ingredient", "")

if search_query:
    search_lower = search_query.lower()
    filtered_recipes = [
        r for r in filtered_recipes
        if search_lower in r['name'].lower()
        or search_lower in r.get('description', '').lower()
        or any(search_lower in ing['ingredient_name'].lower() for ing in r.get('ingredients', []))
    ]
    st.caption(f"Found {len(filtered_recipes)} recipes matching '{search_query}'")

st.markdown("---")

# Display recipes in a grid
if not filtered_recipes:
    st.info("No recipes found. Try adjusting your filters or add more recipes!")
else:
    # Create columns for grid layout
    cols_per_row = 2
    rows = [filtered_recipes[i:i + cols_per_row] for i in range(0, len(filtered_recipes), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)

        for idx, recipe in enumerate(row):
            with cols[idx]:
                recipe_id = recipe['id']
                is_starred = recipe_id in st.session_state.starred_recipes

                # Recipe card
                with st.container(border=True):
                    # Header with star button
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"### {recipe['name']}")
                    with col2:
                        star_icon = "⭐" if is_starred else "☆"
                        if st.button(star_icon, key=f"star_{recipe_id}"):
                            toggle_star(recipe_id)
                            st.rerun()

                    # Description
                    if recipe.get('description'):
                        st.write(recipe['description'])

                    # Metadata
                    total_time = (recipe.get('prep_time') or 0) + (recipe.get('cook_time') or 0)

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.caption(f"⏱️ {total_time} min")
                    with col_b:
                        st.caption(f"🍽️ {recipe.get('servings', 'N/A')}")
                    with col_c:
                        difficulty = recipe.get('difficulty', 'N/A')
                        emoji = {"easy": "😊", "medium": "🤔", "hard": "💪"}.get(difficulty, "❓")
                        st.caption(f"{emoji} {difficulty.title()}")

                    # Cuisine badge
                    if recipe.get('cuisine_type'):
                        st.markdown(f"🌍 *{recipe['cuisine_type']}*")

                    # Expandable details
                    with st.expander("📖 View Details"):
                        # Ingredients
                        st.markdown("**Ingredients:**")
                        for ing in recipe.get('ingredients', []):
                            qty = ing.get('quantity') or ''
                            unit = ing.get('unit') or ''
                            name = ing.get('ingredient_name') or ''
                            st.markdown(f"- {qty} {unit} {name}".strip())

                        # Instructions
                        st.markdown("**Instructions:**")
                        st.write(recipe.get('instructions', 'No instructions available.'))

                        # URL if available
                        if recipe.get('url'):
                            st.markdown(f"**Source:** [View original recipe]({recipe['url']})")
                        
                        # Delete button with confirmation
                        st.markdown("---")
                        delete_key = f"delete_{recipe_id}"
                        confirm_key = f"confirm_delete_{recipe_id}"
                        
                        # Initialize confirmation state
                        if confirm_key not in st.session_state:
                            st.session_state[confirm_key] = False
                        
                        if st.session_state[confirm_key]:
                            # Show confirmation
                            st.warning(f"⚠️ Are you sure you want to delete '{recipe['name']}'?")
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Confirm Delete", key=f"confirm_{recipe_id}", type="primary"):
                                    try:
                                        from agents.catalog_recipe.sql_queries import delete_recipe_from_database
                                        success = delete_recipe_from_database(recipe_id)
                                        if success:
                                            st.session_state[confirm_key] = False
                                            st.success(f"✅ Recipe '{recipe['name']}' deleted successfully!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Recipe not found or could not be deleted.")
                                            st.session_state[confirm_key] = False
                                    except Exception as e:
                                        st.error(f"❌ Error deleting recipe: {str(e)}")
                                        st.session_state[confirm_key] = False
                            with col2:
                                if st.button("❌ Cancel", key=f"cancel_{recipe_id}"):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                        else:
                            # Show delete button
                            if st.button("🗑️ Delete Recipe", key=delete_key, type="secondary"):
                                st.session_state[confirm_key] = True
                                st.rerun()

# Footer
st.markdown("---")
st.caption("💡 Tip: Star your favorite recipes to quickly find them later!")
