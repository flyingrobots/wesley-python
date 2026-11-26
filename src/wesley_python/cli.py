# Copyright 2026 Captain James
# SPDX-License-Identifier: Apache-2.0
"""The command line: ``python -m wesley_python emit [--ir FILE] [--out FILE]``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from wesley_python.emit import module_from_ir
from wesley_python.syntax import render

if TYPE_CHECKING:
    from collections.abc import Sequence

PROG = "wesley-python"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG, description="Generate Python from Wesley IR.")
    commands = parser.add_subparsers(dest="command", required=True)
    emit = commands.add_parser(
        "emit",
        help="emit TypedDicts for plain GraphQL types",
        description="Read Wesley IR JSON and write a Python module of TypedDicts and aliases.",
    )
    emit.add_argument("--ir", metavar="FILE", help="the IR JSON to read (default: standard input)")
    emit.add_argument("--out", metavar="FILE", help="the module to write (default: standard output)")
    return parser


def _emit(ir_path: str | None, out_path: str | None) -> None:
    if ir_path is None:
        text = sys.stdin.read()
    else:
        with open(ir_path, encoding="utf-8") as handle:  # noqa: PTH123 - pathlib is not needed
            text = handle.read()
    output = render(module_from_ir(json.loads(text)))
    if out_path is None:
        sys.stdout.write(output)
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as handle:  # noqa: PTH123
            handle.write(output)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return its exit status: 0 on success, 1 on any error."""
    args = _parser().parse_args(argv)
    try:
        _emit(args.ir, args.out)
    except json.JSONDecodeError as error:
        sys.stderr.write(f"{PROG}: error: the IR is not valid JSON: {error}\n")
        return 1
    except (OSError, ValueError, TypeError) as error:
        sys.stderr.write(f"{PROG}: error: {error}\n")
        return 1
    return 0
