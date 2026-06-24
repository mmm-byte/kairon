"""
kairon/agents/base_agent.py
Abstract base class for all 8 agents. Enforces the standard output schema.
"""
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("kairon.agents")


@dataclass
class AgentSignal:
    """Standard output schema for every agent."""
    agent_name:   str
    signal:       float          # -1.0 to +1.0
    direction:    str            # "UP" | "DOWN" | "HOLD"
    confidence:   float          # 0.0 to 1.0
    reasoning:    str
    raw_data:     dict = field(default_factory=dict)
    elapsed_ms:   float = 0.0
    error:        Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.error is None and -1.0 <= self.signal <= 1.0

    def to_dict(self) -> dict:
        return {
            "agent":      self.agent_name,
            "signal":     round(self.signal, 4),
            "direction":  self.direction,
            "confidence": round(self.confidence, 3),
            "reasoning":  self.reasoning,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "error":      self.error,
            **{f"raw_{k}": v for k, v in self.raw_data.items()},
        }

    @classmethod
    def error_signal(cls, agent_name: str, error: str) -> "AgentSignal":
        return cls(
            agent_name=agent_name,
            signal=0.0,
            direction="HOLD",
            confidence=0.0,
            reasoning=f"Agent error: {error}",
            error=error,
        )


def _direction(score: float) -> str:
    if score > 0.15:  return "UP"
    if score < -0.15: return "DOWN"
    return "HOLD"


def _confidence_from_score(score: float) -> float:
    """Map abs(score) to a confidence in [0.4, 0.95]."""
    return round(min(0.95, 0.40 + abs(score) * 0.65), 3)


class BaseAgent(ABC):
    name: str = "base"

    def run(self, context: dict) -> AgentSignal:
        """Public entry point. Wraps _analyze with timing and error handling."""
        t0 = time.perf_counter()
        try:
            sig = self._analyze(context)
            sig.elapsed_ms = (time.perf_counter() - t0) * 1000
            return sig
        except Exception as e:
            logger.error(f"Agent {self.name} failed: {e}", exc_info=True)
            sig = AgentSignal.error_signal(self.name, str(e))
            sig.elapsed_ms = (time.perf_counter() - t0) * 1000
            return sig

    @abstractmethod
    def _analyze(self, context: dict) -> AgentSignal:
        """Override in each agent subclass."""
        ...
