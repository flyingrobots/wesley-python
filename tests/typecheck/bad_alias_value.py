"""An alias of one union member is that member's type: a wrong key must fail mypy."""

from __future__ import annotations

from emit_unions import Result

result: Result = {"name": 1}
