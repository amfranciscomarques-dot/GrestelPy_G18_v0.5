import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.api.routes import get_scenarios_all


def test_api_scenarios_structure():
    result = get_scenarios_all(hub_on=False, ecogres_on=False)

    assert set(result.keys()) == {"Base", "Upside", "Downside", "Stress"}

    for data in result.values():
        for key in (
            "dr",
            "balanco",
            "dfc",
            "fse_detalhe_anual",
            "fse_detalhe_mensal_2025",
        ):
            assert "rows" in data[key]
        assert isinstance(data["kpis"], dict)

