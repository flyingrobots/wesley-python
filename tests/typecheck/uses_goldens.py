"""Uses of the golden modules that mypy --strict must accept."""

from __future__ import annotations

from emit_plain import Phase, Report, Window
from syntax_messages import Redaction, RunEnd, Step
from syntax_messages import Window as RangeWindow

# An optional key omitted type-checks.
range_window: RangeWindow = {"from": 1}
window: Window = {"from": 1, "to": None}
end: RunEnd = {
    "event": "end",
    "_schema": "run.end/1.0.0",
    "phase": "end",
    "counts": {"files": 3},
    "ok": True,
}

# A keyword key is typed: ``from`` reads as an ``int``, ``in`` as a ``str``.
start: int = window["from"]
redaction: Redaction = {"in": "body", "class": None}
where: str = redaction["in"]

# Optional keys may be present; nested references and lists are checked.
end["window"] = {"from": 1}
end["redactions"] = [redaction]
end["next"] = {"name": "child", "children": []}
step: Step = {"name": "root", "children": [{"name": "leaf", "children": [], "flag": 1}]}

phase: Phase = "START"
report: Report = {
    "id": "r1",
    "phase": phase,
    "window": window,
    "in": ["a"],
    "class": None,
    "flags": [True, None],
    "extra": {"anything": [1, 2]},
    "children": [],
    "related": {"text": "a note"},
}
