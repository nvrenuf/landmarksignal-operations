"""Compatibility entry point for the authoritative isolated test suite."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("test_acceptance_corrected.py")), run_name="__main__")

