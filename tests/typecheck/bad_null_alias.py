"""An alias of ``None`` is the type ``None``: any other value must fail mypy."""

from __future__ import annotations

from syntax_minimal import Null

null: Null = 1
