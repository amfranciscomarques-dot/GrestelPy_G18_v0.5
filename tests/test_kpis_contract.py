from __future__ import annotations

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

import math
import pytest

from src.engine.inputs import load, ALL_YEARS
from src.engine.demonstracoes.statements import build_statements
from src.engine.modelo.kpis import build_kpis


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="module")
def base_data():
    """Carrega cenário Base e gera DR, Balanço, DFC, KPIs."""
    a, base, sched = load("Base")
    dfs = build_statements(a, base, sched)
    kpis = build_kpis(dfs["dr"], dfs["balanco"], dfs["dfc"])
    return {
        "dr": dfs["dr"],
        "balanco": dfs["balanco"],
        "dfc": dfs["dfc"],
        "kpis": kpis,
    }


@pytest.fixture(scope="module")
def kpis_df(base_data):
    return base_data["kpis"]


# ============================================================
# 1. PRESENÇA DE CAMPOS ESPERADOS PELO FRONTEND
# ============================================================

# Nomes "oficiais" (definidos em API_CONTRACT.md). Estes têm de
# existir SEM EXCEÇÃO. Se algum desaparecer, frontend parte.
KPIS_OFICIAIS = {
    # Margens
    "ebitda_margin",
    "ebit_margin",
    "rl_margin",
    # Rentabilidade
    "roe",
    "roa",
    "roce",
    # Endividamento
    "divida_liquida",
    "nd_ebitda",
    "autonomia_financeira",
    # Liquidez
    "current_ratio",
    # Ciclo
    "ciclo_caixa",
    # Absolutos usados em cards/headers
    "vn",
    "ebitda",
    "ebit",
    "rl",
    "caixa",
    "emprestimos_nc",
    "emprestimos_c",
    "cp",
    "total_ativo",
    # Prazos (dias)
    "PMR",
    "PMP",
    "DMI",
    # Identificador
    "ano",
}


def test_kpis_tem_todos_os_campos_oficiais(kpis_df):
    """Todos os KPIs documentados em API_CONTRACT.md existem."""
    missing = KPIS_OFICIAIS - set(kpis_df.columns)
    assert not missing, f"KPIs em falta: {sorted(missing)}"


def test_kpis_tem_uma_linha_por_ano(kpis_df):
    """Uma linha por ano em ALL_YEARS (2024..2029)."""
    anos_kpis = set(kpis_df["ano"].astype(int).tolist())
    anos_esperados = set(ALL_YEARS)
    assert anos_kpis == anos_esperados, (
        f"Anos no KPIs DataFrame: {sorted(anos_kpis)}; "
        f"esperados: {sorted(anos_esperados)}"
    )


# ============================================================
# 2. BUG-FIX: divida_liquida nunca pode ser sempre zero
# ============================================================

def test_divida_liquida_nao_e_zeros(kpis_df):
    """O bug histórico era divida_liquida = [0, 0, 0, ...].

    Após a fase 1.5 deve ter valores reais. Aceita que algum ano
    pontual seja zero (caso degenerado), mas nem todos.
    """
    valores = kpis_df["divida_liquida"].tolist()
    n_zeros = sum(1 for v in valores if v == 0 or v is None)
    assert n_zeros < len(valores), (
        f"divida_liquida está toda a zero ({valores}); "
        f"o bug histórico não foi corrigido"
    )


def test_divida_liquida_bate_com_componentes(base_data, kpis_df):
    """divida_liquida = emprestimos_nc + emprestimos_c - caixa.

    Verifica a fórmula contra o Balanço para cada ano.
    Tolerância pequena para erros de arredondamento de float.
    """
    bal = base_data["balanco"]
    tolerancia = 1.0  # 1€ — generoso para arredondamentos

    for _, row in kpis_df.iterrows():
        ano = int(row["ano"])
        bal_row = bal[bal["ano"] == ano].iloc[0]

        esperado = (
            float(bal_row["emprestimos_nc"])
            + float(bal_row["emprestimos_c"])
            - float(bal_row["caixa"])
        )
        actual = float(row["divida_liquida"])

        assert abs(actual - esperado) < tolerancia, (
            f"Ano {ano}: divida_liquida={actual} "
            f"mas NC+C-caixa={esperado} (diff={actual-esperado})"
        )


# ============================================================
# 3. INVARIANTES NUMÉRICAS
# ============================================================

def test_kpis_sem_nan(kpis_df):
    """Nenhuma célula numérica pode ser NaN.

    NaN propaga-se silenciosamente e parte a UI. Se um KPI não
    é calculável, deve ser None/null explícito ou um valor de
    fallback documentado, não NaN.
    """
    for col in kpis_df.columns:
        if kpis_df[col].dtype.kind in "fi":  # float ou int
            n_nan = kpis_df[col].isna().sum()
            assert n_nan == 0, (
                f"Coluna '{col}' tem {n_nan} valores NaN. "
                f"Linhas: {kpis_df[kpis_df[col].isna()]['ano'].tolist()}"
            )


def test_margens_em_intervalo_razoavel(kpis_df):
    """Margens devem estar em [-1, 1] (em fração, não %).

    Margens fora deste intervalo indicam quase de certeza um
    bug de unidades (a confundir % com fração).
    """
    for col in ("ebitda_margin", "ebit_margin", "rl_margin"):
        for _, row in kpis_df.iterrows():
            v = row[col]
            if v is None or math.isnan(float(v)):
                continue
            assert -1.0 <= float(v) <= 1.0, (
                f"{col} no ano {row['ano']} = {v} fora de [-1, 1]. "
                f"Provável bug de unidades."
            )


