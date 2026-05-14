"""Módulo: engine/produção.py — Orçamento de Produção."""
#to do: cip unitário deve ser calculado a partir de ficha de produto, custo de matéria prima, mão de obra direta, custos indiretos, etc. O valor atual é um placeholder lido do catálogo master/produtos.yaml.
from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, YEARS, ALL_YEARS, PRODUTOS, MESES


def _cip_unitarios(a: Assumptions) -> dict[str, float]:
    """CIP unitário por produto lido do catálogo master/produtos.yaml."""
    families = a.product_families
    return {
        p: float((families.get(p) or {}).get("cip_unitario", 0.0))
        for p in PRODUTOS
    }


def _qty_totais_2024(a: Assumptions, base: Base2024) -> dict[str, float]:
    """Quantidade total 2024 por produto."""
    from .vendas import _qty_2024_mixed

    return _qty_2024_mixed(a, base).groupby("produto")["qtd_2024"].sum().to_dict()


def _fator_calibracao_2024(a: Assumptions, base: Base2024) -> float:
    """Fator que escala os cip_unitario ao CMVMC_prod_2024 auditado.

    Garante que Σ(qty × cip_unitario × fator) == CMVMC_prod_2024,
    preservando a coerência com as demonstrações financeiras históricas.
    """
    cmvmc_prod = (
        float(base.raw["dr_2024_real"]["cmvmc"])
        - float(base.totais["CMVMC_Mercadorias_2024"])
    )

    qtd = _qty_totais_2024(a, base)
    cip = _cip_unitarios(a)

    denom = sum(qtd.get(p, 0.0) * cip[p] for p in PRODUTOS)

    return cmvmc_prod / denom if denom > 0 else 1.0


def cup_base_2024(a: Assumptions, base: Base2024) -> float:
    """Fator de calibração 2024 (mantido para compatibilidade com cmvmc.py)."""
    return _fator_calibracao_2024(a, base)


def cups_por_produto_2024(a: Assumptions, base: Base2024) -> dict[str, float]:
    """CUP calibrado por produto para 2024.

    cup[p] = cip_unitario[p] × fator_calibração
    onde fator garante que Σ(qty × cup) == CMVMC_prod_2024.
    """
    fator = _fator_calibracao_2024(a, base)
    cip = _cip_unitarios(a)
    return {p: cip[p] * fator for p in PRODUTOS}


def _cost_growth_factors(a: Assumptions) -> dict[int, float]:
    """Fator de crescimento acumulado do custo de produção por ano."""
    from .vendas import _monthly_cum_index, _monthly_rates, _saz_to_dict

    block = a.cenario_block()

    cost_block = (
        block.get("custo_mercadorias")
        or a.raw.get("crescimento_custo_mercadorias", {})
    )

    cum = _monthly_cum_index(_monthly_rates(cost_block))
    saz = _saz_to_dict(a.sazonalidade.get("PT", []))

    f_2025 = sum(
        saz[m] * cum[m]
        for m in MESES
    )

    g_yr = a.cresc_2026_2029("custo_mercadorias")

    factors: dict[int, float] = {
        2024: 1.0,
        2025: f_2025,
    }

    f = f_2025

    for y in YEARS[1:]:
        f *= 1 + g_yr[y]
        factors[y] = f

    return factors


def producao_anual(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Produção anual por produto 2024-2029.

    Os custos unitários são lidos de master/produtos.yaml (cip_unitario)
    e calibrados ao CMVMC_prod_2024 auditado.
    """
    from .vendas import vendas_anuais

    df_v = vendas_anuais(a, base, sched)

    qty_por_ano = (
        df_v.groupby(["ano", "produto"])["qtd"]
        .sum()
        .reset_index()
        .rename(columns={"qtd": "qty_vendida"})
    )

    cups_2024 = cups_por_produto_2024(a, base)

    factors = _cost_growth_factors(a)
    dmi_pa = a.prazos["DMI_PA_dias"]

    qtd_2024 = _qty_totais_2024(a, base)

    peso_total = sum(
        cups_2024[p] * qtd_2024.get(p, 0.0)
        for p in PRODUTOS
    )

    cmvmc_prod_2024 = (
        float(base.raw["dr_2024_real"]["cmvmc"])
        - float(base.totais["CMVMC_Mercadorias_2024"])
    )

    rows = []
    pa_ef_prev: dict[str, float] = {}

    for y in ALL_YEARS:
        f = factors[y]

        for p in PRODUTOS:
            cup = cups_2024[p] * f

            mask = (
                (qty_por_ano["ano"] == y)
                & (qty_por_ano["produto"] == p)
            )

            qty_v = (
                float(qty_por_ano[mask]["qty_vendida"].iloc[0])
                if mask.any()
                else 0.0
            )

            cmvmc_v = qty_v * cup
            pa_ef = (cmvmc_v / 365.0) * dmi_pa

            if y == 2024:
                peso_p = (
                    (cups_2024[p] * qtd_2024.get(p, 0.0)) / peso_total
                    if peso_total > 0
                    else 0.0
                )

                pa_ei = (cmvmc_prod_2024 / 365.0) * dmi_pa * peso_p
            else:
                pa_ei = pa_ef_prev.get(p, pa_ef)

            var_pa = pa_ef - pa_ei
            cmvmc_p = max(0.0, cmvmc_v + var_pa)

            qty_prod = cmvmc_p / cup if cup > 0 else 0.0

            pa_ef_prev[p] = pa_ef

            rows.append(
                {
                    "ano": y,
                    "produto": p,
                    "qty_vendida": qty_v,
                    "qty_produzida": qty_prod,
                    "cup": cup,
                    "cip_unitario": _cip_unitarios(a)[p],
                    "cmvmc_vendas": cmvmc_v,
                    "cmvmc_prod": cmvmc_p,
                    "pa_stock_ei": pa_ei,
                    "pa_stock_ef": pa_ef,
                    "var_pa": var_pa,
                }
            )

    return pd.DataFrame(rows)


def producao_mensal_2025(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Produção mensal 2025 por produto."""
    df_anual = producao_anual(a, base, sched)
    df_2025 = df_anual[df_anual["ano"] == 2025]

    saz = a.sazonalidade.get("PT", [])

    if isinstance(saz, list):
        saz = {
            m: saz[i]
            for i, m in enumerate(MESES)
        }

    rows = []

    for _, r in df_2025.iterrows():
        for m in MESES:
            rows.append(
                {
                    "mes": m,
                    "produto": r["produto"],
                    "qty_produzida": r["qty_produzida"] * saz[m],
                    "cmvmc_prod": r["cmvmc_prod"] * saz[m],
                    "cup": r["cup"],
                    "cip_unitario": r["cip_unitario"],
                }
            )

    return pd.DataFrame(rows)
