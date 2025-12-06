# graph.py
from typing import Any, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# local imports
from .config import OPENAI_API_KEY, OPENAI_MODEL


# Define the Agent State
class AgentState(BaseModel):
    """Pydantic model for LangGraph - Recipe Catalog Agent"""

    # Input
    recipe_url: str

    # Fetched data
    html_content: str | None = None
    json_ld_data: dict[str, Any] | None = None

    # Extraction method used
    extraction_method: Literal["json_ld", "llm_html"] | None = None

    # Extracted recipe data
    recipe_data: dict[str, Any] | None = Field(default_factory=dict)
    # Expected fields in recipe_data:
    # {
    #     "name": str,
    #     "description": str,
    #     "instructions": str,
    #     "prep_time": int (minutes),
    #     "cook_time": int (minutes),
    #     "servings": int,
    #     "difficulty": str ("easy", "medium", "hard"),
    #     "cuisine_type": str,
    #     "url": str,
    #     "ingredients": [
    #         {
    #             "name": str,
    #             "quantity": str,
    #             "unit": str,
    #             "category": str
    #         }
    #     ]
    # }

    # Database operation results
    recipe_id: int | None = None
    success: bool = False
    error_message: str | None = None


# Define the Nodes

def fetch_webpage(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Fetch the webpage HTML content from the provided recipe URL.

    This node should:
    1. Make an HTTP request to state.recipe_url
    2. Store the HTML content in state.html_content
    3. Handle any network errors and set state.error_message if needed
    """
    pass


def parse_json_ld(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Attempt to parse JSON-LD Recipe schema from the HTML content.

    This node should:
    1. Search for <script type="application/ld+json"> tags in state.html_content
    2. Parse the JSON and look for @type: "Recipe"
    3. If found, store the structured data in state.json_ld_data
    4. Extract recipe information according to schema.org Recipe specification
    5. Populate state.recipe_data with extracted information
    6. Set state.extraction_method = "json_ld"
    7. If not found or parsing fails, leave state.json_ld_data as None

    JSON-LD fields to extract:
    - name
    - description
    - recipeInstructions (can be array or string)
    - prepTime (ISO 8601 duration, convert to minutes)
    - cookTime (ISO 8601 duration, convert to minutes)
    - recipeYield (servings)
    - recipeIngredient (array of strings)
    - recipeCuisine
    """
    pass


def extract_with_llm(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Use LLM to extract recipe information from HTML when JSON-LD is not available.

    This node should:
    1. Take state.html_content and clean it (remove scripts, styles, etc.)
    2. Use an LLM prompt to extract recipe information
    3. Ask the LLM to structure the response as JSON with all required fields
    4. Parse the LLM response and populate state.recipe_data
    5. Set state.extraction_method = "llm_html"
    6. Infer difficulty level based on instructions complexity if not explicit
    7. Categorize ingredients (meat, vegetable, dairy, spice, grain, etc.)

    The LLM should extract:
    - Recipe name
    - Description
    - Step-by-step instructions
    - Prep time (in minutes)
    - Cook time (in minutes)
    - Number of servings
    - Difficulty level (easy/medium/hard)
    - Cuisine type
    - Ingredients list with quantities, units, and categories
    """
    pass


def validate_recipe_data(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Validate that all required recipe fields are present and properly formatted.

    This node should:
    1. Check that state.recipe_data contains all required fields:
       - name (required)
       - instructions (required)
       - ingredients (required, non-empty list)
    2. Validate data types and ranges:
       - times should be positive integers
       - difficulty should be 'easy', 'medium', or 'hard'
       - servings should be positive
    3. Set default values for optional fields if missing
    4. Ensure state.recipe_data["url"] is set to state.recipe_url
    5. If validation fails, set state.error_message with details
    """
    pass


def save_to_database(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Save the validated recipe data to the SQLite database.

    This node should:
    1. Connect to the database
    2. Insert the recipe into the recipes table
    3. Get the recipe_id from the insert
    4. For each ingredient:
       a. Insert or get the ingredient from ingredients table
       b. Link to recipe in recipe_ingredients table with quantity/unit
    5. Store the recipe_id in state.recipe_id
    6. Set state.success = True on successful save
    7. On error, set state.error_message and state.success = False
    8. Commit the transaction and close the connection
    """
    pass


# Conditional routing functions

def route_after_json_ld(state: AgentState) -> str:
    """
    Route to LLM extraction if JSON-LD parsing failed, otherwise validate.

    Returns:
        "extract_with_llm" if state.json_ld_data is None
        "validate_recipe_data" if JSON-LD data was successfully extracted
    """
    pass


def route_after_validation(state: AgentState) -> str:
    """
    Route to database save if validation passed, otherwise end with error.

    Returns:
        "save_to_database" if state.recipe_data is valid and no error_message
        END if validation failed
    """
    pass


# Build the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("fetch_webpage", fetch_webpage)
builder.add_node("parse_json_ld", parse_json_ld)
builder.add_node("extract_with_llm", extract_with_llm)
builder.add_node("validate_recipe_data", validate_recipe_data)
builder.add_node("save_to_database", save_to_database)

# Add edges
builder.add_edge(START, "fetch_webpage")
builder.add_edge("fetch_webpage", "parse_json_ld")

# Conditional routing after JSON-LD parsing
builder.add_conditional_edges(
    "parse_json_ld",
    route_after_json_ld,
    {
        "extract_with_llm": "extract_with_llm",
        "validate_recipe_data": "validate_recipe_data"
    }
)

# LLM extraction goes to validation
builder.add_edge("extract_with_llm", "validate_recipe_data")

# Conditional routing after validation
builder.add_conditional_edges(
    "validate_recipe_data",
    route_after_validation,
    {
        "save_to_database": "save_to_database",
        END: END
    }
)

# Save to database ends the workflow
builder.add_edge("save_to_database", END)

# Compile the graph
graph = builder.compile()
