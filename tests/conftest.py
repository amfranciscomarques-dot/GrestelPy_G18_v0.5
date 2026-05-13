import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

import pytest

from src.engine.inputs import load


@pytest.fixture(scope="session")
def base_load():
    """Carrega cenário Base (a, base, sched)."""
    return load("Base")

