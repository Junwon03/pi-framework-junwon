"""Compatibility entry point for the active deterministic verifier."""

from __future__ import annotations

import sys

from scripts.verify_outputs import main


if __name__ == "__main__":
    sys.exit(main())
