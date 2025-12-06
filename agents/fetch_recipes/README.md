# Fetch Recipes Agent

An intelligent LangGraph agent for recipe search and database analytics with built-in SQL injection protection.

## Features

### 1. Multi-Mode Query Classification
The agent automatically classifies user queries into four modes:
- **ingredients**: Find recipes based on available ingredients
- **name**: Search for recipes by name or dish type
- **analytics**: Answer analytical questions about the recipe database
- **general**: Browse all recipes

### 2. Standard Recipe Search
Handles traditional recipe searches with:
- Ingredient-based matching with percentage scoring
- Recipe name search
- Filtering and ranking by match quality
- Configurable thresholds and limits

### 3. Analytics Mode with SQL Judge
**New hybrid approach** for analytical questions with robust security:

#### Workflow:
```
User Query → Classify → Generate SQL → Judge SQL → Execute → Analyze Results
                                           ↓
                                    [Validation Failed]
                                           ↓
                                    Retry (max 3x)
```

#### Security Features:
The **SQL Judge** validates all generated queries through:

1. **SQL Injection Detection**
   - Blocks DROP, DELETE, UPDATE, INSERT, ALTER commands
   - Prevents multiple statements
   - Blocks SQL comments (`--`, `/* */`)
   - Detects UNION attacks
   - Prevents stored procedure execution

2. **Query Structure Validation**
   - Only allows SELECT statements
   - Uses `sqlparse` library for proper SQL parsing
   - Validates SQL syntax

3. **Schema Validation**
   - Verifies all referenced tables exist
   - Checks column references against schema
   - Provides warnings for potential issues

4. **Retry Loop**
   - Up to 3 retry attempts on validation failures
   - Feeds validation errors back to LLM for self-correction
   - Graceful failure handling with user-friendly messages

## Architecture

### State Management
```python
class AgentState:
    user_query: str
    search_mode: Literal["ingredients", "general", "name", "analytics"]

    # Recipe search fields
    user_ingredients: list[str] | None
    recipes: list[dict]
    filtered_recipes: list[dict]

    # Analytics fields
    generated_sql: str
    sql_validation_error: str
    sql_retry_count: int
    sql_results: list[dict]

    # Output
    recommendations: str
```

### Graph Structure

**Standard Recipe Flow:**
```
START → classify_query → fetch_recipes → filter_and_rank → generate_recommendations → END
```

**Analytics Flow with Judge:**
```
START → classify_query → generate_sql_query → judge_sql_query
                                                    ↓
                          [Valid] → execute_sql_query → analyze_sql_results → END
                                         ↓
                          [Invalid] → Retry (if count < 3)
                                         ↓
                          [Max Retries] → handle_sql_failure → END
```

## Database Schema

The agent works with a SQLite database containing:

### Tables:
- **users**: User information (id, name)
- **recipes**: Recipe details (id, name, description, instructions, prep_time, cook_time, servings, difficulty, cuisine_type, url)
- **ingredients**: Available ingredients (id, name, category)
- **recipe_ingredients**: Recipe-ingredient relationships (recipe_id, ingredient_id, quantity, unit, notes)

### Relationships:
- `recipe_ingredients.recipe_id` → `recipes.id`
- `recipe_ingredients.ingredient_id` → `ingredients.id`

## Configuration

Environment variables (see [config.py](config.py)):
```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
DB_PATH=database/app.db
MIN_MATCH_THRESHOLD=30.0
MAX_RECIPES_TO_RETURN=5
```

## Usage Examples

### Analytics Queries
```python
from agents.fetch_recipes.graph import graph, AgentState

# Count recipes
result = graph.invoke(AgentState(
    user_query="How many recipes are in the database?"
))

# Aggregations
result = graph.invoke(AgentState(
    user_query="What is the average prep time for Italian recipes?"
))

# Grouping
result = graph.invoke(AgentState(
    user_query="How many recipes do we have for each difficulty level?"
))

# Complex queries
result = graph.invoke(AgentState(
    user_query="Show me the top 3 most common ingredients"
))
```

### Ingredient-Based Search
```python
result = graph.invoke(AgentState(
    user_query="I have chicken, garlic, and olive oil"
))
```

### Recipe Name Search
```python
result = graph.invoke(AgentState(
    user_query="Show me pasta carbonara recipes"
))
```

## Testing

Run the test suite:
```bash
python test_analytics_agent.py
```

Tests include:
- Valid analytics queries
- Aggregations and grouping
- Complex multi-table queries
- Standard recipe search (non-analytics)
- **SQL injection protection** (security test)

## Files

- [graph.py](graph.py) - Main agent graph and nodes
- [sql_validator.py](sql_validator.py) - SQL judge with security validation
- [prompts.py](prompts.py) - LLM prompts for all modes
- [sql_queries.py](sql_queries.py) - Predefined SQL queries
- [fetch_utils.py](fetch_utils.py) - Helper utilities
- [config.py](config.py) - Configuration settings

## Security Notes

⚠️ **Important**: The SQL judge provides multiple layers of protection, but should still be used in controlled environments:

1. ✅ Blocks all destructive SQL operations
2. ✅ Validates against known schema only
3. ✅ Uses parameterized execution for results
4. ✅ Limits retry attempts to prevent abuse
5. ✅ Provides detailed validation feedback

Always review generated SQL queries in production environments and consider additional safeguards like read-only database connections.

## Future Enhancements

Potential improvements:
- [ ] Parameterized query builder (instead of raw SQL generation)
- [ ] Query result caching
- [ ] Support for more complex analytical functions
- [ ] User-specific query history and preferences
- [ ] Query performance monitoring
- [ ] Database view abstractions for security
