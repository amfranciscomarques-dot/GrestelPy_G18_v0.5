"""Caminhos dos ficheiros de dados do modelo."""

from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CONTRACT_DIR = DATA_DIR / "contrato"

ASSUMPTIONS_FILE      = (DATA_DIR / "assumptions" / "assumptions.yaml").resolve()
BASE_FINANCEIRA_FILE  = (DATA_DIR / "assumptions" / "base_financeira.yaml").resolve()

PRODUTOS_FILE         = (DATA_DIR / "master"       / "produtos.yaml").resolve()
MERCADORIAS_FILE      = (DATA_DIR / "master"       / "mercadorias.yaml").resolve()
SCHEDULES_FILE        = (DATA_DIR / "master"       / "schedules.yaml").resolve()

BASE2024_FILE         = (DATA_DIR / "historico"    / "2024" / "base.yaml").resolve()
MIX_2024_FILE         = (DATA_DIR / "historico"    / "2024" / "mix.yaml").resolve()

VENDAS_2025_FILE      = (DATA_DIR / "drivers"      / "2025"     / "vendas_mensal.yaml").resolve()
CUSTOS_2025_FILE      = (DATA_DIR / "drivers"      / "2025"     / "custos_mensal.yaml").resolve()
MIX_2025_FILE         = (DATA_DIR / "drivers"      / "2025"     / "mix_mensal.yaml").resolve()
VENDAS_2026_2029_FILE = (DATA_DIR / "drivers"      / "2026_2029" / "vendas_anual.yaml").resolve()
CUSTOS_2026_2029_FILE = (DATA_DIR / "drivers"      / "2026_2029" / "custos_anual.yaml").resolve()

CUSTOM_SCENARIOS_FILE = (DATA_DIR / "cenarios"     / "custom_scenarios.yaml").resolve()

ECOGRES_ASSUMPTIONS_FILE = (DATA_DIR / "subsidiarias" / "ecogres"       / "ecogres_assumptions.yaml").resolve()
HUB_ASSUMPTIONS_FILE     = (DATA_DIR / "subsidiarias" / "hub_logistico" / "m6_hub_assumptions.yaml").resolve()
