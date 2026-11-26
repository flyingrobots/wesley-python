"""A non-null GraphQL field refuses ``None``; a nullable one is required, not optional."""

from __future__ import annotations

from emit_plain import Window

window: Window = {"from": None, "to": None}
