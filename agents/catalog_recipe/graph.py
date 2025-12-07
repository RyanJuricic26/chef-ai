# graph.py
from typing import Any, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
import json

# local imports
from .config import OPENAI_API_KEY, OPENAI_MODEL, REQUEST_TIMEOUT, USER_AGENT, DB_PATH
from .catalog_utils import (
    fetch_html_content,
    parse_json_ld_from_html,
    extract_recipe_from_json_ld,
    clean_html_for_llm,
    infer_difficulty,
    strip_html_tags,
    format_instructions
)
from .prompts import EXTRACT_RECIPE_FROM_HTML_PROMPT
from .sql_queries import save_recipe_to_database


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
    """
    try:
        html_content = fetch_html_content(
            state.recipe_url,
            timeout=REQUEST_TIMEOUT,
            user_agent=USER_AGENT
        )
        state.html_content = html_content
    except Exception as e:
        state.error_message = f"Failed to fetch webpage: {str(e)}"
    
    return state


def parse_json_ld(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Attempt to parse JSON-LD Recipe schema from the HTML content.
    """
    if not state.html_content:
        state.error_message = "No HTML content available"
        return state
    
    try:
        json_ld_data = parse_json_ld_from_html(state.html_content)
        
        if json_ld_data:
            state.json_ld_data = json_ld_data
            recipe_data = extract_recipe_from_json_ld(json_ld_data, state.recipe_url)
            state.recipe_data = recipe_data
            state.extraction_method = "json_ld"
            
            # Infer difficulty if not set
            if not state.recipe_data.get("difficulty"):
                state.recipe_data["difficulty"] = infer_difficulty(
                    state.recipe_data.get("instructions", ""),
                    state.recipe_data.get("prep_time", 0),
                    state.recipe_data.get("cook_time", 0)
                )
        else:
            state.json_ld_data = None
    except Exception as e:
        state.error_message = f"Failed to parse JSON-LD: {str(e)}"
        state.json_ld_data = None
    
    return state