def test_autonomia_financeira_em_intervalo(kpis_df):
    """Autonomia financeira = CP / Total Ativo, em [0, 1].

    Negativa indica capital próprio negativo (crise grave).
    >1 indica erro de cálculo.
    """
    for _, row in kpis_df.iterrows():
        v = row["autonomia_financeira"]
        if v is None:
            continue
        # Permitir ligeiramente abaixo de 0 (CP pode ser negativo
        # em stress), mas não acima de 1.
        assert float(v) <= 1.0, (
            f"autonomia_financeira no ano {row['ano']} = {v} > 1. "
            f"Impossível matematicamente."
        )


def test_ciclo_caixa_em_dias_razoaveis(kpis_df):
    """Ciclo de caixa em dias, esperado tipicamente em [-365, 500]."""
    for _, row in kpis_df.iterrows():
        v = row["ciclo_caixa"]
        if v is None:
            continue
        assert -365 <= float(v) <= 500, (
            f"ciclo_caixa no ano {row['ano']} = {v} dias, fora de "
            f"[-365, 500]. Verificar unidades (dias, não anos)."
        )


# ============================================================
# 4. RELAÇÕES ENTRE KPIs (cross-checks)
# ============================================================

def test_ebitda_margin_bate_com_ebitda_sobre_vn(kpis_df):
    """ebitda_margin = ebitda / vn."""
    tolerancia = 1e-4

    for _, row in kpis_df.iterrows():
        vn = float(row["vn"])
        if vn == 0:
            continue

        esperado = float(row["ebitda"]) / vn
        actual = float(row["ebitda_margin"])

        assert abs(actual - esperado) < tolerancia, (
            f"Ano {row['ano']}: ebitda_margin={actual} "
            f"mas ebitda/vn={esperado}"
        )


def test_nd_ebitda_bate_com_divida_sobre_ebitda(kpis_df):
    """nd_ebitda = divida_liquida / ebitda (quando ebitda > 0)."""
    tolerancia = 1e-3

    for _, row in kpis_df.iterrows():
        ebitda = float(row["ebitda"])
        if ebitda <= 0:
            continue  # rácio degenerado, salta

        esperado = float(row["divida_liquida"]) / ebitda
        actual = float(row["nd_ebitda"])

        assert abs(actual - esperado) < tolerancia, (
            f"Ano {row['ano']}: nd_ebitda={actual} "
            f"mas divida_liquida/ebitda={esperado}"
        )


# ============================================================
# 5. ALIASES DEPRECATED (existem mas espelham os oficiais)
# ============================================================

ALIASES_DEPRECATED = {
    "ebitda_margin": "margem_ebitda",
    "ebit_margin": "margem_ebit",
    "rl_margin": "margem_rl",
    "roe": "ROE",
    "roa": "ROA",
    "nd_ebitda": "debt_ebitda",
    "current_ratio": "liquidez_geral",
}


@pytest.mark.parametrize("oficial,alias", list(ALIASES_DEPRECATED.items()))
def test_aliases_deprecated_espelham_oficiais(kpis_df, oficial, alias):
    """Aliases legacy devem ter exatamente o mesmo valor que o
    nome oficial. Quando o frontend migrar, removem-se."""
    if alias not in kpis_df.columns:
        pytest.skip(f"Alias '{alias}' já removido — OK")

    for _, row in kpis_df.iterrows():
        v_oficial = row[oficial]
        v_alias = row[alias]

        if v_oficial is None and v_alias is None:
            continue

        assert float(v_oficial) == float(v_alias), (
            f"Ano {row['ano']}: '{oficial}'={v_oficial} mas "
            f"alias '{alias}'={v_alias} — divergem"
        )


# ============================================================
# 6. SCENARIOS API (fim-a-fim)
# ============================================================

def test_api_scenarios_all_devolve_kpis_oficiais():
    """Confirma que get_scenarios_all expõe os KPIs oficiais
    no formato esperado pelo frontend ({"rows": [...]})."""
    from src.api.routes.scenarios import get_scenarios_all

    resp = get_scenarios_all(hub_on=False, ecogres_on=False)

    assert "Base" in resp, "Cenário Base em falta na resposta"
    base = resp["Base"]
    assert "kpis" in base, "KPIs em falta no cenário Base"

    kpis = base["kpis"]
    # Pode vir como {"rows": [...]} ou dict de listas
    if isinstance(kpis, dict) and "rows" in kpis:
        rows = kpis["rows"]
        assert len(rows) > 0, "kpis.rows está vazio"
        primeira = rows[0]
        missing = KPIS_OFICIAIS - set(primeira.keys())
        assert not missing, (
            f"API /scenarios/all não devolve KPIs: {sorted(missing)}"
        )
    elif isinstance(kpis, dict):
        # Formato dict-de-listas (compatibilidade)
        missing = KPIS_OFICIAIS - set(kpis.keys())
        assert not missing, (
            f"API /scenarios/all não devolve KPIs: {sorted(missing)}"
        )
    else:
        pytest.fail(f"Formato inesperado de kpis: {type(kpis)}")


def test_api_scenarios_all_divida_liquida_nao_zero():
    """Bug-fix end-to-end: pela API, divida_liquida deve aparecer."""
    from src.api.routes.scenarios import get_scenarios_all

    resp = get_scenarios_all(hub_on=False, ecogres_on=False)
    kpis = resp["Base"]["kpis"]

    if isinstance(kpis, dict) and "rows" in kpis:
        valores = [r.get("divida_liquida") for r in kpis["rows"]]
    elif isinstance(kpis, dict):
        valores = kpis.get("divida_liquida", [])
    else:
        pytest.fail("Formato inesperado")

    n_zero_ou_none = sum(
        1 for v in valores if v is None or v == 0
    )
    assert n_zero_ou_none < len(valores), (
        f"divida_liquida via API ainda é zeros: {valores}"
    )
