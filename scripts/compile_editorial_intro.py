"""Compatibility entry point; production compiler lives inside the engine."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"engine/src/hermes_video"))
from editorial_compiler import *

if __name__ == "__main__":
    main()
