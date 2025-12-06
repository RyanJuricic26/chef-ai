# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI Configuration - using cheap model for routing
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "gpt-4o-mini")  # Cheap model for intent classification
