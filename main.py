#!/usr/bin/env python3
"""
kairon/main.py
Single entry point for Kairon.
Initialises everything, starts the scheduler in background,
then launches either the API server or the Streamlit UI.

Usage:
  python -m kairon.main              # launch Streamlit UI (default)
  python -m kairon.main --api        # launch FastAPI on port 8000
  python -m kairon.main --both       # launch API + UI together
  python -m kairon.main --scheduler  # scheduler only (for Docker)
  python -m kairon.main --check      # system health check and exit
"""
import sys
import os
import argparse
import logging
import subprocess
import threading
import time
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kairon.config import cfg
logger = logging.getLogger("kairon.main")


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════╗
║  ██╗  ██╗ █████╗ ██╗██████╗  ██████╗ ███╗   ██╗          ║
║  ██║ ██╔╝██╔══██╗██║██╔══██╗██╔═══██╗████╗  ██║          ║
║  █████╔╝ ███████║██║██████╔╝██║   ██║██╔██╗ ██║          ║
║  ██╔═██╗ ██╔══██║██║██╔══██╗██║   ██║██║╚██╗██║          ║
║  ██║  ██╗██║  ██║██║██║  ██║╚██████╔╝██║ ╚████║          ║
║  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝          ║
║  Financial Intelligence System  ·  v1.0                  ║
║  SIM MODE — For educational purposes only                  ║
╚═══════════════════════════════════════════════════════════╝
""")


def check_system() -> dict:
    """Run a system health check and report status of all components."""
    status = {}

    # Database
    try:
        from kairon.db.database import init_db, execute_one
        init_db()
        r = execute_one("SELECT COUNT(*) as n FROM predictions")
        status["database"] = {"ok": True, "predictions": r["n"] if r else 0}
    except Exception as e:
        status["database"] = {"ok": False, "error": str(e)}

    # Core imports
    for module, name in [
        ("kairon.data.market_data",     "market_data"),
        ("kairon.data.indicators",       "indicators"),
        ("kairon.engine.cost_engine",    "cost_engine"),
        ("kairon.engine.risk_engine",    "risk_engine"),
        ("kairon.agents.agents",         "agents"),
        ("kairon.intelligence.knowledge_base", "knowledge_base"),
    ]:
        try:
            __import__(module)
            status[name] = {"ok": True}
        except Exception as e:
            status[name] = {"ok": False, "error": str(e)}

    # Optional dependencies
    for lib in ["yfinance", "fastapi", "streamlit", "apscheduler"]:
        try:
            __import__(lib)
            status[f"lib_{lib}"] = {"ok": True}
        except ImportError:
            status[f"lib_{lib}"] = {"ok": False, "note": f"pip install {lib}"}

    # LLM provider
    if cfg.llm_provider == "ollama":
        try:
            import urllib.request
            urllib.request.urlopen(f"{cfg.ollama_base_url}/api/tags", timeout=3)
            status["llm_ollama"] = {"ok": True, "model": cfg.llm_model}
        except Exception:
            status["llm_ollama"] = {"ok": False, "note": "Install Ollama: ollama.com"}
    elif cfg.llm_provider == "openai" and cfg.openai_api_key:
        status["llm_openai"] = {"ok": True, "model": cfg.llm_model}
    else:
        status["llm"] = {"ok": True, "note": "Template fallback active (no LLM key)"}

    return status


def print_check_results(status: dict):
    print("\nSystem Health Check")
    print("=" * 50)
    all_ok = True
    for component, info in status.items():
        ok   = info.get("ok", False)
        mark = "✓" if ok else "✗"
        extra = info.get("error") or info.get("note") or info.get("predictions", "")
        extra_str = f"  ({extra})" if extra else ""
        print(f"  {mark}  {component:<25}{extra_str}")
        if not ok and not info.get("note"):   # note = optional, not critical
            all_ok = False
    print("=" * 50)
    print(f"  Status: {'READY' if all_ok else 'NEEDS ATTENTION'}")
    print()
    return all_ok


def start_background_scheduler():
    """Start the data refresh scheduler in a background thread."""
    try:
        from kairon.data.scheduler import start_scheduler
        sched = start_scheduler()
        if sched:
            logger.info("Background scheduler started")
            return sched
    except Exception as e:
        logger.warning(f"Scheduler could not start: {e}")
    return None


def run_first_refresh():
    """Run an immediate data refresh on startup so screens have data."""
    try:
        from kairon.data.scheduler import job_refresh_prices, job_refresh_macro
        logger.info("Running initial data refresh...")
        t1 = threading.Thread(target=job_refresh_prices, daemon=True)
        t2 = threading.Thread(target=job_refresh_macro, daemon=True)
        t1.start()
        t2.start()
        # Don't block startup — let these run in background
    except Exception as e:
        logger.debug(f"Initial refresh failed (non-fatal): {e}")


def launch_api(port: int = 8000, host: str = "0.0.0.0", reload: bool = False):
    """Launch the FastAPI server."""
    try:
        import uvicorn
        logger.info(f"Starting FastAPI on {host}:{port}")
        uvicorn.run(
            "kairon.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=cfg.log_level.lower(),
        )
    except ImportError:
        logger.error("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)


def launch_ui(port: int = 8501):
    """Launch the Streamlit UI."""
    ui_path = str(Path(__file__).parent / "ui" / "app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", ui_path,
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--theme.base", "dark",
        "--theme.primaryColor", "#00e676",
        "--theme.backgroundColor", "#080b0f",
        "--theme.secondaryBackgroundColor", "#0d1117",
        "--theme.textColor", "#e8edf5",
    ]
    logger.info(f"Starting Streamlit UI on port {port}")
    try:
        proc = subprocess.Popen(cmd)
        return proc
    except FileNotFoundError:
        logger.error("streamlit not installed. Run: pip install streamlit")
        sys.exit(1)


def launch_both(api_port: int = 8000, ui_port: int = 8501):
    """Launch API and UI side-by-side."""
    # Start API in background thread
    api_thread = threading.Thread(
        target=launch_api,
        kwargs={"port": api_port, "reload": False},
        daemon=True,
    )
    api_thread.start()
    time.sleep(2)   # Give API a moment to bind

    # Start UI in foreground (this blocks)
    ui_proc = launch_ui(ui_port)
    print(f"\n  Kairon is running:")
    print(f"  API:  http://localhost:{api_port}")
    print(f"  UI:   http://localhost:{ui_port}")
    print(f"\n  Press Ctrl+C to stop\n")
    try:
        ui_proc.wait()
    except KeyboardInterrupt:
        ui_proc.terminate()
        print("\nKairon stopped.")


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Kairon Financial Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m kairon.main              Launch Streamlit UI (default)
  python -m kairon.main --api        Launch FastAPI server
  python -m kairon.main --both       Launch API + UI together
  python -m kairon.main --scheduler  Background scheduler only
  python -m kairon.main --check      System health check
        """,
    )
    parser.add_argument("--api",       action="store_true", help="Launch FastAPI server")
    parser.add_argument("--both",      action="store_true", help="Launch API + UI together")
    parser.add_argument("--scheduler", action="store_true", help="Run scheduler only")
    parser.add_argument("--check",     action="store_true", help="Health check and exit")
    parser.add_argument("--api-port",  type=int, default=8000, help="API port (default 8000)")
    parser.add_argument("--ui-port",   type=int, default=8501, help="UI port (default 8501)")
    parser.add_argument("--no-scheduler", action="store_true", help="Skip background scheduler")
    args = parser.parse_args()

    # Always init DB first
    from kairon.db.database import init_db
    init_db()
    logger.info(f"Database ready: {cfg.db_path}")

    # Health check mode
    if args.check:
        status = check_system()
        ok = print_check_results(status)
        sys.exit(0 if ok else 1)

    # Start scheduler (unless disabled)
    scheduler = None
    if not args.no_scheduler and not args.scheduler:
        scheduler = start_background_scheduler()
        run_first_refresh()

    # Scheduler-only mode
    if args.scheduler:
        sched = start_background_scheduler()
        if sched:
            print("Kairon scheduler running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(30)
            except KeyboardInterrupt:
                sched.shutdown()
                print("Scheduler stopped.")
        sys.exit(0)

    # Launch selected mode
    if args.both:
        launch_both(args.api_port, args.ui_port)
    elif args.api:
        print(f"  API: http://localhost:{args.api_port}")
        print(f"  Docs: http://localhost:{args.api_port}/docs\n")
        launch_api(args.api_port, reload=True)
    else:
        # Default: Streamlit UI
        print(f"  UI: http://localhost:{args.ui_port}\n")
        proc = launch_ui(args.ui_port)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            print("\nKairon stopped.")


if __name__ == "__main__":
    main()
