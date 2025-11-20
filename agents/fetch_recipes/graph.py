# graph.py
from typing import Any, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

# local imports
from .sql_queries import get_all_recipes, get_recipes_by_ingredients, search_recipes_by_name
from .fetch_utils import (
    format_recipe_for_llm,
    parse_user_ingredients,
    filter_recipes_by_threshold,
    rank_recipes,
    create_recipe_summary
)
from .config import OPENAI_API_KEY, OPENAI_MODEL, MIN_MATCH_THRESHOLD, MAX_RECIPES_TO_RETURN
from .prompts import (
    CLASSIFY_QUERY_PROMPT,
    EXTRACT_INGREDIENTS_PROMPT,
    EXTRACT_SEARCH_TERM_PROMPT,
    GENERATE_RECOMMENDATIONS_PROMPT
)


# Define the Agent State
class AgentState(BaseModel):
    """Pydantic model for LangGraph"""
    user_query: str
    user_ingredients: list[str] | None = None
    recipes: list[dict[str, Any]] = Field(default_factory=list)
    filtered_recipes: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: str = ""
    search_mode: Literal["ingredients", "general", "name"] = "general"


# Define the Nodes

def classify_query(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Use AI to classify the user's query to determine search mode
    """
    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0)

    # Invoke the prompt
    prompt = CLASSIFY_QUERY_PROMPT.invoke(user_query=state.user_query)

    # Get classification
    response = llm.invoke(prompt)
    classification = response.content.strip().lower()

    # Validate and set search mode
    if classification in ["ingredients", "name", "general"]:
        state.search_mode = classification
    else:
        # Default to general if classification is unclear
        state.search_mode = "general"

    return state


def fetch_recipes(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Fetch recipes from the database based on search mode
    """
    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0)

    if state.search_mode == "ingredients":
        # Extract ingredients from user query using LLM
        prompt = EXTRACT_INGREDIENTS_PROMPT.invoke(user_query=state.user_query)
        response = llm.invoke(prompt)
        ingredients_text = response.content.strip()

        # Parse ingredients
        if ingredients_text.upper() != "NONE":
            state.user_ingredients = [ing.strip() for ing in ingredients_text.split('\n') if ing.strip()]
        else:
            state.user_ingredients = []

        # Fetch recipes by ingredients
        if state.user_ingredients:
            state.recipes = get_recipes_by_ingredients(state.user_ingredients)
        else:
            state.recipes = []

    elif state.search_mode == "name":
        # Extract search term using LLM
        prompt = EXTRACT_SEARCH_TERM_PROMPT.invoke(user_query=state.user_query)
        response = llm.invoke(prompt)
        search_term = response.content.strip()

        # Search recipes by name
        state.recipes = search_recipes_by_name(search_term)

    else:
        # General search - get all recipes
        state.recipes = get_all_recipes()

    return state


def filter_and_rank_recipes(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Filter and rank recipes based on match quality and user preferences
    """
    if state.search_mode == "ingredients" and state.recipes:
        # Filter by minimum threshold
        filtered = filter_recipes_by_threshold(state.recipes, MIN_MATCH_THRESHOLD)

        # Rank the recipes
        state.filtered_recipes = rank_recipes(filtered)[:MAX_RECIPES_TO_RETURN]
    else:
        # For other modes, just limit the number
        state.filtered_recipes = state.recipes[:MAX_RECIPES_TO_RETURN]

    return state


def generate_recommendations(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Use LLM to generate personalized recommendations based on recipes and user query
    """
    if not state.filtered_recipes:
        state.recommendations = "I couldn't find any recipes matching your criteria. Try adding more recipes to the database or adjusting your requirements."
        return state

    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.7)

    # Prepare context
    recipes_context = "\n\n---\n\n".join(
        format_recipe_for_llm(recipe) for recipe in state.filtered_recipes
    )

    # Prepare ingredients context
    ingredients_context = ""
    if state.user_ingredients:
        ingredients_context = f"\n\nUser's Available Ingredients: {', '.join(state.user_ingredients)}"

    # Invoke the prompt
    prompt = GENERATE_RECOMMENDATIONS_PROMPT.invoke(
        user_query=state.user_query,
        recipes_context=recipes_context,
        ingredients_context=ingredients_context
    )

    # Get LLM response
    response = llm.invoke(prompt)
    state.recommendations = response.content

    return state


def should_filter(state: AgentState) -> str:
    """
    Determine if we need to filter recipes
    """
    if state.recipes:
        return "filter_and_rank_recipes"
    else:
        return "generate_recommendations"


# Build the graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("classify_query", classify_query)
builder.add_node("fetch_recipes", fetch_recipes)
builder.add_node("filter_and_rank_recipes", filter_and_rank_recipes)
builder.add_node("generate_recommendations", generate_recommendations)

# Add edges
builder.add_edge(START, "classify_query")
builder.add_edge("classify_query", "fetch_recipes")
builder.add_conditional_edges(
    "fetch_recipes",
    should_filter,
    {
        "filter_and_rank_recipes": "filter_and_rank_recipes",
        "generate_recommendations": "generate_recommendations"
    }
)
builder.add_edge("filter_and_rank_recipes", "generate_recommendations")
builder.add_edge("generate_recommendations", END)

# Compile the graph
graph = builder.compile()
