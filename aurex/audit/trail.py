"""Audit trail — JSON-line append-only log + reader."""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AuditEvent:
    event_id: str
    event_type: str
    ipt_id: str
    actor: str
    timestamp: str = field(default_factory=_now)
    payload: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


class AuditTrail:
    """Thread-safe append-only audit log persisted as JSON lines."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.Lock()
        self._counter = 0

    def record(
        self,
        *,
        event_type: str,
        ipt_id: str,
        actor: str,
        payload: dict | None = None,
        tags: list[str] | None = None,
    ) -> AuditEvent:
        with self._lock:
            self._counter += 1
            evt = AuditEvent(
                event_id=f"EVT-{int(datetime.now(timezone.utc).timestamp() * 1000):013d}-{self._counter:06d}",
                event_type=event_type,
                ipt_id=ipt_id,
                actor=actor,
                payload=payload or {},
                tags=tags or [],
            )
            with self.path.open("a", encoding="utf-8") as f:
                f.write(evt.to_json() + "\n")
            return evt

    def read_all(self) -> list[AuditEvent]:
        if not self.path.exists():
            return []
        events: list[AuditEvent] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(AuditEvent(**json.loads(line)))
        return events

    def filter(self, **kw) -> Iterable[AuditEvent]:
        keep = []
        for e in self.read_all():
            if all(getattr(e, k, None) == v for k, v in kw.items()):
                keep.append(e)
        return keep

    def export_json(self) -> list[dict]:
        return [asdict(e) for e in self.read_all()]

    def export_csv(self) -> str:
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["event_id", "timestamp", "event_type", "ipt_id", "actor", "payload", "tags"])
        for e in self.read_all():
            writer.writerow(
                [e.event_id, e.timestamp, e.event_type, e.ipt_id, e.actor,
                 json.dumps(e.payload), ";".join(e.tags)]
            )
        return buf.getvalue()