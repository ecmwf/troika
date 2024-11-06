"""Main entry point for Troika"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main(prog="troika"))
