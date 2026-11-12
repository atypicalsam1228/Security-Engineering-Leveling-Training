"""Run the lab tool without installing it: python lab/lab.py <command>."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labcli.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
