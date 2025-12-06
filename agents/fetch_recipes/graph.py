# graph.py
from typing import Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
import sqlite3

# local imports
from .config import OPENAI_API_KEY, OPENAI_MODEL, DB_PATH
from .prompts import GENERATE_SQL_PROMPT, ANALYZE_SQL_RESULTS_PROMPT
from .sql_validator import (
    validate_sql_query,
    get_schema_documentation,
    explain_validation_failure
)


# Define the Agent State
class AgentState(BaseModel):
    """Pydantic model for LangGraph"""
    user_query: str
    generated_sql: str = ""
    sql_validation_error: str = ""
    sql_retry_count: int = 0
    sql_results: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: str = ""


# Define the Nodes

def generate_sql_query(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Generate SQL query to answer user's question
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

# Add nodes
builder.add_node("generate_sql_query", generate_sql_query)
builder.add_node("judge_sql_query", judge_sql_query)
builder.add_node("execute_sql_query", execute_sql_query)
builder.add_node("analyze_sql_results", analyze_sql_results)
builder.add_node("handle_sql_failure", handle_sql_failure)

# Add edges
builder.add_edge(START, "generate_sql_query")
builder.add_edge("generate_sql_query", "judge_sql_query")

# Validation loop
builder.add_conditional_edges(
    "judge_sql_query",
    should_retry_sql,
    {
        "generate_sql_query": "generate_sql_query",  # Retry on validation failure
        "execute_sql_query": "execute_sql_query",    # Proceed if valid
        "handle_sql_failure": "handle_sql_failure"   # Give up after max retries
    }
)

# Execution loop
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
