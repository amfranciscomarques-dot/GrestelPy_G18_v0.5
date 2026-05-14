"""
Módulo: engine/operacoes/cmvmc.py — CMVMC: Custo de Mercadorias Vendidas e Matérias-Primas
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
CMVMC (Custo de Mercadorias Vendidas e Matérias-Primas Consumidas) é o custo direto
de produção/aquisição dos produtos vendidos. É o principal componente dos custos.

CONCEITO CONTABILÍSTICO:
  Margem Bruta = Receita de Vendas - CMVMC
  Taxa de Margem Bruta = Margem Bruta / Receita (quanto % fica na empresa após custos diretos)

  Exemplo:
    - Receita: €1.000.000
    - CMVMC: €600.000 (60% da receita)
    - Margem Bruta: €400.000 (40% da receita)
    - EBITDA (com FSE): €400.000 - FSE (custos operacionais)

ESTRUTURA DO CMVMC:

┌─────────────────────────────────────────────────────────────────┐
│ CMVMC TOTAL = CMVMC_PRODUTOS + CMVMC_MERCADORIAS                │
│                                                                 │
│ CMVMC_PRODUTOS:                                                 │
│   = Σ (Quantidade Vendida × Custo Unitário Produção)            │
│   = Σ (QTY_venda × CUP) por produto                             │
│                                                                 │
│   CUP (Custo Unitário de Produção):                            │
│     - Base 2024: custo de produção de 1 unidade                │
│     - Cresce com inflação de matérias-primas, mão-de-obra      │
│     - Reduz com ganhos de eficiência (economia de escala)      │
│     - CUP_ano = CUP_2024 × (1 + inflação) × (1 - eficiência)   │
│                                                                 │
│   Intensidade de Custo (por produto):                          │
│     - Produtos mais complexos têm CUP maior                    │
│     - Exemplo: Produto Premium = CUP × 1,2 (20% mais caro)     │
│                                                                 │
│ CMVMC_MERCADORIAS:                                              │
│   = Receita de Mercadorias × (1 - Margem Mercadorias)          │
│   = Σ (VN_merc × % custo)                                      │
│                                                                 │
│   Margem de Mercadorias: markup fixo (ex: 35% margem, 65% custo)
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

FATORES DE CRESCIMENTO (Dinâmica de Custos):
  1. Inflação de Matérias-Primas: custo de aquisição sobe
  2. Inflação de Mão-de-Obra: pessoal produção fica mais caro
  3. Ganhos de Eficiência: melhor gestão, tecnologia, reduz custo/unidade
  4. Mix de Produtos: se vender mais produtos premium, CMVMC% sobe
  5. Ecogres (se ativa): subcontratação reduz CMVMC (outsourcing)

IMPACTO NA DR:
  - CMVMC é geralmente 50-70% da receita em empresas industriais
  - Uma redução de 1% em CMVMC = aumento de 1% em margem bruta
  - Crítico para rentabilidade e competitividade

EXEMPLO CÁLCULO:
  Produto A: 100 unidades vendidas × €15 CUP = €1.500 CMVMC
  Produto B: 200 unidades vendidas × €20 CUP = €4.000 CMVMC
  Mercadorias: €50.000 receita × 65% custo = €32.500 CMVMC
  ─────────────────────────────────────────────────────────────
  CMVMC TOTAL = €1.500 + €4.000 + €32.500 = €38.000
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, ALL_YEARS, YEARS, MESES, PRODUTOS
from .vendas import _monthly_cum_index, _monthly_rates, _saz_to_dict
from . import produção as prod_mod


def cmvmc_anual(
    a: Assumptions,
    base: Base2024,
    df_vendas: pd.DataFrame,
    df_merc: pd.DataFrame,
) -> pd.DataFrame:
    """CMVMC anual total e desagregado entre produtos e mercadorias.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        df_vendas: DataFrame de vendas anuais de produtos.
        df_merc: DataFrame de vendas anuais de mercadorias.
            Mantido por compatibilidade, embora o cálculo atual use sobretudo
            os totais base e drivers de crescimento.

    Returns:
        DataFrame com colunas:
        ano, cmvmc_prod, cmvmc_merc, cmvmc.
    """
    # Mantido por compatibilidade futura.
    _ = df_merc

    cups_2024 = prod_mod.cups_por_produto_2024(a, base)

    factors = prod_mod._cost_growth_factors(a)

    qty_por_ano = (
        df_vendas.groupby(["ano", "produto"])["qtd"]
        .sum()
        .reset_index()
        .rename(columns={"qtd": "qty_vendida"})
    )

    dmi_pa = float(a.prazos["DMI_PA_dias"])

    cmvmc_prod_2024_total = (
        float(base.raw["dr_2024_real"]["cmvmc"])
        - float(base.totais["CMVMC_Mercadorias_2024"])
    )

    qtd_2024 = prod_mod._qty_totais_2024(a, base)

    peso_total = sum(
        cups_2024.get(p, 0.0) * qtd_2024.get(p, 0.0)
        for p in PRODUTOS
    )

    pa_ef_prev: dict[str, float] = {}
    prod_by_year: dict[int, float] = {}

    for y in ALL_YEARS:
        f = factors[y]
        total_prod_y = 0.0

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

                pa_ei = (cmvmc_prod_2024_total / 365.0) * dmi_pa * peso_p
            else:
                pa_ei = pa_ef_prev.get(p, pa_ef)

            var_pa = pa_ef - pa_ei
            cmvmc_p = max(0.0, cmvmc_v + var_pa)

            pa_ef_prev[p] = pa_ef
            total_prod_y += cmvmc_p

        prod_by_year[y] = total_prod_y

    cmvmc_merc_2024 = float(base.totais["CMVMC_Mercadorias_2024"])

    block = a.cenario_block()

    vol_block = (
        block.get("volume_vendas")
        or a.raw.get("crescimento_volume_vendas", {})
    )

    cost_block = (
        block.get("custo_mercadorias")
        or a.raw.get("crescimento_custo_mercadorias", {})
    )

    cum_vol = _monthly_cum_index(_monthly_rates(vol_block))
    cum_cost = _monthly_cum_index(_monthly_rates(cost_block))

    saz_pt = _saz_to_dict(a.sazonalidade.get("PT", []))

    vol_f = sum(
        saz_pt[m] * cum_vol[m]
        for m in MESES
    )

    cost_f = sum(
        saz_pt[m] * cum_cost[m]
        for m in MESES
    )

    cmvmc_merc_2025 = cmvmc_merc_2024 * vol_f * cost_f

    g_cost_yr = a.cresc_2026_2029("custo_mercadorias")
    g_vol_yr = a.cresc_2026_2029("volume_vendas")

    merc_by_year: dict[int, float] = {
        2024: cmvmc_merc_2024,
        2025: cmvmc_merc_2025,
    }

    prev = cmvmc_merc_2025

    for y in YEARS[1:]:
        prev = prev * (1 + g_cost_yr[y]) * (1 + g_vol_yr[y])
        merc_by_year[y] = prev

    rows = []

    for y in ALL_YEARS:
        cmvmc_prod = prod_by_year[y]
        cmvmc_merc = merc_by_year[y]

        rows.append(
            {
                "ano": y,
                "cmvmc_prod": cmvmc_prod,
                "cmvmc_merc": cmvmc_merc,
                "cmvmc": cmvmc_prod + cmvmc_merc,
            }
        )

    return pd.DataFrame(rows)
