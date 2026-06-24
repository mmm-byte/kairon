#!/usr/bin/env python3
"""
kairon/setup.py
One-command setup script. Run with: python kairon/setup.py
Checks all dependencies, initialises the database, tests data sources,
and gives clear instructions for any missing optional components.
"""
import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import json
from pathlib import Path


# ── Colour output ─────────────────────────────────────────────────────────────
class C:
    GREEN  = "\033[92m"
    AMBER  = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


def ok(msg):    print(f"  {C.GREEN}✓{C.RESET}  {msg}")
def warn(msg):  print(f"  {C.AMBER}!{C.RESET}  {msg}")
def err(msg):   print(f"  {C.RED}✗{C.RESET}  {msg}")
def info(msg):  print(f"  {C.BLUE}→{C.RESET}  {msg}")
def head(msg):  print(f"\n{C.BOLD}{msg}{C.RESET}")


# ── Dependency checks ─────────────────────────────────────────────────────────
REQUIRED_PACKAGES = {
    "pandas":           "pandas>=2.0.0",
    "numpy":            "numpy>=1.26.0",
    "yfinance":         "yfinance>=0.2.36",
    "streamlit":        "streamlit>=1.32.0",
    "fastapi":          "fastapi>=0.109.0",
    "uvicorn":          "uvicorn>=0.27.0",
    "sqlalchemy":       "sqlalchemy>=2.0.25",
    "apscheduler":      "apscheduler>=3.10.4",
    "duckduckgo_search":"duckduckgo-search>=5.0.0",
    "feedparser":       "feedparser>=6.0.0",
    "plotly":           "plotly>=5.18.0",
}

OPTIONAL_PACKAGES = {
    "openai":       ("OPENAI_API_KEY", "Cloud LLM explanations (GPT-4)"),
    "anthropic":    ("ANTHROPIC_API_KEY", "Cloud LLM explanations (Claude)"),
    "chromadb":     (None, "Enhanced vector similarity search"),
    "redis":        (None, "Distributed caching (Redis must be running)"),
    "praw":         ("REDDIT_CLIENT_ID", "Reddit social sentiment"),
    "torch":        (None, "FinBERT sentiment model (heavy download)"),
    "transformers": (None, "FinBERT sentiment model (heavy download)"),
}


def check_python_version():
    head("Python version")
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 11:
        ok(f"Python {major}.{minor} — supported")
    elif major >= 3 and minor >= 9:
        warn(f"Python {major}.{minor} — works but 3.11+ recommended")
    else:
        err(f"Python {major}.{minor} — requires 3.9+. Please upgrade.")
        sys.exit(1)


def check_required_packages():
    head("Required packages")
    missing = []
    for module, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module)
            ok(module)
        except ImportError:
            err(f"{module} — NOT INSTALLED")
            missing.append(pip_name)

    if missing:
        print()
        warn("Install missing packages with:")
        info(f"pip install {' '.join(missing)}")
        return False
    return True


def check_optional_packages():
    head("Optional packages")
    for module, (env_key, description) in OPTIONAL_PACKAGES.items():
        try:
            __import__(module)
            configured = True
            if env_key:
                configured = bool(os.getenv(env_key))
            if configured:
                ok(f"{module} — installed and configured ({description})")
            else:
                warn(f"{module} — installed but {env_key} not set ({description})")
        except ImportError:
            info(f"{module} — optional, not installed ({description})")


def check_env_file():
    head("Environment configuration")
    env_path = Path(".env")
    example  = Path("kairon/.env.example") if not Path(".env.example").exists() else Path(".env.example")

    if env_path.exists():
        ok(".env file found")
        # Check which keys are set
        keys_set = set()
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    if v.strip():
                        keys_set.add(k.strip())

        optional_keys = ["FRED_API_KEY", "BRAVE_SEARCH_API_KEY", "OPENAI_API_KEY",
                          "ANTHROPIC_API_KEY", "REDDIT_CLIENT_ID"]
        for key in optional_keys:
            if key in keys_set:
                ok(f"  {key} — configured")
            else:
                info(f"  {key} — not set (optional)")
    else:
        warn(".env not found — creating from .env.example")
        if example.exists():
            shutil.copy(str(example), ".env")
            ok("Created .env from template. Edit it to add your API keys (all optional).")
        else:
            err(".env.example not found. Run from the kairon project root directory.")


