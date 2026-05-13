"""
Módulo: engine/pessoal/pessoal.py — Gastos com Pessoal (Folha de Salários)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula o custo total anual de pessoal (salários + encargos patronais).
Gastos com pessoal é geralmente 15-30% da receita (segundo maior custo após CMVMC).

ESTRUTURA DE CUSTOS COM PESSOAL:

┌─────────────────────────────────────────────────────────────────┐
│ CUSTO TOTAL PESSOAL = Nº EFECTIVOS × CUSTO MÉDIO POR PESSOA     │
│                                                                 │
│ CUSTO MÉDIO POR PESSOA = Salário Bruto + Encargos Patronais    │
│                                                                 │
│ Componentes:                                                   │
│   1. Salário Bruto: valor contratual (antes de impostos)       │
│   2. Contribuições Sociais (Patronais): ~23,75% do salário    │
│      (Segurança Social do patrão)                              │
│   3. Imposto sobre Remunerações: 10% (retenção em conta)       │
│   → Custo Real = Salário × (1 + 23,75%)                        │
│                                                                 │
│ EXEMPLO:                                                       │
│   Salário Bruto: €1.000                                        │
│   Encargos Patronais (23,75%): €238                            │
│   Custo Real da Empresa: €1.238                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

EVOLUÇÃO TEMPORAL:

  2024: Dados Reais (input)
    - Total Pessoal: €X (auditado)
    - Headcount (Nº de pessoas): N

  2025: Período Parcial + Crescimento (Janeiro-Setembro, 9 meses)
    - Custo Médio 2024: X / N
    - Custo Médio 2025: Custo_2024 × (1 + taxa_inflação_2025)
      (tipicamente 2-3%, assinado em YAML)
    - Headcount 2025: N × (1 + crescimento_HC)
      (pode haver recrutamentos ou despedimentos)
    - Total 2025: Headcount_2025 × Custo_Médio_2025

  2026-2029: Crescimento com Elasticidade (Janeiro-Dezembro completo)
    - Crescimento Base: taxa_fixa_pessoal (ex: 2% a.a.)
    - Crescimento Adicional: α × ΔVN% (elasticidade com receita)

    Fórmula:
      Pessoal(y) = Pessoal(y-1) × [1 + g_fixo + α × (VN(y)/VN(y-1) - 1)]

    Interpretação:
      α = 0.40 (sem Hub): se vendas sobem 10%, pessoal sobe 4% extra
                          (riqueza de operações, necessidade marginal)
      α = 0.15 (com Hub): se vendas sobem 10%, pessoal sobe 1,5% extra
                          (Hub mais automatizado, menos pessoal proporcional)

IMPACTO NA DR:
  - Gastos com Pessoal é linha principal da DR
  - Afeta EBITDA = Receita - CMVMC - Pessoal - FSE
  - Crescimento não proporcional a vendas = pressão em margens

EXEMPLO COMPLETO:
  2024: Pessoal €3.000.000, VN €10.000.000 (30% do VN)
  2025: Pessoal €3.090.000 (30% crescimento custo_médio)
        Pessoal% = 30% (mantém proporção)
  2026: VN cresce 5% → €10.500.000
        Pessoal cresce 2% (base) + 0.4 × 5% (elasticidade)
        Crescimento Total = 2% + 2% = 4%
        Pessoal 2026 = €3.213.600
        Pessoal% = 30,6% (sobe ligeiramente, menos eficiência)
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, ALL_YEARS, YEARS, MESES


def _taxa_pessoal_2025_efetiva(a: Assumptions) -> float:
    """Taxa anual efectiva de crescimento do custo médio de pessoal em 2025.

    Usa `taxa_cresc_custo_2025` de assumptions.yaml como base anual.
    Se `acrescimos_mensais` estiver definido em `crescimento_pessoal`
    (custos_mensal.yaml), calcula a taxa composta a partir dos 12 meses:
        taxa_ef = ∏(1 + r_m  para m em MESES) - 1
    Sem acréscimos, o resultado é idêntico ao anterior.
    """
    base_anual = float(a.taxa_pessoal_2025())
    driver_block = a._driver_block("pessoal")
    acrescimos = driver_block.get("acrescimos_mensais") or driver_block.get("overrides_mensais") or {}

    if not acrescimos:
        return base_anual

    from ..operacoes.vendas import _monthly_rates

    rates = _monthly_rates({"base_2025": base_anual, "acrescimos_mensais": acrescimos})
    factor = 1.0
    for m in MESES:
        factor *= 1.0 + rates[m]
    return factor - 1.0


def pessoal_anual(
    a: Assumptions,
    base: Base2024,
    df_vn: pd.DataFrame,
) -> pd.DataFrame:
    """Gastos anuais com pessoal com elasticidade face ao VN para 2026+.

    2025:
        custo_medio_2024 = custo_total_2024 / headcount_2024
        custo_medio_2025 = custo_medio_2024 × (1 + taxa_2025)
        total_2025 = headcount_2025 × custo_medio_2025

    2026-2029:
        Gastos_Pessoal(y) = Gastos_Pessoal(y-1) × [1 + cresc_fixo(y) + alpha × ΔVN%(y)]
    """
    # Mantido por compatibilidade futura; atualmente os dados vêm de assumptions.
    _ = base

    total_2024 = float(a.pessoal_params["custo_total_2024_auditado"])
    hc_2024 = float(a.pessoal_params["headcount_2024"])
    hc_2025 = float(a.pessoal_params["headcount_2025"])

    ajuste_hc = a.pessoal_params.get("ajuste_headcount") or {}

    custo_medio_2024 = total_2024 / hc_2024 if hc_2024 else 0.0

    taxa_2025 = _taxa_pessoal_2025_efetiva(a)
    custo_medio_2025 = custo_medio_2024 * (1 + taxa_2025)
    total_2025 = hc_2025 * custo_medio_2025

    hub_ativo = a.raw.get("hub_logistico", {}).get("incluir_hub", False)

    ep = a.raw.get("elasticidade_pessoal", {})
    alpha = (
        float(ep.get("alpha_com_hub", 0.15))
        if hub_ativo
        else float(ep.get("alpha_sem_hub", 0.40))
    )

    g_pessoal_yr = a.cresc_2026_2029("pessoal")
    vn_map = df_vn.set_index("ano")["vn_total"].to_dict()

    vals = {
        2024: total_2024,
        2025: total_2025,
    }

    hc_effective = {
        2024: hc_2024,
        2025: hc_2025,
    }

    for y in YEARS[1:]:
        cresc_fixo = float(g_pessoal_yr[y])

        vn_y = float(vn_map.get(y, 0.0))
        vn_prev = float(vn_map.get(y - 1, 0.0))

        delta_vn_pct = (vn_y - vn_prev) / vn_prev if vn_prev else 0.0

        base_cost = vals[y - 1] * (
            1 + cresc_fixo + alpha * delta_vn_pct
        )

        delta_fte = float(ajuste_hc.get(y, ajuste_hc.get(str(y), 0.0)))

        hc_prev = hc_effective.get(y - 1, hc_2025)
        custo_medio_y = vals[y - 1] / hc_prev if hc_prev else 0.0

        ajuste_custo = delta_fte * custo_medio_y

        vals[y] = base_cost + ajuste_custo
        hc_effective[y] = hc_prev + delta_fte

    return pd.DataFrame(
        [
            {
                "ano": y,
                "gastos_pessoal": vals[y],
            }
            for y in ALL_YEARS
        ]
    )