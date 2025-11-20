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

# Recipe Matching Configuration
MIN_MATCH_THRESHOLD = float(os.getenv("MIN_MATCH_THRESHOLD", "30.0"))
MAX_RECIPES_TO_RETURN = int(os.getenv("MAX_RECIPES_TO_RETURN", "5"))
