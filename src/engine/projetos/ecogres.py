"""Ecogres — Pasta e Grés Sustentável, Lda.

Subsidiária 100% Grestel — modelada como subcontratador operacional do grupo.

Funções:
  - load(): Carrega os pressupostos da Ecogres de ecogres_assumptions.yaml.
  - ecogres_dr(): Constrói a Demonstração de Resultados (P&L) da Ecogres.
  - grestel_impact(): Calcula o impacto da Ecogres na DR da Grestel.
  - reducao_mpsc(): Calcula a redução de MPSC da Grestel por aumento de capacidade Ecogres.
"""

from __future__ import annotations

import pandas as pd
import yaml
from pathlib import Path

from ..inputs import ALL_YEARS, DATA_DIR
from ..inputs.paths import ECOGRES_ASSUMPTIONS_FILE


def load() -> dict:
    """Carrega os pressupostos da Ecogres de ecogres_assumptions.yaml."""
    with open(ECOGRES_ASSUMPTIONS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ecogres_dr(
    eco_assumptions: dict,
    hub_ativo: bool = False,
    cresc_subc: float | None = None,
    cresc_ced: float | None = None,
    cresc_custos: float | None = None,
    cresc_dep: float | None = None,
    alpha_sem_hub: float | None = None,
    alpha_com_hub: float | None = None,
    transfer_price: float | None = None,
    transfer_inicio: int | None = None,
    irc_taxa: float | None = None,
    df_vn: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Constrói a Demonstração de Resultados (P&L) da Ecogres.

    Args:
        eco_assumptions: Dicionário com os pressupostos da Ecogres.
        hub_ativo: Indica se o Hub Logístico está ativo.
        cresc_subc: Taxa de crescimento anual para subcontratação, em %, override.
        cresc_ced: Taxa de crescimento anual para cedência de pessoal, em %, override.
        df_vn: DataFrame com VN total da Grestel (colunas: ano, vn_total)
               para aplicar elasticidade ao crescimento dos custos operacionais.

    Returns:
        DataFrame com a DR da Ecogres por ano.
    """
    ops = eco_assumptions["operacoes_correntes"]
    trans = eco_assumptions["transacoes_grestel"]
    fin = eco_assumptions["financiamento"]
    viab = eco_assumptions["viabilidade"]
    transfer_hub = eco_assumptions["transferencia_hub"]
    ops = dict(ops)
    transfer_hub = dict(transfer_hub)

    if cresc_custos is not None:
        ops["crescimento_custos_anual"] = float(cresc_custos)
    if cresc_dep is not None:
        ops["crescimento_depreciacao"] = float(cresc_dep)
    if alpha_sem_hub is not None or alpha_com_hub is not None:
        elasticidade = dict(ops.get("elasticidade_pessoal", {}))
        if alpha_sem_hub is not None:
            elasticidade["alpha_sem_hub"] = float(alpha_sem_hub)
        if alpha_com_hub is not None:
            elasticidade["alpha_com_hub"] = float(alpha_com_hub)
        ops["elasticidade_pessoal"] = elasticidade
    if transfer_price is not None:
        transfer_hub["preco_transferencia_base"] = float(transfer_price)
    if transfer_inicio is not None:
        transfer_hub["inicio"] = int(transfer_inicio)
    if irc_taxa is not None:
        viab = dict(viab)
        viab["irc_taxa_ecogres"] = float(irc_taxa)

    cresc_subc_rate = (
        float(cresc_subc) / 100
        if cresc_subc is not None
        else float(trans["crescimento_subcontratacao"])
    )

    cresc_ced_rate = (
        float(cresc_ced) / 100
        if cresc_ced is not None
        else float(trans["crescimento_cedencia"])
    )

    irc_taxa_base = float(viab["irc_taxa_ecogres"])
    irc_por_ano: dict[int, float] = {
        int(k): float(v)
        for k, v in viab.get("irc_taxa_por_ano", {}).items()
    }
    # If a global override was passed, it takes precedence over the per-year schedule
    irc_taxa_override = irc_taxa if irc_taxa is not None else None

    elasticidade = ops.get("elasticidade_pessoal", {})
    alpha = (
        float(elasticidade.get("alpha_com_hub", 0.15))
        if hub_ativo
        else float(elasticidade.get("alpha_sem_hub", 0.40))
    )

    vn_map = {}
    if df_vn is not None and not df_vn.empty:
        vn_df = df_vn.copy()
        if "ano" in vn_df.columns:
            vn_map = vn_df.set_index("ano")["vn_total"].to_dict()

    anos = ALL_YEARS

    receita_subcontratacao = []
    receita_hub = []
    receita_total = []
    custo_operacional_base = []
    depreciacao = []
    custo_hub = []
    custo_total_operacional = []
    ebitda = []
    ebit = []
    rend_financeiros = []
    rai = []
    irc = []
    rl = []
    cedencia_pessoal = []

    subc_2024 = float(trans["subcontratacao_2024"])
    ced_2024 = float(trans["cedencia_pessoal_2024"])
    custo_op_2024 = float(ops["custos_operacionais_2024"]["total"])
    dep_2024 = float(ops["depreciacao_2024"])
    rl_2024_hist = float(ops["rl_base_2024"])

    custo_op_prev = custo_op_2024

    for y in anos:
        n = y - 2024

        current_receita_subc = subc_2024 * (1 + cresc_subc_rate) ** n
        receita_subcontratacao.append(current_receita_subc)

        current_receita_hub = 0.0

        if hub_ativo and y >= transfer_hub["inicio"]:
            hub_growth_offset = y - int(transfer_hub["inicio"])
            current_receita_hub = float(transfer_hub["preco_transferencia_base"]) * (
                1 + float(transfer_hub["crescimento_anual"])
            ) ** hub_growth_offset

        receita_hub.append(current_receita_hub)

        current_receita_total = current_receita_subc + current_receita_hub
        receita_total.append(current_receita_total)

        if y == 2024:
            current_custo_op_base = custo_op_2024
            custo_op_prev = custo_op_2024
        else:
            cresc_fixo = float(ops["crescimento_custos_anual"])

            if vn_map and y - 1 in vn_map and y in vn_map:
                vn_y = float(vn_map[y])
                vn_prev = float(vn_map[y - 1])
                delta_vn_pct = (vn_y - vn_prev) / vn_prev if vn_prev else 0.0
            else:
                delta_vn_pct = 0.0

            current_custo_op_base = custo_op_prev * (
                1 + cresc_fixo + alpha * delta_vn_pct
            )
            custo_op_prev = current_custo_op_base

        custo_operacional_base.append(current_custo_op_base)

        current_depreciacao = dep_2024 * (
            1 + float(ops["crescimento_depreciacao"])
        ) ** n

        depreciacao.append(current_depreciacao)

        current_custo_hub = 0.0

        if hub_ativo and y >= transfer_hub["inicio"]:
            hub_growth_offset = y - int(transfer_hub["inicio"])
            current_custo_hub = float(transfer_hub["custo_operacional_ecogres"]) * (
                1 + float(transfer_hub["crescimento_anual"])
            ) ** hub_growth_offset

        custo_hub.append(current_custo_hub)

        current_custo_total_operacional = current_custo_op_base + current_custo_hub
        custo_total_operacional.append(current_custo_total_operacional)

        current_ebitda = current_receita_total - current_custo_total_operacional
        ebitda.append(current_ebitda)

        current_ebit = current_ebitda - current_depreciacao
        ebit.append(current_ebit)

        current_rend_financeiros = float(fin["rend_financeiros"])
        rend_financeiros.append(current_rend_financeiros)

        current_rai = current_ebit + current_rend_financeiros
        rai.append(current_rai)

        if y == 2024:
            current_rl = rl_2024_hist
            current_irc = current_rai - current_rl
        else:
            if irc_taxa_override is not None:
                taxa_ano = irc_taxa_override
            else:
                taxa_ano = irc_por_ano.get(y, irc_taxa_base)
            current_irc = current_rai * taxa_ano if current_rai > 0 else 0.0
            current_rl = current_rai - current_irc

        irc.append(current_irc)
        rl.append(current_rl)

        current_cedencia_pessoal = ced_2024 * (1 + cresc_ced_rate) ** n
        cedencia_pessoal.append(current_cedencia_pessoal)

    return pd.DataFrame(
        {
            "ano": anos,
            "receita_subcontratacao": receita_subcontratacao,
            "receita_hub": receita_hub,
            "receita_total": receita_total,
            "custo_operacional_base": custo_operacional_base,
            "custo_hub": custo_hub,
            "custo_total_operacional": custo_total_operacional,
            "ebitda": ebitda,
            "depreciacao": depreciacao,
            "ebit": ebit,
            "rend_financeiros": rend_financeiros,
            "rai": rai,
            "irc": irc,
            "rl": rl,
            "cedencia_pessoal": cedencia_pessoal,
        }
    )


def grestel_impact(
    eco_assumptions: dict,
    hub_ativo: bool = False,
    irc_taxa: float | None = None,
    cresc_subc: float | None = None,
    cresc_ced: float | None = None,
    df_vn: pd.DataFrame | None = None,
) -> dict[int, dict]:
    """Calcula o impacto da Ecogres na DR da Grestel.

    Retorna:
        Dicionário com RL da Ecogres e dividendos por ano.
    """
    _ = irc_taxa

    df = ecogres_dr(
        eco_assumptions,
        hub_ativo=hub_ativo,
        cresc_subc=cresc_subc,
        cresc_ced=cresc_ced,
        df_vn=df_vn,
    )

    df_map = df.set_index("ano")

    impact: dict[int, dict] = {}

    for y in df_map.index:
        impact[int(y)] = {
            "rl_ecogres": float(df_map.loc[y, "rl"]),
            "dividendos": 0.0,
        }

    return impact


def subcontratacao_anual(eco_assumptions: dict) -> pd.DataFrame:
    """Extrai os valores anuais de receita de subcontratação da Ecogres.

    Returns:
        DataFrame com colunas:
        ano, subcontratacao_ecogres.
    """
    df = ecogres_dr(eco_assumptions, hub_ativo=False)

    return df[["ano", "receita_subcontratacao"]].rename(
        columns={
            "receita_subcontratacao": "subcontratacao_ecogres",
        }
    )


def cedencia_pessoal_anual(eco_assumptions: dict) -> pd.DataFrame:
    """Extrai os valores anuais de cedência de pessoal da Ecogres.

    Returns:
        DataFrame com colunas:
        ano, cedencia_pessoal.
    """
    df = ecogres_dr(eco_assumptions, hub_ativo=False)

    return df[["ano", "cedencia_pessoal"]]


def reducao_mpsc(eco_assumptions: dict) -> dict[int, float]:
    """Calcula a redução de MPSC da Grestel por aumento de capacidade da Ecogres.

    Quando a Ecogres aumenta a sua capacidade de subcontratação (via crescimento
    orgânico), parte da produção que a Grestel faria internamente é transferida
    para a Ecogres, reduzindo o consumo de matérias-primas (MPSC) da Grestel.

    A lógica usa:
      - subcontratacao_capacidade_referencia: valor base da subcontratação (ex: 2.240.000€)
      - reducao_mpsc_por_capacidade: percentagem de redução de MPSC por cada
        unidade de subcontratação acima da referência

    Returns:
        Dicionário {ano: redução_mpsc_em_euros}.
    """
    capacidade = eco_assumptions.get("capacidade", {})
    if not capacidade.get("ativar_reducao_mpsc", False):
        return {y: 0.0 for y in ALL_YEARS}

    ref = float(capacidade.get("subcontratacao_capacidade_referencia", 2240000))
    reducao_pct = float(capacidade.get("reducao_mpsc_por_capacidade", 0.15))

    df = ecogres_dr(eco_assumptions, hub_ativo=False)
    df_map = df.set_index("ano")

    result: dict[int, float] = {}
    for y in ALL_YEARS:
        subc = float(df_map.loc[y, "receita_subcontratacao"])
        excesso = max(subc - ref, 0.0)
        result[y] = excesso * reducao_pct

    return result