def check_ollama():
    head("Local LLM (Ollama)")
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            headers={"User-Agent": "kairon-setup/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        if models:
            ok(f"Ollama running — models: {', '.join(models[:3])}")
        else:
            warn("Ollama running but no models downloaded")
            info("Run: ollama pull llama3.2")
    except Exception:
        warn("Ollama not running — AI explanations will use template fallback")
        info("Install Ollama from: https://ollama.com")
        info("Then run: ollama pull llama3.2")
        info("(Optional — system works without it)")


def init_database():
    head("Database")
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from kairon.db.database import init_db
        init_db()
        ok("SQLite database initialised (kairon.db)")
    except Exception as e:
        err(f"Database init failed: {e}")


def check_data_sources():
    head("Data sources")
    try:
        from kairon.data.market_data import _generate_demo_data, ASSETS
        result = _generate_demo_data("GC=F", ASSETS["GC=F"])
        price  = float(result["df"]["close"].iloc[-1])
        ok(f"Demo data — Gold: ${price:,.2f} (simulation)")

        # Try Yahoo Finance if network available
        try:
            import yfinance as yf
            df = yf.download("GC=F", period="5d", progress=False)
            if not df.empty:
                ok(f"Yahoo Finance — Gold: ${float(df['Close'].iloc[-1]):,.2f} (live)")
            else:
                warn("Yahoo Finance — no data returned (will use demo data)")
        except Exception:
            warn("Yahoo Finance — unavailable (will use demo data)")

    except Exception as e:
        err(f"Data source check failed: {e}")


def run_smoke_test():
    head("Smoke test (full pipeline)")
    try:
        import tempfile, os
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        os.environ["DATABASE_URL"] = f"sqlite:///{tf.name}"

        from kairon.db.database import init_db
        init_db()

        from kairon.engine.analyzer import analyze
        result = analyze("GC=F", "commodities", capital_usd=20000)
        decision = result.get("decision")
        conf     = result.get("confidence", 0) * 100
        ok(f"Full pipeline — Gold: {decision} ({conf:.0f}% confidence)")

        os.remove(tf.name)
    except Exception as e:
        err(f"Smoke test failed: {e}")


def print_launch_instructions():
    head("Launch instructions")
    print(f"""
  {C.BOLD}Streamlit UI (recommended):{C.RESET}
    streamlit run kairon/ui/app.py
    → Opens at http://localhost:8501

  {C.BOLD}FastAPI backend:{C.RESET}
    uvicorn kairon.api.main:app --reload --port 8000
    → API at http://localhost:8000/api/health
    → Docs at http://localhost:8000/docs

  {C.BOLD}Full Docker stack (API + UI + Scheduler + Redis):{C.RESET}
    docker-compose up
    → UI: http://localhost:8501
    → API: http://localhost:8000

  {C.BOLD}Background scheduler only:{C.RESET}
    python -m kairon.data.scheduler

  {C.BOLD}Run tests:{C.RESET}
    python kairon/tests/test_all.py

  {C.BOLD}Optional — add free API keys to .env:{C.RESET}
    FRED_API_KEY=        (fred.stlouisfed.org — better macro data)
    BRAVE_SEARCH_API_KEY=(api.search.brave.com — 2000 free/month)
    REDDIT_CLIENT_ID=    (reddit.com/prefs/apps — social sentiment)
""")


def main():
    print(f"\n{C.BOLD}{'='*50}{C.RESET}")
    print(f"{C.BOLD}  Kairon Setup — Financial Intelligence System{C.RESET}")
    print(f"{C.BOLD}{'='*50}{C.RESET}")

    check_python_version()
    all_required = check_required_packages()
    check_optional_packages()
    check_env_file()

    if all_required:
        check_ollama()
        init_database()
        check_data_sources()
        run_smoke_test()

    print_launch_instructions()

    print(f"\n{C.BOLD}{'='*50}{C.RESET}")
    if all_required:
        print(f"{C.GREEN}{C.BOLD}  Setup complete — Kairon is ready to launch.{C.RESET}")
    else:
        print(f"{C.AMBER}{C.BOLD}  Install missing packages first, then re-run setup.{C.RESET}")
    print(f"{C.BOLD}{'='*50}{C.RESET}\n")


if __name__ == "__main__":
    main()
