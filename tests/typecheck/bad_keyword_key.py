"""A keyword key is typed as ``int``, so reading it as ``str`` must fail mypy."""

from __future__ import annotations

from syntax_messages import Window

window: Window = {"from": 1}
start: str = window["from"]
