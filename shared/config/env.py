import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_file = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_file)

# Hub Configuration
HUB_HOST = os.getenv("HUB_HOST", "localhost")
HUB_PORT = int(os.getenv("HUB_PORT", "8000"))
HUB_URL = os.getenv("HUB_URL", f"http://{HUB_HOST}:{HUB_PORT}")

# Agent Configuration
AGENT_ID = os.getenv("AGENT_ID", "agent-001")
AGENT_HOST = os.getenv("AGENT_HOST", "localhost")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exostack.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Model Configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "microsoft/DialoGPT-medium")
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models")
MAX_MODEL_MEMORY = int(os.getenv("MAX_MODEL_MEMORY", "4096"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "./logs/exostack.log")

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
API_KEY_EXPIRES_DAYS = int(os.getenv("API_KEY_EXPIRES_DAYS", "30"))

# Resource Management
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "300"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "10"))

# Development Configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
