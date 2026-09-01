import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/free")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "deepseek/deepseek-chat-v3-0324:free")
SUBSTACK_COOKIES = os.getenv("SUBSTACK_COOKIES", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
FETCH_HOUR = int(os.getenv("FETCH_HOUR", "8"))
FETCH_MINUTE = int(os.getenv("FETCH_MINUTE", "0"))
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_MODEL = os.getenv("GLM_MODEL", "glm-4.5-air")
