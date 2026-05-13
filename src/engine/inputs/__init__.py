"""API pública de carregamento de dados do engine."""

from src.engine.inputs.paths import DATA_DIR
from src.engine.inputs.constants import (
    YEARS,
    ALL_YEARS,
    PRODUTOS,
    MERCADORIAS,
    MERCADOS,
    CANAIS,
    MESES,
)
from src.engine.inputs.models import Assumptions, Base2024, Schedules
from src.engine.inputs.loader import load, CENARIOS
from src.engine.inputs.custom_scenarios import (
    load_custom_scenarios,
    save_custom_scenarios,
    custom_scenario_names,
    get_custom_scenario,
    upsert_custom_scenario,
    delete_custom_scenario,
)

__all__ = [
    "DATA_DIR",
    "YEARS",
    "ALL_YEARS",
    "PRODUTOS",
    "MERCADORIAS",
    "MERCADOS",
    "CANAIS",
    "MESES",
    "Assumptions",
    "Base2024",
    "Schedules",
    "load",
    "CENARIOS",
    "load_custom_scenarios",
    "save_custom_scenarios",
    "custom_scenario_names",
    "get_custom_scenario",
    "upsert_custom_scenario",
    "delete_custom_scenario",
]
