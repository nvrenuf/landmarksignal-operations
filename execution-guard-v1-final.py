"""Compatibility wrapper; implementation lives in execution_guard_v1_final."""
from execution_guard_v1_final import *

if __name__ == "__main__":
    from pathlib import Path
    import runpy
    runpy.run_path(str(Path(__file__).with_name("test_acceptance_corrected.py")), run_name="__main__")
