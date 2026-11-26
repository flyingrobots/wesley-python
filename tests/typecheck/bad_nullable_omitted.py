"""A nullable GraphQL field is still a required key: omitting it must fail mypy."""

from __future__ import annotations

from emit_plain import Window

window: Window = {"from": 1}
