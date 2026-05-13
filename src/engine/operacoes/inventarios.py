"""
Módulo: engine/operacoes/inventarios.py — Inventários (Stock de Produtos)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula o saldo de inventários (stock) ao fim de cada período.
Inventários ligam o CMVMC (custo de produção) à gestão de caixa (crédito stock).

CONCEITO CONTABILÍSTICO:

  Inventário = mercadorias/produtos na posse da empresa que se destina à venda
  Categorias:
    1. Matérias-Primas (MP): recebidas de fornecedores, aguardam transformação
    2. Produtos em Curso (PA): em processo de manufatura
    3. Produtos Acabados (PF): prontos para venda, em armazém
    4. Mercadorias: compradas prontas para revenda (sem transformação)

  Período de Rotação (DMI - Dias de Médio Inventário):
    - DMI = nº de dias que o produto fica armazenado em média
    - Mais dias = mais capital circulante imobilizado
    - Exemplo: DMI_PA = 15 dias (produto leva 15 dias em produção)

┌─────────────────────────────────────────────────────────────────┐
│ CÁLCULO DE SALDO DE INVENTÁRIO (Método DMI)                    │
│                                                                 │
│ Saldo = (CMVMC / 365) × DMI_dias                               │
│                                                                 │
│ EXEMPLO:                                                       │
│   CMVMC Anual: €7.300.000 (€20.000/dia)                       │
│   DMI_PA (Produtos em Curso): 20 dias                         │
│   DMI_PF (Produtos Acabados): 30 dias                         │
│   DMI_MP (Matérias-Primas): 25 dias                           │
│                                                                 │
│   Saldo_PA = €20.000/dia × 20 dias = €400.000                │
│   Saldo_PF = €20.000/dia × 30 dias = €600.000                │
│   Saldo_MP = €20.000/dia × 25 dias = €500.000                │
│   TOTAL INVENTÁRIO = €1.500.000                               │
│                                                                 │
│ Interpretação:                                                 │
│   - €1.5M é capital circulante "congelado" em stock            │
│   - Reduzir DMI de 20 dias para 18 dias liberta €40K de caixa │
│   - Aumentar DMI prejudica fluxo de caixa                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

IMPACTO NA GESTÃO FINANCEIRA:

  1. Capital Circulante (Working Capital):
     - Inventário + Clientes - Fornecedores = Ciclo de Caixa
     - Stock alto = capital circulante alto = menos caixa livre
     - Gestão de stock (JIT) reduz inventário = liberta caixa

  2. Fluxo de Caixa:
     - Variação de Inventário é ajustamento na DFC
     - Se inventário sobe: caixa desce (dinheiro investido em stock)
     - Se inventário desce: caixa sobe (venda de stock = recuperação)

  3. Análise de Eficiência:
     - Rotação de Inventário = CMVMC / Inventário Médio
       * Maior rotação = melhor gestão (menos dias em stock)
     - Exemplo: Rotação = 5,5× (CMVMC €7.3M / Inventário €1.3M)
       → Cada unidade em stock circula 5,5 vezes/ano (66 dias)

VARIAÇÕES ESPERADAS:

  - Inventário cresce com CMVMC (mais produção = mais stock)
  - Crescimento não linear: DMI constante + CMVMC crescent = stock crescente
  - 2025 (período parcial): ajuste proporcional para 9 meses
  - Dinâmica positiva: crescimento de vendas → crescimento de stock necessário
  - Dinâmica negativa: redução de DMI → menor necessidade de stock

EXEMPLO COMPLETO (2 anos):
  Ano 1:
    CMVMC: €7.300.000
    DMI Médio: 30 dias
    Inventário: (€7.3M / 365) × 30 = €600.000

  Ano 2:
    CMVMC: €7.740.000 (crescimento 6%)
    DMI Médio: 30 dias (mantém eficiência)
    Inventário: (€7.74M / 365) × 30 = €636.000
    Variação: +€36.000 (caixa negativa: investimento em stock)
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, ALL_YEARS


def inventarios_anual(
    a: Assumptions,
    base: Base2024,
    df_cmvmc: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula saldos anuais de inventários por natureza.

    Metodologia DMI:
        PA = CMVMC_prod / 365 × DMI_PA_dias
        MP = CMVMC_prod / 365 × DMI_MP_dias
        Mercadorias = CMVMC_merc / 365 × DMI_Mercadorias_dias

    2024 usa o valor auditado do balanço.
    """
    inv_2024 = float(base.balanco["ativo_corrente"]["Inventarios"])
    merc_2024 = float(base.totais["Inventario_Final_Merc_2024"])

    dmi_pa = float(a.prazos["DMI_PA_dias"])
    dmi_mp = float(a.prazos["DMI_MP_dias"])
    dmi_merc = float(a.prazos["DMI_Mercadorias_dias"])

    cmvmc_idx = df_cmvmc.set_index("ano")

    has_breakdown = (
        "cmvmc_prod" in cmvmc_idx.columns
        and "cmvmc_merc" in cmvmc_idx.columns
    )

    cmvmc_merc_2024 = float(base.totais["CMVMC_Mercadorias_2024"])
    cmvmc_total_2024 = float(base.raw["dr_2024_real"]["cmvmc"])

    merc_share = (
        cmvmc_merc_2024 / cmvmc_total_2024
        if cmvmc_total_2024 > 0
        else 0.08
    )

    rows = []
    inv_prev = inv_2024

    for y in ALL_YEARS:
        if y == 2024:
            rows.append(
                {
                    "ano": 2024,
                    "mp_inventario": inv_2024 - merc_2024,
                    "pa_inventario": 0.0,
                    "merc_inventario": merc_2024,
                    "inventarios": inv_2024,
                    "var_inventarios": float(
                        base.raw["dr_2024_real"].get("var_inventarios", 0.0)
                    ),
                }
            )

            inv_prev = inv_2024
            continue

        cmvmc_total = float(cmvmc_idx.loc[y, "cmvmc"])

        if has_breakdown:
            cmvmc_prod = float(cmvmc_idx.loc[y, "cmvmc_prod"])
            cmvmc_merc = float(cmvmc_idx.loc[y, "cmvmc_merc"])
        else:
            cmvmc_merc = cmvmc_total * merc_share
            cmvmc_prod = cmvmc_total - cmvmc_merc

        pa = (cmvmc_prod / 365.0) * dmi_pa
        mp = (cmvmc_prod / 365.0) * dmi_mp
        merc = (cmvmc_merc / 365.0) * dmi_merc

        total = pa + mp + merc
        var = total - inv_prev

        rows.append(
            {
                "ano": y,
                "mp_inventario": mp,
                "pa_inventario": pa,
                "merc_inventario": merc,
                "inventarios": total,
                "var_inventarios": var,
            }
        )

        inv_prev = total

    return pd.DataFrame(rows)
