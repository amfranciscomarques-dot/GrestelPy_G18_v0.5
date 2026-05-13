import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.engine.operacional.fse import FSE_DETALHE_KEYS, fse_rubricas_ordered
from src.engine.inputs import load


def test_fse_keys_exist_in_base_data():
    _, b, _ = load("Base")
    base_vals = getattr(b, "fse_detalhe", {}) or {}

    assert FSE_DETALHE_KEYS
    assert fse_rubricas_ordered()
    assert all(rub in base_vals for rub in FSE_DETALHE_KEYS.keys())

