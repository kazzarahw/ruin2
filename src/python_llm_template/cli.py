"""Command-line interface (the ``cli`` layer).

Parses arguments, calls services, and prints results. This is the *only*
module in the package allowed to call ``print()``.
"""

import argparse
import sys
from collections.abc import Sequence

from python_llm_template.services.greeting import GreetingService


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="python-llm-template",
        description="Print a greeting for NAME.",
    )
    parser.add_argument("name", help="the name to greet")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        message = GreetingService().greet(args.name)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(message)
    return 0
