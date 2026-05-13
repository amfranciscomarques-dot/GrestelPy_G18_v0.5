import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.engine.modelo.model import dataframe_to_records, run_model


def test_run_model_returns_expected_outputs():
    dfs = run_model("Base", hub_on=False, ecogres_on=False)
    rec = dataframe_to_records(dfs)

    for key in ("dr", "balanco", "dfc", "kpis"):
        assert key in dfs
        assert key in rec

    assert "fse_detalhe_anual" in dfs
    assert "fse_detalhe_mensal_2025" in dfs
    assert len(dfs["fse_detalhe_anual"]) > 0
    assert sum(sum(v.values()) for v in dfs["fse_detalhe_mensal_2025"].values()) > 0

