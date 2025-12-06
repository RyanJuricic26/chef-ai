# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Database Configuration
DB_PATH = os.getenv("DB_PATH", "database/app.db")

# HTTP Request Configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; ChefAI-RecipeBot/1.0)")