def extract_with_llm(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Use LLM to extract recipe information from HTML when JSON-LD is not available.
    """
    if not state.html_content:
        state.error_message = "No HTML content available"
        return state
    
    if not OPENAI_API_KEY:
        state.error_message = "OpenAI API key not configured"
        return state
    
    try:
        # Clean HTML for LLM
        cleaned_html = clean_html_for_llm(state.html_content)
        
        # Initialize LLM
        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0
        )
        
        # Create prompt chain
        chain = EXTRACT_RECIPE_FROM_HTML_PROMPT | llm
        
        # Get LLM response
        response = chain.invoke({"html_content": cleaned_html})
        
        # Extract JSON from response
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        recipe_data = json.loads(content)
        
        # Clean HTML tags from all text fields
        if "name" in recipe_data and recipe_data["name"]:
            recipe_data["name"] = strip_html_tags(str(recipe_data["name"]))
        if "description" in recipe_data and recipe_data["description"]:
            recipe_data["description"] = strip_html_tags(str(recipe_data["description"]))
        if "instructions" in recipe_data and recipe_data["instructions"]:
            cleaned_instructions = strip_html_tags(str(recipe_data["instructions"]))
            formatted = format_instructions(cleaned_instructions)
            # Ensure we don't lose the instructions - use formatted if available, otherwise use cleaned
            recipe_data["instructions"] = formatted if formatted else cleaned_instructions
        
        # Clean ingredients
        if "ingredients" in recipe_data and isinstance(recipe_data["ingredients"], list):
            for ing in recipe_data["ingredients"]:
                if isinstance(ing, dict):
                    if "name" in ing:
                        ing["name"] = strip_html_tags(str(ing["name"]))
                    if "quantity" in ing:
                        ing["quantity"] = strip_html_tags(str(ing["quantity"])) if ing["quantity"] else ""
                    if "unit" in ing:
                        ing["unit"] = strip_html_tags(str(ing["unit"])) if ing["unit"] else ""
        
        # Ensure URL is set
        recipe_data["url"] = state.recipe_url
        
        # Ensure required fields
        if "name" not in recipe_data or not recipe_data["name"]:
            state.error_message = "LLM extraction failed: missing recipe name"
            return state
        
        if "instructions" not in recipe_data or not recipe_data["instructions"]:
            state.error_message = "LLM extraction failed: missing instructions"
            return state
        
        if "ingredients" not in recipe_data or not recipe_data["ingredients"]:
            state.error_message = "LLM extraction failed: missing ingredients"
            return state
        
        # Set defaults
        if "prep_time" not in recipe_data:
            recipe_data["prep_time"] = 0
        if "cook_time" not in recipe_data:
            recipe_data["cook_time"] = 0
        if "difficulty" not in recipe_data or not recipe_data["difficulty"]:
            recipe_data["difficulty"] = infer_difficulty(
                recipe_data.get("instructions", ""),
                recipe_data.get("prep_time", 0),
                recipe_data.get("cook_time", 0)
            )
        
        state.recipe_data = recipe_data
        state.extraction_method = "llm_html"
        
    except json.JSONDecodeError as e:
        state.error_message = f"Failed to parse LLM response as JSON: {str(e)}"
    except Exception as e:
        state.error_message = f"LLM extraction failed: {str(e)}"
    
    return state


def validate_recipe_data(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Validate that all required recipe fields are present and properly formatted.
    """
    if not state.recipe_data:
        state.error_message = "No recipe data to validate"
        return state
    
    recipe_data = state.recipe_data
    
    # Check required fields
    if not recipe_data.get("name"):
        state.error_message = "Validation failed: recipe name is required"
        return state
    
    if not recipe_data.get("instructions"):
        state.error_message = "Validation failed: instructions are required"
        return state
    
    if not recipe_data.get("ingredients") or not isinstance(recipe_data["ingredients"], list) or len(recipe_data["ingredients"]) == 0:
        state.error_message = "Validation failed: at least one ingredient is required"
        return state
    
    # Validate and set defaults
    if "prep_time" not in recipe_data or recipe_data["prep_time"] is None:
        recipe_data["prep_time"] = 0
    else:
        recipe_data["prep_time"] = max(0, int(recipe_data["prep_time"]))
    
    if "cook_time" not in recipe_data or recipe_data["cook_time"] is None:
        recipe_data["cook_time"] = 0
    else:
        recipe_data["cook_time"] = max(0, int(recipe_data["cook_time"]))
    
    if "servings" in recipe_data and recipe_data["servings"] is not None:
        recipe_data["servings"] = max(1, int(recipe_data["servings"]))
    
    # Validate difficulty
    if "difficulty" not in recipe_data or recipe_data["difficulty"] not in ["easy", "medium", "hard"]:
        recipe_data["difficulty"] = infer_difficulty(
            recipe_data.get("instructions", ""),
            recipe_data.get("prep_time", 0),
            recipe_data.get("cook_time", 0)
        )
    
    # Ensure URL is set
    recipe_data["url"] = state.recipe_url
    
    # Validate ingredients
    valid_ingredients = []
    for ing in recipe_data["ingredients"]:
        if isinstance(ing, dict) and ing.get("name"):
            # Ensure all ingredient fields exist
            valid_ing = {
                "name": str(ing.get("name", "")).strip(),
                "quantity": str(ing.get("quantity", "")).strip() if ing.get("quantity") else "",
                "unit": str(ing.get("unit", "")).strip() if ing.get("unit") else "",
                "category": str(ing.get("category", "other")).strip() if ing.get("category") else "other"
            }
            if valid_ing["name"]:
                valid_ingredients.append(valid_ing)
    
    if not valid_ingredients:
        state.error_message = "Validation failed: no valid ingredients found"
        return state
    
    recipe_data["ingredients"] = valid_ingredients
    
    # Set optional defaults
    if "description" not in recipe_data:
        recipe_data["description"] = None
    
    if "cuisine_type" not in recipe_data:
        recipe_data["cuisine_type"] = None
    
    state.recipe_data = recipe_data
    return state


def save_to_database(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Save the validated recipe data to the SQLite database.
    """
    if not state.recipe_data:
        state.error_message = "No recipe data to save"
        state.success = False
        return state
    
    try:
        recipe_id = save_recipe_to_database(state.recipe_data)
        if recipe_id:
            state.recipe_id = recipe_id
            state.success = True
        else:
            state.error_message = "Failed to save recipe to database"
            state.success = False
    except Exception as e:
        state.error_message = f"Database save failed: {str(e)}"
        state.success = False
    
    return state


# Conditional routing functions

def route_after_json_ld(state: AgentState) -> str:
    """
    Route to LLM extraction if JSON-LD parsing failed, otherwise validate.
    """
    if state.error_message:
        return END
    
    if state.json_ld_data is None or not state.recipe_data:
        return "extract_with_llm"
    else:
        return "validate_recipe_data"


def route_after_validation(state: AgentState) -> str:
    """
    Route to database save if validation passed, otherwise end with error.
    """
    if state.error_message:
        return END
    
    if state.recipe_data:
        return "save_to_database"
    else:
        return END


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
        "validate_recipe_data": "validate_recipe_data",
        END: END
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
