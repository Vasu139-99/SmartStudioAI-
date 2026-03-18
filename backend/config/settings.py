import os
from dotenv import load_dotenv

# Load .env from project root (one level above backend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(ROOT_DIR, ".env"))


class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    VOICE_ID = os.getenv("VOICE_ID", "FGY2WhTYpPnrIDTdsKH5")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")


    # DeAPI: supports multiple comma-separated keys for rotation
    _deapi_env = os.getenv("DEAPI_KEY", "")
    DEAPI_KEYS = [k.strip() for k in _deapi_env.split(",") if k.strip()]
    DEAPI_KEY = DEAPI_KEYS[0] if DEAPI_KEYS else ""  # backward compat

    # MySQL Database config
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "smartstudio_db")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_SSL = os.getenv("MYSQL_SSL", "false").lower() == "true"
    
    # Email config
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

    # Video dimensions
    DEFAULT_ASPECT_RATIO = "9:16"
    ASPECT_RATIOS = {
        "9:16": (432, 768),
        "16:9": (768, 432)
    }

    # Whisper config
    WHISPER_MODEL_SIZE = "small"
    MAX_CAPTION_WORDS = 3

    # Directories
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "output")
    TEMP_FOLDER = os.path.join(BASE_DIR, "temp")

    @classmethod
    def init_dirs(cls):
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(cls.TEMP_FOLDER, exist_ok=True)


settings = Settings()