"""
Generate Mermaid diagrams for Chef AI application workflows
"""
import sys
import os
import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath('..'))

def main():
    print("Generating Chef AI Application Diagrams...")
    print("=" * 60)

    # Import workflows
    from agents.fetch_recipes.graph import graph as fetch_recipes_graph
    from agents.recipe_catalog.graph import graph as recipe_catalog_graph

    # Generate Mermaid diagrams
    print("\n1. Generating Fetch Recipes workflow diagram...")
    fetch_recipes_mermaid = fetch_recipes_graph.get_graph().draw_mermaid()

    print("2. Generating Recipe Catalog workflow diagram...")
    recipe_catalog_mermaid = recipe_catalog_graph.get_graph().draw_mermaid()

    print("3. Creating Streamlit application flow diagram...")
    streamlit_mermaid = """graph TD
    Start([User Opens App]) --> Init[Initialize Session State]
    Init --> VoiceInput{Voice Input?}

    VoiceInput -->|Yes| AudioRecord[st.audio_input: Record Audio]
    AudioRecord --> Whisper[OpenAI Whisper: Transcribe]
    Whisper --> UpdateText[Update query_text in Session State]
    UpdateText --> TextArea

    VoiceInput -->|No| TextArea[Text Area Input]

    TextArea --> FindButton{Click Find Recipes?}
    FindButton -->|No| Wait[Wait for User Action]
    Wait --> VoiceInput

    FindButton -->|Yes| InvokeGraph[Invoke fetch_recipes Graph]
    InvokeGraph --> ProcessResults[Process & Store Results]
    ProcessResults --> DisplayRecs[Display Recommendations]

    DisplayRecs --> TTSButton{Click TTS Button?}
    TTSButton -->|Yes| EdgeTTS[Edge TTS: Generate Audio]
    EdgeTTS --> PlayAudio[st.audio: Play Audio]
    PlayAudio --> DisplayRecipes

    TTSButton -->|No| DisplayRecipes[Display Recipe Cards]
    DisplayRecipes --> ExpandRecipe{Expand Recipe?}
    ExpandRecipe -->|Yes| ShowDetails[Show Ingredients & Instructions]
    ShowDetails --> End([Session Continues])
    ExpandRecipe -->|No| End

    style Start fill:#e1f5e1
    style InvokeGraph fill:#ffe1e1
    style EdgeTTS fill:#e1e5ff
    style Whisper fill:#e1e5ff
    style End fill:#ffe1f5"""

    # Create comprehensive documentation
    markdown_content = f"""# Chef AI Application Architecture

This document provides visual diagrams of the Chef AI application architecture, including all workflows and user interactions.

---

## Table of Contents

1. [Streamlit Application Flow](#streamlit-application-flow)
2. [Fetch Recipes Workflow](#fetch-recipes-workflow)
3. [Recipe Catalog Workflow](#recipe-catalog-workflow)
4. [System Overview](#system-overview)

---

## Streamlit Application Flow

The Streamlit app provides a voice-enabled interface for users to interact with the Chef AI system.

### Features:
- **Voice Input**: Uses `st.audio_input` to record user voice
- **Speech-to-Text**: OpenAI Whisper transcribes audio to text
- **Recipe Search**: Invokes the fetch_recipes workflow
- **Text-to-Speech**: Edge TTS reads recommendations aloud
- **Interactive Recipe Cards**: Expandable recipe details with ingredients and instructions

```mermaid
{streamlit_mermaid}
```

---

## Fetch Recipes Workflow

This LangGraph workflow processes user queries to find matching recipes from the database.

### Workflow Steps:
1. **Classify Query**: AI determines if user wants to search by ingredients, recipe name, or general browse
2. **Fetch Recipes**: Queries database based on classification
   - **Ingredients Mode**: Extracts ingredients from query, calculates match percentages
   - **Name Mode**: Searches by recipe name or cuisine type
   - **General Mode**: Returns all recipes
3. **Filter & Rank**: Applies match threshold and ranks by relevance
4. **Generate Recommendations**: LLM creates personalized, conversational recommendations

```mermaid
{fetch_recipes_mermaid}
```

### Key Features:
- **Smart Classification**: No hardcoded keywords - AI understands natural language
- **Ingredient Matching**: Calculates percentage match and shows missing ingredients
- **Contextual Recommendations**: LLM provides helpful cooking tips and alternatives

---

## Recipe Catalog Workflow

This LangGraph workflow extracts recipes from URLs and adds them to the database.

### Workflow Steps:
1. **Fetch Webpage**: Downloads HTML from recipe URL
2. **Parse JSON-LD**: Attempts to extract structured Recipe schema (preferred method)
3. **Extract with LLM**: Fallback to AI extraction if JSON-LD not available
4. **Validate Recipe Data**: Ensures all required fields are present and valid
5. **Save to Database**: Persists recipe with ingredients and relationships

```mermaid
{recipe_catalog_mermaid}
```

### Key Features:
- **Dual Extraction**: Tries structured data first, falls back to AI parsing
- **Comprehensive Validation**: Ensures data quality before database insert
- **Smart Categorization**: AI categorizes ingredients and infers difficulty levels
- **URL Preservation**: Stores source URL for reference

---

## System Overview

### Architecture Components:

```mermaid
graph LR
    User([User]) -->|Voice/Text| StreamlitApp[Streamlit App]
    StreamlitApp -->|Audio| Whisper[OpenAI Whisper]
    Whisper -->|Text| StreamlitApp

    StreamlitApp -->|Query| FetchRecipes[Fetch Recipes Workflow]
    FetchRecipes -->|SQL| Database[(SQLite Database)]
    Database -->|Results| FetchRecipes
    FetchRecipes -->|Recommendations| StreamlitApp

    StreamlitApp -->|Text| EdgeTTS[Edge TTS]
    EdgeTTS -->|Audio| StreamlitApp
    StreamlitApp -->|Audio| User

    RecipeURL[Recipe URL] -->|URL| RecipeCatalog[Recipe Catalog Workflow]
    RecipeCatalog -->|Fetch| WebPage[Recipe Webpage]
    WebPage -->|HTML| RecipeCatalog
    RecipeCatalog -->|Parse/Extract| LLM[OpenAI GPT]
    LLM -->|Structured Data| RecipeCatalog
    RecipeCatalog -->|Insert| Database

    style User fill:#e1f5e1
    style Database fill:#ffe1e1
    style LLM fill:#e1e5ff
    style Whisper fill:#e1e5ff
    style EdgeTTS fill:#e1e5ff
```

### Technology Stack:

- **Frontend**: Streamlit (Python-based web UI)
- **Workflows**: LangGraph (orchestration framework)
- **LLM**: OpenAI GPT-4o-mini (query classification, extraction, recommendations)
- **Speech-to-Text**: OpenAI Whisper (voice transcription)
- **Text-to-Speech**: Edge TTS (audio generation)
- **Database**: SQLite (recipe and ingredient storage)
- **Web Scraping**: BeautifulSoup, Requests (HTML parsing)

### Database Schema:

```mermaid
erDiagram
    RECIPES ||--o{{ RECIPE_INGREDIENTS : contains
    INGREDIENTS ||--o{{ RECIPE_INGREDIENTS : used_in

    RECIPES {{
        int id PK
        string name
        string description
        text instructions
        int prep_time
        int cook_time
        int servings
        string difficulty
        string cuisine_type
        string url
        timestamp created_at
    }}

    INGREDIENTS {{
        int id PK
        string name UK
        string category
    }}

    RECIPE_INGREDIENTS {{
        int id PK
        int recipe_id FK
        int ingredient_id FK
        string quantity
        string unit
        string notes
    }}
```

---

## Workflow Integration

### User Journey: Finding a Recipe

1. User opens Streamlit app
2. User either:
   - Records voice: "I have chicken, rice, and soy sauce"
   - Types query in text area
3. App invokes `fetch_recipes` workflow:
   - Classifies as "ingredients" mode
   - Extracts: chicken, rice, soy sauce
   - Queries database for matching recipes
   - Ranks by match percentage
   - Generates conversational recommendations
4. App displays:
   - AI-generated recommendations
   - Top matching recipes with details
   - TTS option to read aloud

### Admin Journey: Adding a Recipe

1. Admin provides recipe URL
2. `recipe_catalog` workflow:
   - Fetches webpage HTML
   - Tries JSON-LD extraction first
   - Falls back to LLM if needed
   - Validates all fields
   - Saves to database
3. Recipe now available for user searches

---

## Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Save to file
    output_path = 'app_diagram.md'
    with open(output_path, 'w') as f:
        f.write(markdown_content)

    print(f"\n✅ Diagrams saved to {output_path}")
    print(f"\nFile size: {len(markdown_content):,} characters")
    print(f"Total diagrams: 5")
    print("\nDiagrams included:")
    print("  1. Streamlit Application Flow")
    print("  2. Fetch Recipes Workflow")
    print("  3. Recipe Catalog Workflow")
    print("  4. System Overview")
    print("  5. Database Schema")
    print("\n" + "=" * 60)
    print("You can view the diagrams by:")
    print("  - Opening app_diagram.md in VS Code or GitHub")
    print("  - Using Mermaid live editor: https://mermaid.live")
    print("=" * 60)


if __name__ == "__main__":
    main()
