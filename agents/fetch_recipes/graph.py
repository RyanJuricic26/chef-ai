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
    GENERATE_RECOMMENDATIONS_PROMPT,
    GENERATE_SQL_PROMPT,
    ANALYZE_SQL_RESULTS_PROMPT
)
from .sql_validator import (
    validate_sql_query,
    get_schema_documentation,
    explain_validation_failure
)
import sqlite3


# Define the Agent State
class AgentState(BaseModel):
    """Pydantic model for LangGraph"""
    user_query: str
    user_ingredients: list[str] | None = None
    recipes: list[dict[str, Any]] = Field(default_factory=list)
    filtered_recipes: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: str = ""
    search_mode: Literal["ingredients", "general", "name", "analytics"] = "general"
    # Analytics-specific fields
    generated_sql: str = ""
    sql_validation_error: str = ""
    sql_retry_count: int = 0
    sql_results: list[dict[str, Any]] = Field(default_factory=list)


# Define the Nodes

def classify_query(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Use AI to classify the user's query to determine search mode
    """
    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0)

    # Invoke the prompt
    prompt = CLASSIFY_QUERY_PROMPT.invoke({"user_query": state.user_query})

    # Get classification
    response = llm.invoke(prompt)
    classification = response.content.strip().lower()

    # Validate and set search mode
    if classification in ["ingredients", "name", "general", "analytics"]:
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
        prompt = EXTRACT_INGREDIENTS_PROMPT.invoke({"user_query": state.user_query})
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
        prompt = EXTRACT_SEARCH_TERM_PROMPT.invoke({"user_query": state.user_query})
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


def generate_sql_query(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Generate SQL query for analytics questions
    """
    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0)

    # Get schema documentation
    schema_doc = get_schema_documentation()

    # If retrying, add validation error context
    if state.sql_validation_error:
        user_query_with_context = f"{state.user_query}\n\nPrevious attempt failed with: {state.sql_validation_error}\nPlease fix the query."
    else:
        user_query_with_context = state.user_query

    # Generate SQL query
    prompt = GENERATE_SQL_PROMPT.invoke({
        "schema_documentation": schema_doc,
        "user_query": user_query_with_context
    })

    response = llm.invoke(prompt)
    state.generated_sql = response.content.strip()

    # Clear previous validation error
    state.sql_validation_error = ""

    return state


