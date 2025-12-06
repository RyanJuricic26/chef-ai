# Chef AI Streamlit App

A multi-page Streamlit application for your personal recipe assistant.

## Pages

### 💬 Chat
Main chat interface to interact with Chef AI:
- Ask questions about recipes
- Search for recipes by ingredients
- Get cooking recommendations
- Add new recipes via URL
- Voice input support
- Text-to-speech responses

### 📚 Recipe Library
Browse and manage your recipe collection:
- View all recipes in a grid layout
- Star your favorite recipes
- Filter by difficulty, cuisine, and time
- Search by name or ingredient
- Expandable recipe details

## Running the App

```bash
# From the project root
streamlit run streamlit/0_💬_Chat.py
```

Or from the streamlit directory:
```bash
cd streamlit
streamlit run 0_💬_Chat.py
```

The app will open in your browser at `http://localhost:8501`

## Features

### Chat Features
- **Continuous conversation** - Message history persists across interactions
- **Voice input** - Record and transcribe speech using Whisper
- **Text-to-speech** - Listen to responses with Edge TTS
- **Clear history** - Reset conversation anytime

### Library Features
- **Star recipes** - Mark favorites (persisted in database)
- **Advanced filters** - Filter by difficulty, cuisine, max time
- **Search** - Find recipes by name or ingredient
- **Recipe cards** - Beautiful grid layout with expandable details
- **Persistent stars** - Your favorites are saved to the database

## Database

The app uses the SQLite database at `database/app.db` with these tables:
- `recipes` - Recipe information
- `ingredients` - Available ingredients
- `recipe_ingredients` - Recipe-ingredient relationships
- `starred_recipes` - User's starred recipes
- `users` - User information

## Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
DB_PATH=database/app.db
```

## Navigation

Use the sidebar to switch between pages:
- 💬 Chat - Main conversational interface
- 📚 Recipe Library - Browse and star recipes
