"""Rule / Guideline storage with hot reload."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Iterable

from aurex.core.primitives import Guideline, Rule, Severity


class RuleStore:
    """Loads, validates, and hot-reloads rules & guidelines for an IPT."""

    def __init__(self, ipt_root: Path) -> None:
        self.ipt_root = Path(ipt_root)
        self._rules: dict[str, Rule] = {}
        self._guidelines: dict[str, Guideline] = {}
        self._lock = RLock()
        self.reload()

    # ---------- public API ----------
    def reload(self) -> None:
        with self._lock:
            self._rules = {r.id: r for r in self._load_dir(self.ipt_root / "rules", Rule)}
            self._guidelines = {
                g.id: g for g in self._load_dir(self.ipt_root / "guidelines", Guideline)
            }

    @property
    def rules(self) -> list[Rule]:
        with self._lock:
            return list(self._rules.values())

    @property
    def guidelines(self) -> list[Guideline]:
        with self._lock:
            return list(self._guidelines.values())

    def get_rule(self, rule_id: str) -> Rule | None:
        with self._lock:
            return self._rules.get(rule_id)

    def get_guideline(self, guideline_id: str) -> Guideline | None:
        with self._lock:
            return self._guidelines.get(guideline_id)

    def upsert_rule(self, rule: Rule) -> None:
        with self._lock:
            path = self.ipt_root / "rules" / f"{rule.id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(rule), indent=2))
            self._rules[rule.id] = rule

    def upsert_guideline(self, guideline: Guideline) -> None:
        with self._lock:
            path = self.ipt_root / "guidelines" / f"{guideline.id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(guideline), indent=2))
            self._guidelines[guideline.id] = guideline

    # ---------- internals ----------
    def _load_dir(self, path: Path, cls: type) -> Iterable:
        if not path.exists():
            return []
        results: list = []
        for f in sorted(path.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                if cls is Rule:
                    data["severity"] = Severity(data.get("severity", "hard"))
                results.append(cls(**data))
            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                # Reject malformed rules per the spec
                raise ValueError(f"Malformed {cls.__name__} in {f}: {exc}") from exc
        return results