def judge_sql_query(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Validate the generated SQL query for security and correctness
    """
    validation_result = validate_sql_query(state.generated_sql)

    if not validation_result.is_valid:
        # Query failed validation
        state.sql_validation_error = explain_validation_failure(validation_result)
        state.sql_retry_count += 1
    else:
        # Query passed - use sanitized version
        state.generated_sql = validation_result.sanitized_query
        state.sql_validation_error = ""

    return state


def execute_sql_query(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Execute the validated SQL query and store results
    """
    from .config import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute(state.generated_sql)
        rows = cur.fetchall()
        state.sql_results = [dict(row) for row in rows]
    except Exception as e:
        # If execution fails, set error for retry
        state.sql_validation_error = f"SQL execution error: {str(e)}\n\nPlease revise your query."
        state.sql_retry_count += 1
        state.sql_results = []
    finally:
        conn.close()

    return state


def analyze_sql_results(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Use LLM to analyze SQL results and generate natural language response
    """
    llm = ChatOpenAI(model=OPENAI_MODEL, api_key=OPENAI_API_KEY, temperature=0.7)

    # Format results for LLM
    if not state.sql_results:
        results_text = "No results found (empty result set)"
    else:
        results_text = "\n".join(str(row) for row in state.sql_results)

    # Generate analysis
    prompt = ANALYZE_SQL_RESULTS_PROMPT.invoke({
        "user_query": state.user_query,
        "sql_query": state.generated_sql,
        "query_results": results_text
    })

    response = llm.invoke(prompt)
    state.recommendations = response.content

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
    prompt = GENERATE_RECOMMENDATIONS_PROMPT.invoke({
        "user_query": state.user_query,
        "recipes_context": recipes_context,
        "ingredients_context": ingredients_context
    })

    # Get LLM response
    response = llm.invoke(prompt)
    state.recommendations = response.content

    return state


def route_after_classify(state: AgentState) -> str:
    """
    Route to appropriate handler based on search mode
    """
    if state.search_mode == "analytics":
        return "generate_sql_query"
    else:
        return "fetch_recipes"


def should_filter(state: AgentState) -> str:
    """
    Determine if we need to filter recipes
    """
    if state.recipes:
        return "filter_and_rank_recipes"
    else:
        return "generate_recommendations"


def should_retry_sql(state: AgentState) -> str:
    """
    Determine if SQL query should be retried or if we should proceed
    """
    MAX_RETRIES = 3

    if state.sql_validation_error and state.sql_retry_count < MAX_RETRIES:
        # Retry generation with error feedback
        return "generate_sql_query"
    elif state.sql_validation_error:
        # Max retries reached - give up and return error
        return "handle_sql_failure"
    else:
        # Validation passed - execute query
        return "execute_sql_query"


def should_retry_execution(state: AgentState) -> str:
    """
    Determine if we should retry after execution failure or analyze results
    """
    MAX_RETRIES = 3

    if state.sql_validation_error and state.sql_retry_count < MAX_RETRIES:
        # Execution failed - retry generation
        return "generate_sql_query"
    elif state.sql_validation_error:
        # Max retries reached
        return "handle_sql_failure"
    else:
        # Success - analyze results
        return "analyze_sql_results"


def handle_sql_failure(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Handle case where SQL generation/validation failed after max retries
    """
    state.recommendations = (
        f"I apologize, but I wasn't able to generate a valid SQL query to answer your question "
        f"after {state.sql_retry_count} attempts. The last error was:\n\n{state.sql_validation_error}\n\n"
        f"Could you try rephrasing your question or asking something more specific?"
    )
    return state


# Build the graph
builder = StateGraph(AgentState)

# Add nodes - Standard recipe search flow
builder.add_node("classify_query", classify_query)
builder.add_node("fetch_recipes", fetch_recipes)
builder.add_node("filter_and_rank_recipes", filter_and_rank_recipes)
builder.add_node("generate_recommendations", generate_recommendations)

# Add nodes - Analytics flow with judge
builder.add_node("generate_sql_query", generate_sql_query)
builder.add_node("judge_sql_query", judge_sql_query)
builder.add_node("execute_sql_query", execute_sql_query)
builder.add_node("analyze_sql_results", analyze_sql_results)
builder.add_node("handle_sql_failure", handle_sql_failure)

# Add edges - Main routing
builder.add_edge(START, "classify_query")
builder.add_conditional_edges(
    "classify_query",
    route_after_classify,
    {
        "fetch_recipes": "fetch_recipes",
        "generate_sql_query": "generate_sql_query"
    }
)

# Standard recipe search flow
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

# Analytics flow with validation loop
builder.add_edge("generate_sql_query", "judge_sql_query")
builder.add_conditional_edges(
    "judge_sql_query",
    should_retry_sql,
    {
        "generate_sql_query": "generate_sql_query",  # Retry on validation failure
        "execute_sql_query": "execute_sql_query",    # Proceed if valid
        "handle_sql_failure": "handle_sql_failure"   # Give up after max retries
    }
)
builder.add_conditional_edges(
    "execute_sql_query",
    should_retry_execution,
    {
        "generate_sql_query": "generate_sql_query",  # Retry on execution failure
        "analyze_sql_results": "analyze_sql_results", # Proceed if successful
        "handle_sql_failure": "handle_sql_failure"   # Give up after max retries
    }
)
builder.add_edge("analyze_sql_results", END)
builder.add_edge("handle_sql_failure", END)

# Compile the graph
graph = builder.compile()
