# Fetch Recipes Agent

An intelligent LangGraph agent that uses **LLM-generated SQL** with built-in security validation to answer ANY question about your recipe database.

## Philosophy

**No predefined queries. Just ask questions.**

The LLM generates custom SQL queries for every request - whether you're searching for recipes, asking analytical questions, or exploring your data. The SQL Judge ensures every query is safe and valid.

## Features

### 1. Universal Query Handling
Ask anything about your recipes in natural language:
- "I have chicken and garlic, what can I make?"
- "Show me easy Italian recipes under 30 minutes"
- "What's the average prep time for my recipes?"
- "Which ingredients do I use most often?"

### 2. Smart SQL Generation
The LLM understands your database schema and generates appropriate queries:
- Recipe searches with ingredient matching
- Analytical aggregations (COUNT, AVG, SUM)
- Complex JOINs across multiple tables
- Filtering and sorting

### 3. Multi-Layer Security with SQL Judge

Every generated query passes through validation:

#### Layer 1: Pattern Detection
- Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`
- Prevents SQL comments (`--`, `/* */`)
- Detects multiple statements
- Catches `UNION` attacks

#### Layer 2: Structure Validation
- Ensures SELECT-only queries
- Validates SQL syntax with `sqlparse`
- Rejects malformed queries

#### Layer 3: Schema Validation
- Verifies tables exist
- Checks column references
- Warns about suspicious patterns

#### Layer 4: Retry Loop
- Up to 3 retry attempts
- Feeds errors back to LLM
- Self-correcting query generation

## Workflow

```
User Question → Generate SQL → Judge (Validate) → Execute → Analyze Results
                                      ↓
                               [If invalid]
                                      ↓
                              Retry with feedback
                                      ↓
                             [Max 3 retries]
                                      ↓
                              Error message
```

## Architecture

### State
```python
class AgentState:
    user_query: str                    # User's question
    generated_sql: str                 # LLM-generated query
    sql_validation_error: str          # Error from judge
    sql_retry_count: int               # Retry counter
    sql_results: list[dict]            # Query results
    recommendations: str               # Final response
```

### Graph Flow
```
START → generate_sql_query → judge_sql_query → execute_sql_query → analyze_sql_results → END
              ↑                     ↓                    ↓
              └─────[retry]─────────┴────[retry]────────┘
                                    ↓
                          [max retries reached]
                                    ↓
                           handle_sql_failure → END
```

## Database Schema

```
users:
  - id, name

recipes:
  - id, name, description, instructions
  - prep_time, cook_time, servings
  - difficulty, cuisine_type, url, created_at

ingredients:
  - id, name, category

recipe_ingredients:
  - id, recipe_id, ingredient_id
  - quantity, unit, notes
```

## Usage Examples

### Recipe Search
```python
from agents.fetch_recipes.graph import graph, AgentState

# Ingredient-based search
result = graph.invoke(AgentState(
    user_query="I have chicken, garlic, and olive oil"
))

# Response includes recipe matches with percentages
```

### Analytics
```python
# Simple count
result = graph.invoke(AgentState(
    user_query="How many recipes do I have?"
))

# Aggregations
result = graph.invoke(AgentState(
    user_query="What's the average cook time for easy recipes?"
))

# Grouping
result = graph.invoke(AgentState(
    user_query="Show me recipe count by cuisine type"
))
```

### Complex Queries
```python
# Multi-condition search
result = graph.invoke(AgentState(
    user_query="Show me easy Italian recipes that take less than 30 minutes"
))

# Top N queries
result = graph.invoke(AgentState(
    user_query="What are the 5 most common ingredients?"
))
```

## Example Queries & Generated SQL

| User Query | Generated SQL |
|------------|---------------|
| "How many recipes?" | `SELECT COUNT(*) FROM recipes` |
| "I have chicken and garlic" | Complex JOIN with match percentage calculation |
| "Average prep time for Italian recipes" | `SELECT AVG(prep_time) FROM recipes WHERE cuisine_type='Italian'` |
| "Most common ingredients" | `SELECT name, COUNT(*) FROM ingredients ... GROUP BY name ORDER BY count DESC` |

## Configuration

`.env` file:
```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
DB_PATH=database/app.db
```

## Testing

Run comprehensive tests:
```bash
# Test all query types
python test_simplified_agent.py

# Test SQL validator directly
python test_sql_validator.py
```

Test results show:
- ✅ Analytical queries work correctly
- ✅ Recipe searches with ingredient matching
- ✅ Complex multi-condition queries
- ✅ Security: SQL injection attempts blocked
- ✅ Edge cases handled gracefully

## Security Guarantees

The SQL Judge provides robust protection:

1. **✅ No Data Modification**: Only SELECT queries allowed
2. **✅ Schema Validation**: Queries limited to known tables
3. **✅ Injection Prevention**: Malicious patterns blocked
4. **✅ Syntax Validation**: Malformed queries rejected
5. **✅ Rate Limiting**: Max 3 retry attempts

**Security Test Result:**
```
User: "How many recipes? DROP TABLE recipes; --"
LLM Generated: "SELECT COUNT(*) FROM recipes"
Judge: ✅ PASS (malicious intent ignored by LLM)
```

## Files

- **[graph.py](graph.py)** - Main agent with SQL workflow
- **[sql_validator.py](sql_validator.py)** - Security judge
- **[prompts.py](prompts.py)** - LLM prompts with SQL patterns
- **[config.py](config.py)** - Configuration
- **[README.md](README.md)** - This file
- **[ANALYTICS_WORKFLOW.md](ANALYTICS_WORKFLOW.md)** - Detailed workflow diagram

## Why This Approach?

### ✅ Advantages
- **Maximum Flexibility**: Handle any question without writing new code
- **Natural Language**: Users ask questions normally
- **Self-Improving**: LLM learns from validation errors
- **Secure**: Multi-layer validation prevents attacks
- **Maintainable**: No predefined query library to maintain

### ⚠️ Considerations
- **LLM Cost**: Each query requires 2 LLM calls (generate + analyze)
- **Latency**: Validation and retries add processing time
- **LLM Reliability**: Query quality depends on LLM capabilities

### 🎯 Best Practices
1. Use read-only database connections in production
2. Monitor generated queries for optimization opportunities
3. Cache common query patterns if needed
4. Set appropriate timeout limits
5. Log all queries for audit trail

## Future Enhancements

- [ ] Query result caching
- [ ] Query performance monitoring
- [ ] User-specific query history
- [ ] Support for query explanations
- [ ] Suggested follow-up questions
- [ ] Read-only database views for extra security

## Comparison with Predefined Queries

| Aspect | Predefined Queries | LLM-Generated SQL |
|--------|-------------------|-------------------|
| Flexibility | Limited to predefined patterns | Unlimited natural language |
| Maintenance | Must write new code for new queries | Just update prompts |
| Security | Very safe (hardcoded) | Safe with judge validation |
| Performance | Fast (optimized) | Slightly slower (LLM calls) |
| User Experience | Must learn specific commands | Ask anything naturally |

## Conclusion

This agent demonstrates that **LLM-generated SQL with proper validation** can safely handle any database question while maintaining security and flexibility. The SQL Judge provides the guardrails needed to use LLMs for dynamic SQL generation in production.
