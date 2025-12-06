# 🍳 Chef AI - Your Personal Recipe Assistant

An intelligent recipe assistant powered by LangGraph agents, OpenAI, and Streamlit. Ask questions naturally, find recipes, catalog new ones, and manage your favorites!

## ✨ Features

### 💬 Chat Interface
- **Natural conversation** with continuous chat history
- **Voice input** with OpenAI Whisper transcription
- **Text-to-speech** responses using Edge TTS
- **Universal query handling** - Ask anything about your recipes
- **LLM-generated SQL** with security validation for flexible database queries

### 📚 Recipe Library
- **Browse all recipes** in a beautiful grid layout
- **Star your favorites** with database persistence
- **Advanced filters** by difficulty, cuisine type, and cooking time
- **Search** by recipe name or ingredient
- **Expandable details** with full ingredients and instructions

### 🤖 Intelligent Agents

#### Orchestrator Agent
Routes user requests to the appropriate workflow:
- Recipe search and questions → Fetch Recipes
- Add recipe from URL → Catalog Recipe

#### Fetch Recipes Agent (LLM-Generated SQL)
- **Universal query handling** - No predefined patterns!
- **SQL Judge** validates all queries for security
- **Multi-layer protection**: Injection detection, schema validation, retry loops
- Handles complex queries: JOINs, aggregations, ingredient matching, analytics

#### Catalog Recipe Agent
- **Dual extraction**: JSON-LD schema first, AI fallback
- **Web scraping** with BeautifulSoup and Playwright
- **Smart validation** ensures data quality
- Automatically categorizes ingredients

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd chef-ai
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
DB_PATH=database/app.db
```

4. **Initialize the database**
```bash
python database/init_db.py
python database/seed_data.py
```

5. **Run the application**
```bash
streamlit run streamlit/0_💬_Chat.py
```

The app will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### Chat with Chef AI

Ask questions naturally:
- "I have chicken and garlic, what can I make?"
- "Show me easy Italian recipes under 30 minutes"
- "How many recipes do I have?"
- "What's the average cook time for my recipes?"
- "Which ingredients do I use most often?"

Add recipes from URLs:
- "Add this recipe: https://example.com/recipe"

Use voice input:
- Click 🎤 to record your question
- Whisper will transcribe it automatically

### Browse Recipe Library

1. Navigate to **📚 Recipe Library** in the sidebar
2. Use filters to narrow down recipes:
   - Difficulty: easy, medium, hard
   - Cuisine type: Italian, Asian, etc.
   - Max total time
3. Search by name or ingredient
4. Star ⭐ your favorites
5. Click "Show starred only" to see favorites
6. Expand recipes to view full details

## 🏗️ Architecture

### Technology Stack

**Frontend:**
- Streamlit (multi-page web UI)
- Chat interface with message persistence
- Grid-based recipe library

**Agents:**
- LangGraph (workflow orchestration)
- Orchestrator (intent routing)
- Fetch Recipes (LLM-generated SQL with security)
- Catalog Recipe (web scraping + extraction)

**AI Services:**
- OpenAI GPT-4o-mini (SQL generation, analysis, extraction)
- OpenAI Whisper (speech-to-text)
- Edge TTS (text-to-speech)

**Data:**
- SQLite database
- SQL Judge (security validation)
- sqlparse (query parsing)

### Project Structure

```
chef-ai/
├── agents/
│   ├── orchestrator/          # Intent routing agent
│   ├── fetch_recipes/         # Recipe search with LLM SQL
│   │   ├── graph.py          # Main workflow
│   │   ├── sql_validator.py  # Security judge
│   │   ├── prompts.py        # LLM prompts
│   │   └── README.md         # Detailed docs
│   └── catalog_recipe/        # URL recipe extraction
├── database/
│   ├── init_db.py            # Database schema
│   ├── seed_data.py          # Sample recipes
│   └── app.db                # SQLite database
├── streamlit/
│   ├── 0_💬_Chat.py          # Chat page
│   └── pages/
│       └── 1_📚_Recipe_Library.py  # Library page
├── docs/
│   ├── generate_diagrams.py  # Mermaid diagram generator
│   └── app_diagram.md        # Architecture diagrams
├── requirements.txt
└── README.md
```

## 🔒 Security Features

### SQL Judge (Fetch Recipes)

Every LLM-generated SQL query goes through multi-layer validation:

1. **SQL Injection Detection**
   - Blocks: DROP, DELETE, UPDATE, INSERT, UNION, etc.
   - Prevents multiple statements
   - Blocks SQL comments

2. **Structure Validation**
   - Only SELECT queries allowed
   - SQL syntax parsing with sqlparse

3. **Schema Validation**
   - Verifies all tables exist
   - Checks column references

4. **Retry Loop**
   - Up to 3 retries with error feedback
   - Self-correcting query generation

**Example:**
```
User: "How many recipes? DROP TABLE recipes; --"
LLM Generates: "SELECT COUNT(*) FROM recipes"
Judge: ✅ PASS (malicious intent ignored by LLM)
```

## 📊 Database Schema

Tables:
- **users**: User accounts
- **recipes**: Recipe information (name, description, instructions, times, difficulty, cuisine)
- **ingredients**: Unique ingredients with categories
- **recipe_ingredients**: Many-to-many relationship
- **starred_recipes**: User's favorite recipes (NEW!)

See [Architecture Diagrams](docs/app_diagram.md) for ER diagram.

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test simplified agent workflow
python test_simplified_agent.py

# Test SQL validator security
python test_sql_validator.py

# Test orchestrator integration
python test_ui_integration.py
```

