# graph.py
from typing import Any, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# local imports
from .config import OPENAI_API_KEY, ROUTER_MODEL
from .prompts import ROUTE_INTENT_PROMPT


# Define the Agent State
class OrchestratorState(BaseModel):
    """Pydantic model for Orchestrator Agent"""

    # Input
    user_input: str

    # Routing
    intent: Literal["fetch_recipes", "catalog_recipe"] | None = None
    recipe_url: str | None = None  # Extracted URL for catalog_recipe

    # Subgraph results
    fetch_recipes_result: dict[str, Any] | None = None
    catalog_recipe_result: dict[str, Any] | None = None

    # Final output
    response: str = ""
    success: bool = False
    error_message: str | None = None


# Define the Nodes

def classify_intent(state: OrchestratorState, config: RunnableConfig) -> OrchestratorState:
    """
    Use a cheap LLM to classify user intent: fetch_recipes vs catalog_recipe
    """
    llm = ChatOpenAI(model=ROUTER_MODEL, api_key=OPENAI_API_KEY, temperature=0)

    # Invoke the prompt
    prompt = ROUTE_INTENT_PROMPT.invoke({"user_input": state.user_input})

    # Get intent classification
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()

    # Validate and set intent
    if intent in ["fetch_recipes", "catalog_recipe"]:
        state.intent = intent
    else:
        # Default to fetch_recipes if unclear
        state.intent = "fetch_recipes"

    return state


def extract_url(state: OrchestratorState, config: RunnableConfig) -> OrchestratorState:
    """
    Extract recipe URL from user input for catalog_recipe intent
    """
    import re

    # Simple URL extraction using regex
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, state.user_input)

    if urls:
        state.recipe_url = urls[0]  # Take the first URL found
    else:
        # If no URL found, set error
        state.error_message = "No URL found in your message. Please provide a recipe URL to catalog."
        state.success = False

    return state


def invoke_fetch_recipes(state: OrchestratorState, config: RunnableConfig) -> OrchestratorState:
    """
    Invoke the fetch_recipes workflow and store results
    """
    from agents.fetch_recipes.graph import graph as fetch_recipes_graph

    try:
        # Invoke fetch_recipes graph
        result = fetch_recipes_graph.invoke({"user_query": state.user_input})

        # Store results
        state.fetch_recipes_result = result
        state.response = result.get("recommendations", "No recommendations available.")
        state.success = True

    except Exception as e:
        state.error_message = f"Error in fetch_recipes workflow: {str(e)}"
        state.success = False
        state.response = "Sorry, I encountered an error while searching for recipes."

    return state


def invoke_catalog_recipe(state: OrchestratorState, config: RunnableConfig) -> OrchestratorState:
    """
    Invoke the catalog_recipe workflow and store results
    """
    from agents.catalog_recipe.graph import graph as catalog_recipe_graph

    try:
        # Invoke catalog_recipe graph
        result = catalog_recipe_graph.invoke({"recipe_url": state.recipe_url})

        # Store results
        state.catalog_recipe_result = result
        state.success = result.get("success", False)

        if state.success:
            recipe_name = result.get("recipe_data", {}).get("name", "the recipe")
            state.response = f"✅ Successfully added '{recipe_name}' to the database!"
        else:
            error = result.get("error_message", "Unknown error")
            state.response = f"❌ Failed to catalog recipe: {error}"
            state.error_message = error

    except Exception as e:
        state.error_message = f"Error in catalog_recipe workflow: {str(e)}"
        state.success = False
        state.response = "Sorry, I encountered an error while cataloging the recipe."

    return state


# Conditional routing functions

def route_by_intent(state: OrchestratorState) -> str:
    """
    Route to appropriate workflow based on classified intent
    """
    if state.intent == "catalog_recipe":
        return "extract_url"
    else:
        return "invoke_fetch_recipes"


def route_after_url_extraction(state: OrchestratorState) -> str:
    """
    Route to catalog workflow if URL was found, otherwise end with error
    """
    if state.recipe_url:
        return "invoke_catalog_recipe"
    else:
        return END


# Build the graph
builder = StateGraph(OrchestratorState)

# Add nodes
builder.add_node("classify_intent", classify_intent)
builder.add_node("extract_url", extract_url)
builder.add_node("invoke_fetch_recipes", invoke_fetch_recipes)
builder.add_node("invoke_catalog_recipe", invoke_catalog_recipe)

# Add edges
builder.add_edge(START, "classify_intent")

# Route based on intent
builder.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "extract_url": "extract_url",
        "invoke_fetch_recipes": "invoke_fetch_recipes"
    }
)

# Route after URL extraction
builder.add_conditional_edges(
    "extract_url",
    route_after_url_extraction,
    {
        "invoke_catalog_recipe": "invoke_catalog_recipe",
        END: END
    }
)

# Both workflows end at END
builder.add_edge("invoke_fetch_recipes", END)
builder.add_edge("invoke_catalog_recipe", END)

# Compile the graph
graph = builder.compile()
