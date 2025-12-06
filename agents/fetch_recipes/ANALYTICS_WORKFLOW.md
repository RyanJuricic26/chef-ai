# Analytics Workflow with SQL Judge

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                      │
│              "How many Italian recipes are there?"                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CLASSIFY QUERY (LLM)                               │
│  Determines: ingredients | name | analytics | general                  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
              [analytics]                  [other modes]
                    │                           │
                    ▼                           ▼
        ┌───────────────────────┐   ┌──────────────────────┐
        │  GENERATE SQL QUERY   │   │   Standard Recipe    │
        │       (LLM)           │   │   Search Flow        │
        │                       │   └──────────────────────┘
        │ Provides schema docs  │
        │ Generates SELECT only │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   JUDGE SQL QUERY     │◄──────────────┐
        │   (Validator)         │               │
        │                       │               │
        │ ✓ Injection check     │               │
        │ ✓ Structure check     │               │
        │ ✓ Schema check        │               │
        └───────────────────────┘               │
                    │                           │
        ┌───────────┴───────────┐               │
        │                       │               │
    [VALID]                [INVALID]            │
        │                       │               │
        │              ┌────────┴────────┐      │
        │              │  Retry Count?   │      │
        │              └────────┬────────┘      │
        │                       │               │
        │                  [< 3 retries]        │
        │                       │               │
        │                       └───────────────┘
        │                     (Feed error back)
        │
        │                  [≥ 3 retries]
        │                       │
        ▼                       ▼
┌───────────────────┐   ┌──────────────────┐
│  EXECUTE SQL      │   │  HANDLE FAILURE  │
│                   │   │                  │
│ Try to run query  │   │ Return error msg │
└───────────────────┘   └──────────────────┘
        │                       │
        │                       │
    [Success]              [To END]
        │
        ▼
┌───────────────────┐
│ ANALYZE RESULTS   │
│     (LLM)         │
│                   │
│ Convert SQL       │
│ results to        │
│ natural language  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   RETURN TO USER  │
│                   │
│ "There are 3      │
│  Italian recipes" │
└───────────────────┘
```

## Security Layers

### Layer 1: LLM Instruction
The LLM is instructed to:
- Only generate SELECT statements
- Use proper table.column references
- Follow schema documentation
- Avoid dangerous patterns

### Layer 2: SQL Injection Detection
Pattern matching for:
- `DROP TABLE`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`
- SQL comments (`--`, `/* */`)
- Multiple statements (`;`)
- `UNION SELECT` attacks
- Stored procedures

### Layer 3: Structure Validation
Using `sqlparse` library:
- Parse SQL syntax
- Verify it's a SELECT statement
- Reject malformed queries

### Layer 4: Schema Validation
Against defined schema:
- Check all table names exist
- Warn about suspicious column names
- Ensure proper relationships

### Layer 5: Execution Protection
If validation passes:
- Execute in read-only mode
- Catch runtime errors
- Return structured results

## Example Flow

### User Query
```
"What's the average cook time for easy recipes?"
```

### Step 1: Classification
```
Mode: analytics
```

### Step 2: Generate SQL
```sql
SELECT AVG(recipes.cook_time) AS average_cook_time
FROM recipes
WHERE recipes.difficulty = 'easy'
```

### Step 3: Judge (Validation)
```
✓ No SQL injection patterns detected
✓ Structure is valid SELECT
✓ Table 'recipes' exists in schema
✓ Column 'cook_time' exists
✓ Column 'difficulty' exists
→ PASS
```

### Step 4: Execute
```
Results: [{'average_cook_time': 18.5}]
```

### Step 5: Analyze
```
"The average cook time for easy recipes is approximately
18.5 minutes. This makes them perfect for quick weeknight
meals!"
```

## Retry Logic Example

### Attempt 1: Invalid SQL
```sql
SELECT COUNT(*) FROM recipe  -- Wrong table name
```
**Judge**: ❌ Invalid table 'recipe' (should be 'recipes')

### Attempt 2: Corrected
```sql
SELECT COUNT(*) FROM recipes
```
**Judge**: ✅ PASS

## Attack Prevention Examples

### Attack: DROP TABLE
```sql
Input: "How many recipes? DROP TABLE recipes; --"
LLM Generates: SELECT COUNT(*) FROM recipes
```
**Result**: LLM ignores malicious intent

### Attack: SQL Comment Injection
```sql
Generated: SELECT * FROM recipes WHERE id=1 --
```
**Judge**: ❌ Blocked - SQL comment detected

### Attack: UNION SELECT
```sql
Generated: SELECT name FROM recipes UNION SELECT password FROM users
```
**Judge**: ❌ Blocked - UNION SELECT attack detected

## Configuration

### Max Retries
```python
MAX_RETRIES = 3
```

### Validation Rules
See [sql_validator.py](sql_validator.py) for:
- `check_for_sql_injection()` - Pattern matching
- `validate_query_structure()` - SQL parsing
- `validate_schema_references()` - Schema checking

### Error Handling
```python
if sql_retry_count >= MAX_RETRIES:
    return "Could not generate valid SQL after 3 attempts"
```

## Testing

Run comprehensive tests:
```bash
# Test end-to-end analytics workflow
python test_analytics_agent.py

# Test SQL validator directly
python test_sql_validator.py
```

## Future Enhancements

1. **Parameterized Query Builder**: Instead of raw SQL generation
2. **Query Whitelisting**: Pre-approved query patterns
3. **Read-Only Database Connection**: Additional DB-level protection
4. **Query Logging**: Audit trail for all executed queries
5. **Rate Limiting**: Prevent query flooding
6. **Result Set Limits**: Cap maximum rows returned
