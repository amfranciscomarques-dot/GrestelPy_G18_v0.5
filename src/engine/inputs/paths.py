"""Caminhos dos ficheiros de dados do modelo."""

from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# --- Dados históricos (imutáveis após fecho do exercício) ---
BASE2024_FILE         = (DATA_DIR / "historico"      / "2024"      / "base.yaml").resolve()
MIX_2024_FILE         = (DATA_DIR / "historico"      / "2024"      / "mix.yaml").resolve()
PRODUTOS_2024_FILE    = (DATA_DIR / "historico"      / "2024"      / "produtos.yaml").resolve()
MERCADORIAS_2024_FILE = (DATA_DIR / "historico"      / "2024"      / "mercadorias.yaml").resolve()

# --- Pressupostos (inputs editáveis do modelo) ---
ASSUMPTIONS_FILE      = (DATA_DIR / "pressupostos"   / "globais.yaml").resolve()
INVESTIMENTO_FILE     = (DATA_DIR / "pressupostos"   / "investimento.yaml").resolve()

MACRO_2025_FILE       = (DATA_DIR / "pressupostos"   / "2025"      / "macro.yaml").resolve()
VENDAS_2025_FILE      = (DATA_DIR / "pressupostos"   / "2025"      / "vendas.yaml").resolve()
CUSTOS_2025_FILE      = (DATA_DIR / "pressupostos"   / "2025"      / "custos.yaml").resolve()
MIX_2025_FILE         = (DATA_DIR / "pressupostos"   / "2025"      / "mix.yaml").resolve()

MACRO_2026_2029_FILE  = (DATA_DIR / "pressupostos"   / "2026_2029" / "macro.yaml").resolve()
VENDAS_2026_2029_FILE = (DATA_DIR / "pressupostos"   / "2026_2029" / "vendas.yaml").resolve()
CUSTOS_2026_2029_FILE = (DATA_DIR / "pressupostos"   / "2026_2029" / "custos.yaml").resolve()

# --- Catálogos estruturais estáveis ---
PRODUTOS_FILE         = (DATA_DIR / "master"         / "produtos.yaml").resolve()
MERCADORIAS_FILE      = (DATA_DIR / "master"         / "mercadorias.yaml").resolve()
FSE_RUBRICAS_FILE     = (DATA_DIR / "master"         / "fse_rubricas.yaml").resolve()

# --- Outputs calculados pelo motor (não editar manualmente) ---
SCHEDULES_FILE        = (DATA_DIR / "computed"       / "schedules.yaml").resolve()

# --- Cenários e subsidiárias ---
CUSTOM_SCENARIOS_FILE    = (DATA_DIR / "cenarios"      / "custom_scenarios.yaml").resolve()
ECOGRES_ASSUMPTIONS_FILE = (DATA_DIR / "subsidiarias"  / "ecogres"       / "ecogres_assumptions.yaml").resolve()
HUB_ASSUMPTIONS_FILE     = (DATA_DIR / "subsidiarias"  / "hub_logistico" / "m6_hub_assumptions.yaml").resolve()
