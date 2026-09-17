import os

from dotenv import load_dotenv


load_dotenv()


LLM_PROVIDER = os.getenv(
    "LLM_PROVIDER",
    "ollama",
)

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama3.2",
)

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
)

LLM_TIMEOUT = float(
    os.getenv("LLM_TIMEOUT", "30")
)

MCP_TOOL_TIMEOUT = float(
    os.getenv("MCP_TOOL_TIMEOUT", "60")
)

RAG_TIMEOUT = float(
    os.getenv("RAG_TIMEOUT", "60")
)

MAX_RETRIES = int(
    os.getenv("MAX_RETRIES", "2")
)

RETRY_BACKOFF_BASE = float(
    os.getenv("RETRY_BACKOFF_BASE", "0.5")
)

RETRY_BACKOFF_MAX = float(
    os.getenv("RETRY_BACKOFF_MAX", "5.0")
)


# Database configuration
DB_HOST = os.getenv(
    "DB_HOST",
    "localhost",
)

DB_PORT = os.getenv(
    "DB_PORT",
    "5432",
)

DB_NAME = os.getenv(
    "DB_NAME",
    "opspilot",
)

DB_USER = os.getenv(
    "DB_USER",
    "",
)

DB_PASSWORD = os.getenv(
    "DB_PASSWORD",
    "",
)


DB_ECHO = os.getenv(
    "DB_ECHO",
    "false",
).lower() == "true"