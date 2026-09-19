"""Windows sign-in entrypoint: restore the project's working directory first."""
import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
runpy.run_path(str(ROOT / "main.py"), run_name="__main__")