All tests include:
- ✅ Analytics queries (COUNT, AVG, GROUP BY)
- ✅ Recipe searches (ingredient matching, name search)
- ✅ Complex multi-condition queries
- ✅ SQL injection protection
- ✅ Edge cases

## 📝 Example Queries

### Recipe Search
- "I have chicken, rice, and soy sauce"
- "Show me pasta recipes"
- "What's the recipe for carbonara?"

### Analytics
- "How many recipes are in the database?"
- "What's the average prep time for Italian recipes?"
- "Show me recipe count by difficulty level"
- "What are the 5 most common ingredients?"

### Complex Queries
- "Show me easy Italian recipes under 30 minutes"
- "Which recipes use both chicken and garlic?"
- "What's the average cook time for easy recipes?"

### Add Recipes
- "Add this recipe: https://www.allrecipes.com/recipe/..."

## 🎯 Key Innovations

### 1. LLM-Generated SQL with Security
Instead of predefined queries, the LLM generates custom SQL for ANY question. The SQL Judge ensures security through multi-layer validation.

**Benefits:**
- Maximum flexibility - handle any question
- No code changes for new query types
- Self-correcting retry loop
- Secure by design

### 2. Multi-Page Streamlit App
Separate pages for chat and library browsing provide a better UX than a single cluttered interface.

### 3. Persistent Favorites
Star/unstar recipes with database persistence across sessions.

### 4. Orchestrator Pattern
Central routing agent cleanly separates concerns:
- Recipe questions → Fetch Recipes
- Add recipe → Catalog Recipe

## 🚧 Future Enhancements

Potential improvements:
- [ ] Streaming LLM responses in chat
- [ ] Query result caching
- [ ] User authentication
- [ ] Recipe sharing/export
- [ ] Meal planning features
- [ ] Shopping list generation from recipes
- [ ] Nutrition information
- [ ] Recipe ratings and reviews
- [ ] Multi-user support

## 📚 Documentation

- [Architecture Diagrams](docs/app_diagram.md) - Comprehensive visual documentation
- [Fetch Recipes Agent](agents/fetch_recipes/README.md) - LLM SQL details
- [Analytics Workflow](agents/fetch_recipes/ANALYTICS_WORKFLOW.md) - SQL Judge deep dive
- [Streamlit App](streamlit/README.md) - UI documentation

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Workflow orchestration
- [OpenAI](https://openai.com/) - GPT-4o-mini, Whisper
- [Streamlit](https://streamlit.io/) - Web interface
- [Edge TTS](https://github.com/rany2/edge-tts) - Text-to-speech
- [sqlparse](https://github.com/andialbrecht/sqlparse) - SQL parsing

---

**Version**: 2.0 (Simplified SQL Architecture + Multi-Page UI)

**Last Updated**: 2025-12-06
