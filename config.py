"""
kairon/config.py
Loads environment variables and provides a single typed Config object.
Zero required keys — everything has a safe default.
"""
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path

# Load .env file if present (without python-dotenv dependency)
def _load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_env_file()


def _bool(val: str) -> bool:
    return str(val).lower() in ("1", "true", "yes", "on")

def _float(val: str, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    # LLM
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3.2"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    # Market data
    fred_api_key: str = field(default_factory=lambda: os.getenv("FRED_API_KEY", ""))
    brave_api_key: str = field(default_factory=lambda: os.getenv("BRAVE_SEARCH_API_KEY", ""))
    serper_api_key: str = field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""))

    # Social
    reddit_client_id: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", ""))
    reddit_user_agent: str = field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "kairon/1.0"))

    # Portfolio
    portfolio_capital: float = field(default_factory=lambda: _float(os.getenv("PORTFOLIO_CAPITAL", "100000"), 100000.0))
    base_currency: str = field(default_factory=lambda: os.getenv("BASE_CURRENCY", "USD"))
    max_position_pct: float = field(default_factory=lambda: _float(os.getenv("MAX_POSITION_PCT", "0.25"), 0.25))
    max_drawdown_pct: float = field(default_factory=lambda: _float(os.getenv("MAX_DRAWDOWN_PCT", "0.10"), 0.10))
    min_net_profit_pct: float = field(default_factory=lambda: _float(os.getenv("MIN_NET_PROFIT_PCT", "0.005"), 0.005))

    # Tax
    tax_region: str = field(default_factory=lambda: os.getenv("TAX_REGION", "US"))
    short_term_tax_rate: float = field(default_factory=lambda: _float(os.getenv("SHORT_TERM_TAX_RATE", "0.37"), 0.37))
    long_term_tax_rate: float = field(default_factory=lambda: _float(os.getenv("LONG_TERM_TAX_RATE", "0.20"), 0.20))
    tax_year_days: int = field(default_factory=lambda: int(os.getenv("TAX_YEAR_DAYS", "365")))
    state_tax_rate: float = field(default_factory=lambda: _float(os.getenv("STATE_TAX_RATE", "0.05"), 0.05))

    # Infrastructure
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///kairon.db"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    data_refresh_minutes: int = field(default_factory=lambda: int(os.getenv("DATA_REFRESH_INTERVAL_MINUTES", "15")))

    # Feature flags
    enable_finbert: bool = field(default_factory=lambda: _bool(os.getenv("ENABLE_FINBERT", "false")))
    enable_chromadb: bool = field(default_factory=lambda: _bool(os.getenv("ENABLE_CHROMADB", "false")))
    enable_redis: bool = field(default_factory=lambda: _bool(os.getenv("ENABLE_REDIS", "false")))
    first_run: bool = field(default_factory=lambda: _bool(os.getenv("FIRST_RUN", "true")))

    # Derived helpers
    @property
    def has_llm(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.llm_provider == "ollama":
            return True  # assume running; checked at startup
        return False

    @property
    def has_fred(self) -> bool:
        return bool(self.fred_api_key)

    @property
    def has_brave(self) -> bool:
        return bool(self.brave_api_key)

    @property
    def db_path(self) -> str:
        """Extract SQLite file path from DATABASE_URL."""
        url = self.database_url
        if url.startswith("sqlite:///"):
            return url[len("sqlite:///"):]
        return "kairon.db"


# Singleton
cfg = Config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, cfg.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kairon")
