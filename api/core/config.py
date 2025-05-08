import os
from enum import Enum

from dotenv import load_dotenv


class Environment(str, Enum):
    """Application environment types.

    Defines the possible environments the application can run in:
    development, staging, production, and test.
    """

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TEST = "test"


def get_environment() -> Environment:
    """Get the current environment.

    Returns:
        Environment: The current environment (development, production, or test)
    """
    match os.getenv("APP_ENV", "development").lower():
        case "production":
            return Environment.PRODUCTION
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


def parse_list_from_env(env_key, default=None):
    """Parse a comma-separated list from an environment variable."""
    value = os.getenv(env_key)
    if not value:
        return default or []

    # Remove quotes if they exist
    value = value.strip("\"'")
    # Handle single value case
    if "," not in value:
        return [value]
    # Split comma-separated values
    return [item.strip() for item in value.split(",") if item.strip()]


def load_env_file():
    """Load environment-specific .env file."""
    env = get_environment()
    print(f"Loading environment: {env}")
    base_dir = os.path.dirname(os.path.dirname(__file__))

    # Define env files in priority order
    env_files = [
        os.path.join(base_dir, f".env.{env.value}"),
        os.path.join(base_dir, ".env"),
    ]

    # Load the first env file that exists
    for env_file in env_files:
        if os.path.isfile(env_file):
            load_dotenv(dotenv_path=env_file)
            print(f"Loaded environment from {env_file}")
            return env_file

    # Fall back to default if no env file found
    return None


class Settings:

    def __init__(self):
        self.ENVIRONMENT = get_environment()
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "ChapChapAI")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
        self.DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "t", "yes")

        # CORS Settings
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])

        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "console")
        self.LOG_JSON_FORMAT = os.getenv("LOG_JSON_FORMAT", "false").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )

        # Postgres Configuration
        self.POSTGRES_URL = os.getenv(
            "POSTGRES_URL", "postgres://postgres:postgres@localhost:54322/chapchap"
        )
        self.POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
        self.POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
        self.POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "chapchap")

        # LLM Settings
        self.LLM_MODEL = os.getenv("LLM_MODEL", "google_genai:gemini-2.0-flash")
        self.DEFAULT_LLM_TEMPERATURE = float(
            os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2")
        )
        self.LLM_DB_POOL_SIZE = int(os.getenv("LLM_DB_POOL_SIZE", "10"))
        self.CHECKPOINT_TABLES = [
            "checkpoint_blobs",
            "checkpoint_writes",
            "checkpoints",
        ]


# Create settings instance
load_env_file()
settings = Settings()
