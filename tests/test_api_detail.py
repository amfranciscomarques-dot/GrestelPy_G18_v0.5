import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.api.routes import get_scenarios_all


def test_api_detail_has_monthly_fse_rows():
    result = get_scenarios_all(hub_on=False, ecogres_on=False)

    base = result["Base"]
    fse_mensal = base.get("fse_detalhe_mensal_2025", {})
    rows = fse_mensal.get("rows", [])

    assert rows
    assert all({"rubrica", "mes", "valor"} <= set(r.keys()) for r in rows)
    assert sum(r["valor"] for r in rows) > 0
    assert any(r["rubrica"] == "Subcontratos" for r in rows)

