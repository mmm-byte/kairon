"""Watch rule & guideline folders and reload the store on change.

Uses polling by default (no external dependency). If `watchdog` is installed,
prefers inotify-style events.
"""
from __future__ import annotations

import time
from pathlib import Path

from aurex.rules.store import RuleStore


try:  # Optional dependency
    from watchdog.events import FileSystemEventHandler  # type: ignore
    from watchdog.observers import Observer  # type: ignore

    _HAS_WATCHDOG = True
except ImportError:  # pragma: no cover
    _HAS_WATCHDOG = False


class _PollWatcher:
    """Tiny fallback poller — watches mtimes and triggers reload()."""

    def __init__(self, store: RuleStore, interval: float = 1.0) -> None:
        self.store = store
        self.interval = interval
        self._stop = False
        self._thread = None

    def start(self) -> None:
        import threading

        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._mtimes = self._snapshot()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _snapshot(self) -> dict[str, float]:
        snap: dict[str, float] = {}
        for sub in ("rules", "guidelines"):
            p = self.store.ipt_root / sub
            if not p.exists():
                continue
            for f in p.glob("*.json"):
                try:
                    snap[str(f)] = f.stat().st_mtime
                except OSError:
                    pass
        return snap

    def _loop(self) -> None:
        while not self._stop:
            time.sleep(self.interval)
            new = self._snapshot()
            if new != self._mtimes:
                self._mtimes = new
                self.store.reload()


if _HAS_WATCHDOG:

    class _ReloadHandler(FileSystemEventHandler):
        def __init__(self, store: RuleStore) -> None:
            self.store = store

        def on_modified(self, event):  # type: ignore[override]
            if not event.is_directory and str(event.src_path).endswith(".json"):
                self.store.reload()

        def on_created(self, event):  # type: ignore[override]
            self.on_modified(event)


class HotReloader:
    """Background file watcher that triggers RuleStore.reload()."""

    def __init__(self, store: RuleStore) -> None:
        self.store = store
        self._observer = None  # watchdog Observer or _PollWatcher

    def start(self) -> None:
        if self._observer:
            return
        if _HAS_WATCHDOG:
            handler = _ReloadHandler(self.store)
            obs = Observer()
            for sub in ("rules", "guidelines"):
                p: Path = self.store.ipt_root / sub
                if p.exists():
                    obs.schedule(handler, str(p), recursive=False)
            obs.daemon = True
            obs.start()
            self._observer = obs
        else:
            self._observer = _PollWatcher(self.store)
            self._observer.start()

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer = None

    # Convenience: blocking-loop for CLI/tests
    def run_forever(self) -> None:
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()