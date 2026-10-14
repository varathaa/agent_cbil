import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

_root = logging.getLogger("cibil")
if not _root.handlers:
    _fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    _file = RotatingFileHandler(LOG_DIR / "cibil_agent.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    _file.setFormatter(_fmt)
    _console = logging.StreamHandler()
    _console.setFormatter(_fmt)
    _root.addHandler(_file)
    _root.addHandler(_console)
    _root.setLevel(LOG_LEVEL)

ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")
ORACLE_DSN = os.getenv("ORACLE_DSN")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
