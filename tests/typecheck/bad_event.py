"""A wrong ``event`` literal must fail mypy."""

from __future__ import annotations

from syntax_messages import RunEnd

end: RunEnd = {
    "event": "start",
    "_schema": "run.end/1.0.0",
    "phase": "end",
    "counts": {},
    "ok": True,
}
