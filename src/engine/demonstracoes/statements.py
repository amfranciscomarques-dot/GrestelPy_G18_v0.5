"""
Módulo: engine/statements.py — Orquestrador das Demonstrações Financeiras Consolidadas
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Este módulo coordena a construção das três demonstrações financeiras consolidadas
que formam o núcleo da análise financeira de uma empresa:

  1. DR (Demonstração de Resultados):
     - Receitas e custos operacionais (vendas, CMV, CMVMC, pessoal, FSE);
     - Resultados operacionais (EBIT);
     - Resultados financeiros (juros, subsídios);
     - Resultado antes de impostos e imposto sobre o rendimento;
     - Resultado líquido (lucro ou prejuízo final).

  2. BALANÇO (Situação Financeira):
     - Ativo: contas a receber, inventário, imobilizado, caixa;
     - Passivo: fornecedores, empréstimos, contas a pagar;
     - Capitais Próprios: capital social, reservas, resultados retidos.

  3. DFC (Demonstração de Fluxos de Caixa):
     - Fluxos da atividade operacional (entradas/saídas de caixa);
     - Fluxos de investimento (aquisição de ativos);
     - Fluxos de financiamento (empréstimos, reembolsos).

LÓGICA DE CONSTRUÇÃO (Ordem Crítica):
  1. Primeiro: DR (contém receitas líquidas, custos, lucro → base para o balanço)
  2. Segundo: BALANÇO (usa DR para reconciliação, calcula saldos de contas)
  3. Terceiro: DFC (usa DR e Balanço para calcular movimentos de caixa reais)

Esta ordem garante consistência financeira (não há circularidades, cada demonstração
usa outputs anteriores sem dependências cíclicas).
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules
from ..operacional import vendas as _vendas_mod
from .dr import build_dr
from .balanco import build_balanco
from .dfc import build_dfc


def build_statements(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_eoep_mensal: "pd.DataFrame | None" = None,
    df_prod: "pd.DataFrame | None" = None,
    df_merc: "pd.DataFrame | None" = None,
    df_total: "pd.DataFrame | None" = None,
) -> dict[str, pd.DataFrame]:
    """
    Constrói as três demonstrações financeiras consolidadas.

    PARÂMETROS:
      a (Assumptions): Hipóteses operacionais (crescimentos, custos, tax rate, etc.)
      base (Base2024): Saldos iniciais 2024 (starting balance para projeção)
      sched (Schedules): Tabelas plurianuais pré-calculadas (juros, depr., etc.)
      df_eoep_mensal: Calendário EOEP mensal de 2025 (opcional). Quando fornecido,
          os saldos EOEP de 2025 no Balanço são derivados do calendário mensal.
      df_prod, df_merc, df_total: Vendas pré-calculadas (opcional). Quando fornecidos,
          evita recomputation em build_dr e build_balanco.

    RETORNA:
      dict[str, DataFrame]: Dicionário com três DataFrames:
        - "dr": Demonstração de Resultados (anos 2024-2029, várias rubricas)
        - "balanco": Balanço (ativos, passivos, patrimônio por ano)
        - "dfc": Demonstração de Fluxos de Caixa (entrada/saída por ano)

    ORDEM CRÍTICA: DR → Balanço → DFC (dependências acíclicas)
    """
    if df_prod is None:
        df_prod = _vendas_mod.vendas_anuais(a, base, sched)
    if df_merc is None:
        df_merc = _vendas_mod.vendas_mercadorias_anuais(a, base)
    if df_total is None:
        df_total = _vendas_mod.resumo_anual(df_prod, df_merc)

    df_dr = build_dr(a, base, sched, df_prod=df_prod, df_merc=df_merc, df_total=df_total)
    df_balanco = build_balanco(
        a, base, sched, df_dr,
        df_eoep_mensal=df_eoep_mensal,
        df_prod=df_prod, df_merc=df_merc, df_total=df_total,
    )
    df_dfc = build_dfc(a, df_dr, df_balanco, sched, base)

    return {
        "dr": df_dr,
        "balanco": df_balanco,
        "dfc": df_dfc,
    }


__all__ = [
    "build_dr",
    "build_balanco",
    "build_dfc",
    "build_statements",
]