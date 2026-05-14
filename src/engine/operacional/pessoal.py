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


# ---------------------------------------------------------------------------
# Funções de detalhe — subdivisão contabilística e departamental
# ---------------------------------------------------------------------------

def pessoal_contab_anual(
    a: Assumptions,
    base: Base2024,
    df_vn: pd.DataFrame,
) -> pd.DataFrame:
    """Detalhe contabilístico dos gastos com pessoal por ano (Nota 28 / IAS 19).

    Rubricas:
        Remuneracoes    — salários brutos incl. subsídios de férias e de Natal
        Encargos_TSU    — contribuições patronais para Segurança Social (23,75%)
        Seguros_AT      — prémio de seguro de acidentes de trabalho (~1,32%)
        Outros_Encargos — residual: participação nos lucros, formação, outros

    Lógica temporal:
        2024 : valores auditados de pessoal_detalhe_2024 (base.yaml)
        2025+: Remuneracoes cresce proporcionalmente ao total de pessoal;
               TSU e SAT derivam da taxa legal aplicada às remunerações;
               Outros_Encargos = total − Remuneracoes − TSU − SAT.
    """
    df_total = pessoal_anual(a, base, df_vn)
    total_map = df_total.set_index("ano")["gastos_pessoal"].to_dict()

    tsu = float(a.pessoal_params.get("TSU_empregador", 0.2375))
    sat = float(a.pessoal_contab.get("sat_pct_remun", 0.0132))

    # Âncora 2024 — valores auditados
    det_2024 = (base.pessoal_detalhe or {}).get("rubricas_contab", {})
    remun_2024 = float(det_2024.get("Remuneracoes", a.pessoal_contab.get("Remuneracoes_2024", 0.0)))
    total_2024 = total_map.get(2024, 1.0)

    rows = []
    for y in ALL_YEARS:
        total_y = total_map.get(y, 0.0)
        # Remunerações: cresce proporcionalmente ao total de pessoal
        remun_y = remun_2024 * (total_y / total_2024) if total_2024 else 0.0
        tsu_y = remun_y * tsu
        sat_y = remun_y * sat
        outros_y = total_y - remun_y - tsu_y - sat_y

        rows.extend([
            {"ano": y, "rubrica": "Remuneracoes",    "valor": remun_y},
            {"ano": y, "rubrica": "Encargos_TSU",    "valor": tsu_y},
            {"ano": y, "rubrica": "Seguros_AT",      "valor": sat_y},
            {"ano": y, "rubrica": "Outros_Encargos", "valor": outros_y},
        ])

    return pd.DataFrame(rows)


def pessoal_depart_anual(
    a: Assumptions,
    base: Base2024,
    df_vn: pd.DataFrame,
) -> pd.DataFrame:
    """Detalhe departamental dos gastos com pessoal por ano.

    Departamentos: Producao · RD · Comercial · Financeira · Marketing

    Lógica temporal:
        2024 : valores imputados de pessoal_detalhe_2024 (base.yaml)
        2025+: pesos fixos de pessoal.departamentos (globais.yaml) aplicados
               ao total projetado por pessoal_anual().
               Os pesos são estáveis por omissão; alterar em globais.yaml
               para simular reequilíbrio da estrutura organizacional.
    """
    df_total = pessoal_anual(a, base, df_vn)
    total_map = df_total.set_index("ano")["gastos_pessoal"].to_dict()

    # Pesos de globais.yaml (somam 1.0)
    pesos = a.pessoal_departamentos
    if not pesos:
        pesos = {
            "Producao":   0.65,
            "RD":         0.05,
            "Comercial":  0.10,
            "Financeira": 0.12,
            "Marketing":  0.08,
        }

    # Âncora 2024 — valores imputados auditados
    det_2024 = (base.pessoal_detalhe or {}).get("departamentos", {})

    rows = []
    for y in ALL_YEARS:
        total_y = total_map.get(y, 0.0)
        if y == 2024 and det_2024:
            for dept, val in det_2024.items():
                rows.append({"ano": y, "departamento": dept, "valor": float(val)})
        else:
            soma_pesos = sum(float(v) for v in pesos.values()) or 1.0
            for dept, peso in pesos.items():
                rows.append({"ano": y, "departamento": dept, "valor": total_y * float(peso) / soma_pesos})

    return pd.DataFrame(rows)