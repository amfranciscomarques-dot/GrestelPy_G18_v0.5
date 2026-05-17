"""Módulo: engine/investimento.py — Investimento, Depreciação e Amortização."""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS, YEARS


def _get_dfc_2024_value(
    base: Base2024,
    key: str,
    default: float = 0.0,
) -> float:
    """Lê uma rubrica da DFC real de 2024 a partir de base.raw."""
    try:
        return float(base.raw["dfc_2024_real"][key])
    except (AttributeError, KeyError, TypeError, ValueError):
        return float(default)


def _load_ecogres_impact(a: Assumptions, df_vn: pd.DataFrame | None = None) -> dict[int, dict] | None:
    """Carrega grestel_impact() da Ecogres apenas se ativa."""
    try:
        from ..projetos import ecogres as eco_mod

        eco = eco_mod.load()
        if not eco or not eco.get("incluir_ecogres", False):
            return None

        irc_taxa = (
            float(a.impostos.get("IRC_taxa_geral", 0.20))
            + float(a.impostos.get("Derrama_Municipal", 0.015))
        )

        hub_ativo = a.raw.get("hub_logistico", {}).get("incluir_hub", False)

        return eco_mod.grestel_impact(
            eco,
            hub_ativo=hub_ativo,
            irc_taxa=irc_taxa,
            df_vn=df_vn,
        )
    except Exception:
        return None


def _load_hub_capex(a: Assumptions) -> dict | None:
    """Carrega impacto CAPEX/depreciação do Hub, ou None se Hub desativado."""
    try:
        raw_hub = a.raw.get("hub_logistico", {})

        if not raw_hub.get("incluir_hub", False):
            return None

        from ..projetos import hub_logistico as hub_mod

        df = hub_mod.hub_capex(raw_hub)

        return df.set_index("ano").to_dict(orient="index")
    except Exception:
        return None


def investimento_anual(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_vn: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tabela anual de investimento, depreciações, intangíveis e subsidiárias."""
    inv = sched.investimento

    taxa_aft = float(inv["taxa_dep_aft"])
    taxa_int = float(inv["taxa_amort_intang"])

    aft_24 = float(base.balanco["ativo_nao_corrente"]["AFT_liquido"])
    intang_24 = float(base.balanco["ativo_nao_corrente"]["Intangiveis"])

    novo_aft = inv["novo_investimento_aft"]
    novo_int = inv["novo_investimento_intang"]

    aft_fim = {
        2024: aft_24,
    }

    intang_fim = {
        2024: intang_24,
    }

    dep_aft = {
        2024: aft_24 * taxa_aft,
    }

    dep_int = {
        2024: intang_24 * taxa_int,
    }

    hub_capex_map = _load_hub_capex(a)

    aft = aft_24      # AFT geral da Grestel (sem hub)
    hub_aft = 0.0     # AFT do hub rastreado separadamente para evitar dupla depreciação
    intang = intang_24

    for y in YEARS:
        if y > 2025:
            d_aft = aft * taxa_aft   # taxa geral só sobre AFT Grestel, não hub
            d_int = intang * taxa_int
        else:
            d_aft = float(inv["depreciacao_aft_anual"][y])
            d_int = float(inv["amortizacao_intang_anual"][y])

        dep_hub_y = 0.0
        capex_hub_y = 0.0

        jc_hub_y = 0.0
        if hub_capex_map and y in hub_capex_map:
            dep_hub_y = float(hub_capex_map[y].get("depreciacao", 0.0))
            capex_hub_y = float(hub_capex_map[y].get("capex", 0.0))
            jc_hub_y = float(hub_capex_map[y].get("juros_capitalizados_aft", 0.0))

        aft = aft - d_aft + float(novo_aft.get(y, 0.0))
        hub_aft = hub_aft + capex_hub_y + jc_hub_y - dep_hub_y

        intang = (
            intang
            - d_int
            + float(novo_int.get(y, 0.0))
        )

        aft_fim[y] = max(aft + hub_aft, 0.0)   # total para balanço
        intang_fim[y] = max(intang, 0.0)

        dep_aft[y] = d_aft + dep_hub_y          # total depreciação = geral + hub pools
        dep_int[y] = d_int

    rend_eq = inv["rend_equiv_patrimonial"]
    div = inv["dividendos_recebidos"]

    eco_impact = _load_ecogres_impact(a, df_vn=df_vn)

    cn = {
        2024: float(base.balanco["ativo_nao_corrente"]["Subsidiarias"]),
    }

    for y in YEARS:
        rend_y = float(rend_eq.get(y, 0.0))
        div_y = float(div.get(y, 0.0))

        if eco_impact and y in eco_impact:
            rend_y += float(eco_impact[y].get("rl_ecogres", 0.0))
            div_y += float(eco_impact[y].get("dividendos", 0.0))

        cn_equity = 0.0
        cn[y] = cn[y - 1] + rend_y - div_y - cn_equity

    goodwill = float(base.balanco["ativo_nao_corrente"]["Goodwill"])
    outros_af = float(base.balanco["ativo_nao_corrente"]["Ativos_Fin_Justo_Valor"])
    outros_fixos = float(base.balanco["ativo_nao_corrente"]["Outros_Ativos_Fixos"])

    capex_aft_2024 = abs(_get_dfc_2024_value(base, "capex_aft", 0.0))
    capex_intang_2024 = abs(_get_dfc_2024_value(base, "capex_intang", 0.0))
    dividendos_2024 = _get_dfc_2024_value(base, "dividendos_recebidos", 0.0)

    rows = []

    for y in ALL_YEARS:
        if y >= 2025:
            rend_y = float(rend_eq.get(y, 0.0))
            div_y = float(div.get(y, 0.0))
            novo_aft_y = float(novo_aft.get(y, 0.0))
            novo_int_y = float(novo_int.get(y, 0.0))
        else:
            rend_y = float(base.outros_rendimentos["Equivalencia_patrimonial"])
            div_y = dividendos_2024
            novo_aft_y = capex_aft_2024
            novo_int_y = capex_intang_2024

        if eco_impact and y in eco_impact:
            rend_y += float(eco_impact[y].get("rl_ecogres", 0.0))
            div_y += float(eco_impact[y].get("dividendos", 0.0))

        total_outros = (
            goodwill
            + intang_fim[y]
            + cn[y]
            + outros_af
            + outros_fixos
        )

        rows.append(
            {
                "ano": y,
                "aft_liquido_fim": aft_fim[y],
                "depreciacao_aft": dep_aft[y],
                "novo_investimento_aft": novo_aft_y,
                "intang_liquido_fim": intang_fim[y],
                "amortizacao_intang": dep_int[y],
                "novo_investimento_intang": novo_int_y,
                "subsidiarias_fim": cn[y],
                "rend_equiv_patrimonial": rend_y,
                "dividendos_recebidos": div_y,
                "goodwill_intang_subs_af_total": total_outros,
                "total_dep_amort": dep_aft[y] + dep_int[y],
                "hub_incluido": hub_capex_map is not None,
                "ecogres_incluido": eco_impact is not None,
                # Colunas separadas para o balanço desagregado
                "goodwill": goodwill,
                "intangiveis_fim": intang_fim[y],
                "ativos_fin_jv": outros_af,
                "outros_fixos_af": outros_fixos,
            }
        )

    return pd.DataFrame(rows)
