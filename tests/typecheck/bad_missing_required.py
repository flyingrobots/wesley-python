"""Omitting a required key must fail mypy."""

from __future__ import annotations

from syntax_messages import Window

window: Window = {"to": 2}
