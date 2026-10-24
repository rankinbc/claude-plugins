"""``python -m courier ...`` runs the CLI."""

from __future__ import annotations

import sys

from courier.cli import main

if __name__ == "__main__":
    sys.exit(main())
