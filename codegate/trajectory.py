"""Trajectory recorder — captures every backend stage of a CodeGate analysis.

Inspired by DeepSeek-harness style "trajectory" views: an ordered, inspectable
timeline of what the analyzer actually did, with machine-readable payloads so
a developer can see the AST, CFG, and decisions behind a verdict.

Usage:
    t = Trajectory()
    with t.step("parse", "Parse source with Python ast") as s:
        tree = ast.parse(source)
        s.summary = f"{len(tree.body)} top-level statements"
        s.data = {...}
    steps = t.finish()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    id: int = 0
    phase: str = ""          # parse | desugar | cfg | resources | paths | exceptions | fix
    title: str = ""
    status: str = "ok"       # ok | error | skipped | warn
    detail: str = ""         # one-line human summary
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "durationMs": round(self.duration_ms, 2),
            "data": self.data,
        }


class Trajectory:
    def __init__(self) -> None:
        self._steps: list[Step] = []
        self._next_id = 1

    def add(self, phase: str, title: str, *, status: str = "ok",
            detail: str = "", data: dict[str, Any] | None = None,
            duration_ms: float = 0.0) -> Step:
        step = Step(
            id=self._next_id,
            phase=phase,
            title=title,
            status=status,
            detail=detail,
            duration_ms=duration_ms,
            data=data or {},
        )
        self._next_id += 1
        self._steps.append(step)
        return step

    class _StepContext:
        def __init__(self, traj: "Trajectory", phase: str, title: str):
            self._traj = traj
            self._phase = phase
            self._title = title
            self._t0 = 0.0
            self.step: Step | None = None

        def __enter__(self) -> Step:
            self._t0 = time.perf_counter()
            self.step = self._traj.add(self._phase, self._title)
            return self.step

        def __exit__(self, exc_type, exc, tb) -> bool:
            assert self.step is not None
            self.step.duration_ms = (time.perf_counter() - self._t0) * 1000
            if exc_type is not None:
                self.step.status = "error"
                self.step.detail = f"{type(exc).__name__}: {exc}"
                self.step.data = {"error": repr(exc)}
                return True  # swallow — caller handles failure
            return False

    def step(self, phase: str, title: str) -> "Trajectory._StepContext":
        return Trajectory._StepContext(self, phase, title)

    def to_list(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._steps]

    def __len__(self) -> int:
        return len(self._steps)
