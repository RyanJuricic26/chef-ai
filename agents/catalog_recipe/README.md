# Recipe Catalog Agent

This agent fetches recipes from URLs and adds them to the database.

## Workflow Overview

```
START
  ↓
fetch_webpage
  ↓
parse_json_ld
  ↓
  ├─→ [JSON-LD found] → validate_recipe_data
  └─→ [JSON-LD not found] → extract_with_llm → validate_recipe_data
                                                    ↓
                                                    ├─→ [valid] → save_to_database → END
                                                    └─→ [invalid] → END (with error)
```

## Agent State

### Input
- `recipe_url`: The URL of the recipe webpage to catalog

### Processing State
- `html_content`: Raw HTML from the webpage
- `json_ld_data`: Parsed JSON-LD Recipe schema (if found)
- `extraction_method`: Either "json_ld" or "llm_html"

### Extracted Data
- `recipe_data`: Dictionary containing:
  - `name`: Recipe name
  - `description`: Brief description
  - `instructions`: Step-by-step cooking instructions
  - `prep_time`: Preparation time in minutes
  - `cook_time`: Cooking time in minutes
  - `servings`: Number of servings
  - `difficulty`: "easy", "medium", or "hard"
  - `cuisine_type`: Type of cuisine (Italian, Mexican, etc.)
  - `url`: Source URL
  - `ingredients`: List of ingredient dictionaries with:
    - `name`: Ingredient name
    - `quantity`: Amount needed
    - `unit`: Unit of measurement
    - `category`: Category (meat, vegetable, dairy, etc.)

### Output
- `recipe_id`: Database ID of saved recipe
- `success`: Boolean indicating if recipe was saved
- `error_message`: Error details if operation failed

## Nodes

### 1. fetch_webpage
Fetches the HTML content from the recipe URL using HTTP requests.

### 2. parse_json_ld
Attempts to extract recipe data from JSON-LD structured data (schema.org/Recipe format). This is the preferred method as it provides clean, structured data.

### 3. extract_with_llm
Fallback extraction method using LLM to parse recipe information from HTML when JSON-LD is not available. The LLM cleans the HTML and extracts all required fields.

### 4. validate_recipe_data
Validates that all required fields are present and properly formatted. Sets default values for optional fields.

### 5. save_to_database
Persists the validated recipe to the SQLite database, including ingredients and their relationships.

## Usage

```python
from agents.recipe_catalog.graph import graph

result = graph.invoke({
    "recipe_url": "https://example.com/recipe/chocolate-chip-cookies"
})

if result["success"]:
    print(f"Recipe saved with ID: {result['recipe_id']}")
else:
    print(f"Error: {result['error_message']}")
```

## Database Schema

The agent populates three tables:

1. **recipes**: Main recipe information
2. **ingredients**: Unique ingredient names and categories
3. **recipe_ingredients**: Junction table linking recipes to ingredients with quantities
