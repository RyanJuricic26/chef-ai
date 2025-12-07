import os
import sys
import streamlit as st
from dotenv import load_dotenv

# --- Fix import path: add project root to Python path ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# --- Load environment variables from the project root .env ---
load_dotenv(os.path.join(ROOT_DIR, ".env"))

st.set_page_config(page_title="Catalog Recipe", page_icon="📥", layout="centered")

st.title("📥 Catalog Recipe")
st.write("Add a new recipe to your database by providing a recipe URL.")

# --- Try importing catalog_recipe graph ---
try:
    from agents.catalog_recipe.graph import graph, AgentState
except Exception as e:
    st.error("❌ Error importing agents.catalog_recipe.graph")
    st.exception(e)
    st.stop()

# Example URLs for testing
st.markdown("### 📝 How it works")
st.info("""
1. **Enter a recipe URL** - The agent will fetch the webpage
2. **JSON-LD Extraction** - First tries to extract structured recipe data (preferred method)
3. **LLM Fallback** - If JSON-LD isn't available, uses AI to extract recipe information
4. **Validation** - Ensures all required fields are present
5. **Save to Database** - Adds the recipe to your recipe library
""")

# Example recipe URLs
with st.expander("💡 Example Recipe URLs to Test"):
    st.markdown("""
    Try these recipe URLs that typically have JSON-LD structured data:
    - AllRecipes: https://www.allrecipes.com/recipe/...
    - Food Network: https://www.foodnetwork.com/recipes/...
    - BBC Good Food: https://www.bbcgoodfood.com/recipes/...
    - Serious Eats: https://www.seriouseats.com/...
    
    Or any recipe website - the agent will try JSON-LD first, then fall back to LLM extraction.
    """)

# Recipe URL input
recipe_url = st.text_input(
    "Recipe URL",
    placeholder="https://example.com/recipe/chocolate-chip-cookies",
    help="Enter the full URL of the recipe webpage you want to catalog"
)

# Initialize session state for results
if "catalog_result" not in st.session_state:
    st.session_state.catalog_result = None
if "catalog_error" not in st.session_state:
    st.session_state.catalog_error = None

# Catalog button
if st.button("📥 Catalog Recipe", type="primary"):
    if not recipe_url or not recipe_url.strip():
        st.warning("Please enter a recipe URL first.")
    elif not recipe_url.startswith(("http://", "https://")):
        st.warning("Please enter a valid URL starting with http:// or https://")
    else:
        with st.spinner("Cataloging recipe... This may take a moment."):
            try:
                # Create initial state
                state = AgentState(recipe_url=recipe_url.strip())
                
                # Invoke the graph
                result = graph.invoke(state)
                
                # Store results
                st.session_state.catalog_result = result
                st.session_state.catalog_error = None
                
            except Exception as e:
                st.error("❌ Error running the catalog recipe agent.")
                st.exception(e)
                st.session_state.catalog_error = str(e)
                st.session_state.catalog_result = None

# Display results
if st.session_state.catalog_result:
    result = st.session_state.catalog_result
    
    st.markdown("---")
    st.subheader("📊 Catalog Results")
    
    # Success/Failure indicator
    if result.get("success"):
        st.success(f"✅ Recipe successfully cataloged!")
        st.balloons()
        
        # Show recipe ID
        recipe_id = result.get("recipe_id")
        if recipe_id:
            st.info(f"**Recipe ID:** {recipe_id}")
        
        # Show extracted recipe data
        recipe_data = result.get("recipe_data", {})
        if recipe_data:
            st.markdown("### 📋 Extracted Recipe Data")
            
            # Basic info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Name", recipe_data.get("name", "N/A"))
            with col2:
                extraction_method = result.get("extraction_method", "unknown")
                method_emoji = "📊" if extraction_method == "json_ld" else "🤖"
                st.metric("Method", f"{method_emoji} {extraction_method}")
            with col3:
                st.metric("Difficulty", recipe_data.get("difficulty", "N/A") or "N/A")
            
            # Description
            if recipe_data.get("description"):
                st.markdown(f"**Description:** {recipe_data.get('description')}")
            
            # Times and servings
            col1, col2, col3 = st.columns(3)
            with col1:
                prep_time = recipe_data.get("prep_time", 0) or 0
                st.metric("Prep Time", f"{prep_time} min")
            with col2:
                cook_time = recipe_data.get("cook_time", 0) or 0
                st.metric("Cook Time", f"{cook_time} min")
            with col3:
                servings = recipe_data.get("servings")
                st.metric("Servings", servings or "N/A")
            
            # Cuisine type
            if recipe_data.get("cuisine_type"):
                st.markdown(f"**Cuisine:** {recipe_data.get('cuisine_type')}")
            
            # Ingredients
            ingredients = recipe_data.get("ingredients", [])
            if ingredients:
                st.markdown("### 🧂 Ingredients")
                for ing in ingredients:
                    qty = ing.get("quantity", "")
                    unit = ing.get("unit", "")
                    name = ing.get("name", "")
                    category = ing.get("category", "")
                    
                    ing_text = f"- {qty} {unit} {name}".strip()
                    if category:
                        ing_text += f" *({category})*"
                    st.markdown(ing_text)
            
            # Instructions
            if recipe_data.get("instructions"):
                st.markdown("### 👩‍🍳 Instructions")
                st.text_area(
                    "Recipe Instructions",
                    recipe_data.get("instructions"),
                    height=200,
                    disabled=True,
                    label_visibility="collapsed"
                )
            
            # Source URL
            if recipe_data.get("url"):
                st.markdown(f"**Source:** [View original recipe]({recipe_data.get('url')})")
            
            st.success("🎉 You can now view this recipe in the Recipe Library page!")
            if st.button("📚 Go to Recipe Library"):
                st.switch_page("pages/1_Recipe_Library.py")
    
    else:
        # Error case
        st.error("❌ Failed to catalog recipe")
        error_message = result.get("error_message", "Unknown error")
        st.error(f"**Error:** {error_message}")
        
        # Show partial data if available
        recipe_data = result.get("recipe_data")
        if recipe_data:
            st.warning("⚠️ Some data was extracted but validation/saving failed:")
            st.json(recipe_data)

# Display error if any
if st.session_state.catalog_error:
    st.error(f"**Exception:** {st.session_state.catalog_error}")

# Debug section (collapsible)
with st.expander("🔍 Debug Information"):
    if st.session_state.catalog_result:
        st.json(st.session_state.catalog_result)
    
    st.markdown("### Workflow Steps")
    st.info("""
    The catalog recipe agent follows these steps:
    1. **fetch_webpage** - Downloads HTML from the URL
    2. **parse_json_ld** - Attempts to extract JSON-LD Recipe schema
    3. **extract_with_llm** - Falls back to LLM extraction if JSON-LD not found
    4. **validate_recipe_data** - Validates all required fields
    5. **save_to_database** - Saves to SQLite database
    """)

# Footer
st.markdown("---")
st.caption("💡 Tip: Recipes with JSON-LD structured data will be extracted more accurately and quickly!")

