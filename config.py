import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
SUBSTACK_COOKIES = os.getenv("SUBSTACK_COOKIES", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
FETCH_HOUR = int(os.getenv("FETCH_HOUR", "8"))
FETCH_MINUTE = int(os.getenv("FETCH_MINUTE", "0"))
