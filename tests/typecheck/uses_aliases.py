"""Aliases from the goldens are type aliases: mypy --strict must accept them as types."""

from __future__ import annotations

from emit_unions import Either, Holder, Item, Result
from syntax_messages import MaybeStep

result: Result = {"name": "only"}
item: Item = result
either: Either = {"count": 2}
holder: Holder = {"result": result, "either": [either, {"name": "x"}]}
later: MaybeStep = None
