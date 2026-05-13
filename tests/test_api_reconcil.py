import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.api.routes import get_scenarios_all
from src.engine.demonstracoes.dr import build_dr
from src.engine.inputs import load


def test_api_fse_detail_reconciles_with_dr():
    result = get_scenarios_all(hub_on=False, ecogres_on=False)
    base = result["Base"]

    fse_anual_rows = base["fse_detalhe_anual"]["rows"]
    fse_mensal_rows = base["fse_detalhe_mensal_2025"]["rows"]

    a, b, s = load("Base")
    dr = build_dr(a, b, s)
    fse_dr_2025 = dr[dr.ano == 2025]["fse"].iloc[0]

    fse_2025_from_detail = sum(r["valor"] for r in fse_anual_rows if r["ano"] == 2025)
    fse_2025_from_mensal = sum(r["valor"] for r in fse_mensal_rows)

    assert abs(fse_2025_from_detail + fse_dr_2025) < 0.01
    assert abs(fse_2025_from_mensal - (-fse_dr_2025)) < 0.01

