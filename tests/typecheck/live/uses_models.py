"""Uses of the emitter's live output for ``tests/fixtures/unions.ir.json``, written as ``models.py``.

Every alias must be a type alias: mypy --strict must accept each one as a type.
"""

from __future__ import annotations

from models import Either, Holder, Result

result: Result = {"name": "only"}
either: Either = {"count": 2}
holder: Holder = {"result": result, "either": [either]}
