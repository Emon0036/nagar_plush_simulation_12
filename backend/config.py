import os
from pathlib import Path
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    # Load root .env file
    root_dir = Path(__file__).resolve().parent.parent
    env_file = root_dir / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()
except ImportError:
    pass

@dataclass
class Config:
    # Aiven MySQL Cloud Server configuration
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "4000"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "")
    MYSQL_SSL_REQUIRED: bool = True
    REQUIRE_MYSQL: bool = os.getenv("REQUIRE_MYSQL", "true").lower() in ("1", "true", "yes") or bool(os.getenv("VERCEL"))

    # Local fallback SQLite database
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "ecosim_local.db")

    # Simulation defaults
    DEFAULT_AGENT_COUNT: int = 50
    DEFAULT_FOOD_PRICE_INDEX: float = 1.0
    DEFAULT_TAX_RATE: float = 0.10
    DEFAULT_INFLATION_RATE: float = 0.05
    CURRENCY_SYMBOL: str = "BDT"

config = Config()
