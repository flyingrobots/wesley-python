"""Uses of the syntax API's live output for ``tests.support.minimal_module()``, written as ``minimal.py``.

Every alias must be a type alias: mypy --strict must accept each one as a type.
"""

from __future__ import annotations

from typing import List

from minimal import AlsoNull, Null, Single

single: Single = "s"
null: Null = None
also: AlsoNull = None
nulls: List[Null] = [None, null, also]
