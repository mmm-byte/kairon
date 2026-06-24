"""IPT loader and registry."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aurex.core.primitives import Mode
from aurex.rules.hot_reload import HotReloader
from aurex.rules.store import RuleStore


@dataclass
class IPT:
    ipt_id: str
    name: str
    mode: Mode
    asset_universe: list[str] = field(default_factory=list)
    description: str = ""
    version: int = 1
    root: Path = field(default=None)  # type: ignore[assignment]
    rule_store: RuleStore | None = None
    hot_reloader: HotReloader | None = None
    endpoints: dict = field(default_factory=dict)

    def start_hot_reload(self) -> None:
        if self.rule_store and not self.hot_reloader:
            self.hot_reloader = HotReloader(self.rule_store)
            self.hot_reloader.start()

    def stop_hot_reload(self) -> None:
        if self.hot_reloader:
            self.hot_reloader.stop()
            self.hot_reloader = None


def load_ipt(root: Path) -> IPT:
    root = Path(root)
    cfg_path = root / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"IPT config.json missing at {cfg_path}")
    data = json.loads(cfg_path.read_text())

    endpoints_path = root / "mcp_endpoints.json"
    endpoints = json.loads(endpoints_path.read_text()) if endpoints_path.exists() else {"endpoints": {}}

    store = RuleStore(root)
    return IPT(
        ipt_id=data["ipt_id"],
        name=data.get("name", data["ipt_id"]),
        mode=Mode(data.get("mode", "SANDBOX")),
        asset_universe=data.get("asset_universe", []),
        description=data.get("description", ""),
        version=data.get("version", 1),
        root=root,
        rule_store=store,
        endpoints=endpoints.get("endpoints", {}),
    )


class IPTRegistry:
    """In-memory registry of active IPTs."""

    def __init__(self) -> None:
        self._ipts: dict[str, IPT] = {}

    def register(self, ipt: IPT) -> None:
        self._ipts[ipt.ipt_id] = ipt

    def unregister(self, ipt_id: str) -> None:
        ipt = self._ipts.pop(ipt_id, None)
        if ipt:
            ipt.stop_hot_reload()

    def get(self, ipt_id: str) -> IPT:
        if ipt_id not in self._ipts:
            raise KeyError(f"IPT '{ipt_id}' not registered")
        return self._ipts[ipt_id]

    def all(self) -> list[IPT]:
        return list(self._ipts.values())