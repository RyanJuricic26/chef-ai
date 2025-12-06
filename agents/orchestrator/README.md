# Orchestrator Agent

This agent routes user requests to the appropriate workflow based on intent classification.

## Overview

The orchestrator acts as the main entry point for all user interactions. It uses a cheap LLM (gpt-4o-mini) to classify user intent and route to either:

1. **fetch_recipes** - Search for recipes in the database
2. **catalog_recipe** - Add a new recipe from a URL

## Workflow

```
START
  ↓
classify_intent (LLM classifies: fetch_recipes or catalog_recipe)
  ↓
  ├─→ [fetch_recipes] → invoke_fetch_recipes → END
  └─→ [catalog_recipe] → extract_url → invoke_catalog_recipe → END
```

## Agent State

### Input
- `user_input`: Raw user message (text or voice-transcribed)

### Processing
- `intent`: Classified intent ("fetch_recipes" or "catalog_recipe")
- `recipe_url`: Extracted URL (for catalog_recipe intent)

### Results
- `fetch_recipes_result`: Result from fetch_recipes workflow
- `catalog_recipe_result`: Result from catalog_recipe workflow
- `response`: Final response text for the user
- `success`: Boolean indicating operation success
- `error_message`: Error details if operation failed

## Intent Classification

The LLM identifies intent based on user phrasing:

### fetch_recipes Examples:
- "What can I make with chicken and rice?"
- "Show me Italian recipes"
- "I have tomatoes and cheese"
- "Find me an easy dinner recipe"

### catalog_recipe Examples:
- "Add this recipe: https://example.com/recipe"
- "Catalog https://tasty.co/chocolate-cake"
- "Save this recipe link"
- "Import recipe from https://..."

## Usage

### Direct API

```python
from agents.orchestrator.graph import graph

# Search for recipes
result = graph.invoke({
    "user_input": "I have chicken and rice. What can I make?"
})

print(result["response"])  # AI recommendations

# Add a recipe
result = graph.invoke({
    "user_input": "Add this recipe: https://example.com/pasta"
})

print(result["response"])  # Success/error message
```

### In Streamlit App

The Streamlit app automatically uses the orchestrator for all user inputs, supporting both voice and text input.

## Benefits

1. **Single Entry Point**: Users don't need to know which workflow to use
2. **Natural Language**: No special commands or syntax required
3. **Cost Effective**: Uses cheap LLM for routing, expensive models only when needed
4. **Extensible**: Easy to add new workflows in the future

## Future Enhancements

Potential new intents to add:
- `edit_recipe` - Modify existing recipes
- `delete_recipe` - Remove recipes from database
- `meal_plan` - Generate weekly meal plans
- `shopping_list` - Create shopping lists from recipes
