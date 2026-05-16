"""
Módulo: engine/financas/financiamento.py — Financiamento: Empréstimos, Juros e Dívida
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula a estrutura de financiamento (dívida) e respetiva carga financeira (juros).
Financiamento é crítico para empresas que investem em imobilizado (máquinas, edifícios).

CONCEITOS FUNDAMENTAIS:

┌─────────────────────────────────────────────────────────────────┐
│ DÍVIDA FINANCEIRA (CAPITAL EM DÍVIDA)                           │
│                                                                 │
│ Estrutura:                                                     │
│   - Empréstimo Principal (draw-down): montante total solicitado│
│   - Taxa de Juro: % a.a. (ex: 3% ao ano)                      │
│   - Prazo: nº de anos para amortizar (ex: 8 anos)             │
│   - Carência: período sem amortizações (ex: 2 anos)           │
│                                                                 │
│ EXEMPLO: Empréstimo €5.000.000 a 3% durante 8 anos            │
│   Ano 1-2 (Carência): Paga só juros (€150.000/ano)            │
│   Ano 3-10 (Amortização): Amortiza + juros (decrescente)      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ CÁLCULO DE JUROS (Carga Financeira)                            │
│                                                                 │
│ Juros = Saldo da Dívida no início do período × Taxa de Juro   │
│                                                                 │
│ EXEMPLO AMORTIZAÇÃO LINEAR:                                    │
│   Empréstimo: €1.000.000                                       │
│   Taxa: 5% a.a.                                                │
│   Prazo: 5 anos (sem carência)                                 │
│                                                                 │
│   Ano 1:                                                       │
│     Saldo Inicial: €1.000.000                                  │
│     Juros: €1.000.000 × 5% = €50.000                          │
│     Amortização: €1.000.000 / 5 = €200.000                    │
│     Saldo Final: €800.000                                      │
│                                                                 │
│   Ano 2:                                                       │
│     Saldo Inicial: €800.000                                    │
│     Juros: €800.000 × 5% = €40.000 (desceu!)                  │
│     Amortização: €200.000 (linear)                             │
│     Saldo Final: €600.000                                      │
│                                                                 │
│   ... (similar para anos 3-5)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

IMPACTO FINANCEIRO:

  1. Na DR (Demonstração de Resultados):
     - Juros são despesa financeira (reduz RAI)
     - Amortizações NÃO aparecem na DR (aparecem na DFC)
     - Impacto: Juros decrescem ano a ano (menos dívida = menos juros)

  2. Na DFC (Demonstração de Fluxos de Caixa):
     - Juros: saída de caixa (pagamento efetivo)
     - Amortizações: saída de caixa (reembolso do principal)
     - Total Fluxo Financiamento = Juros + Amortizações (saída)

  3. Na Análise de Rentabilidade:
     - EBIT (Earnings Before Interest & Tax): exclui juros
     - Comparável entre empresas (ignora estrutura financeira)
     - RAI (Result After Interest): inclui juros
     - EBIT > Juros anuais = saudável (cobre carga financeira)

MÉTRICAS IMPORTANTES:

  - Dívida Líquida = Dívida Total - Caixa
  - Rácio de Endividamento = Dívida / Patrimônio
    * <1.0: conservador
    * 1.0-2.0: moderado
    * >2.0: agressivo (risco)

  - Cobertura de Juros = EBIT / Juros
    * >5: excelente (folga para pagar juros)
    * 2-5: aceitável
    * <2: risco elevado (juros muitos grandes)

  - Vida Média da Dívida = (Σ Amortizações × Anos) / Dívida Total
    * Indica quantos anos até estar livre de dívida

EXEMPLO IMPACTO NO MODELO:
  - Empréstimo é input (YAML: sched.financiamento)
  - Plano de amortização é pré-calculado (não dinâmico com vendas)
  - Juros crescem/descem determinísticos (menos flexibilidade)
  - Se vendas caem e não pode pagar juros = risco de insolvência
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Schedules, Assumptions, ALL_YEARS


def _hub_fin(a: Assumptions) -> dict[int, dict] | None:
    """Retorna impacto financeiro Hub por ano, ou None se Hub desativado."""
    try:
        raw_hub = a.raw.get("hub_logistico", {})

        if not raw_hub.get("incluir_hub", False):
            return None

        from ..projetos import hub_logistico as hub_mod

        df = hub_mod.hub_financing(raw_hub)

        return df.set_index("ano").to_dict(orient="index")

    except Exception:
        return None


def _get_fin_value(
    fin: dict,
    section: str,
    year: int,
    default: float = 0.0,
) -> float:
    """Obtém valor de sched.financiamento com fallback seguro."""
    try:
        return float(fin[section][year])
    except (KeyError, TypeError, ValueError):
        return float(default)


def financiamento_anual(
    sched: Schedules,
    a: Assumptions | None = None,
) -> pd.DataFrame:
    """Tabela anual de financiamento: juros, capital em dívida e amortizações."""
    fin = sched.financiamento

    # Fallback antigo apenas se schedules.yaml não tiver juros_total[2024].
    juros_dr_2024_fallback = 528_161.02

    hub_impact = _hub_fin(a) if a is not None else None

    rows = []

    for y in ALL_YEARS:
        juros = _get_fin_value(
            fin,
            "juros_total",
            y,
            default=juros_dr_2024_fallback if y == 2024 else 0.0,
        )

        cap_fim = _get_fin_value(
            fin,
            "capital_divida_total_fim_ano",
            y,
            default=0.0,
        )

        amort = _get_fin_value(
            fin,
            "amortizacoes_capital",
            y,
            default=0.0,
        )

        emp_nc = _get_fin_value(
            fin,
            "emprestimos_NC",
            y,
            default=0.0,
        )

        emp_c = _get_fin_value(
            fin,
            "emprestimos_C",
            y,
            default=0.0,
        )

        hub_juros = 0.0
        hub_cap_fim = 0.0
        hub_incluido = False

        if hub_impact and y in hub_impact:
            h = hub_impact[y]

            # Usa juros_expensed (não juros totais) para não reconhecer na DR
            # os juros capitalizados no AFT (NCRF 10). Os juros_capitalizados
            # aumentam o custo do ativo e são depreciados — não são gasto do período.
            hub_juros = float(h.get("juros_expensed", h.get("juros", 0.0)))
            hub_saldo = float(h.get("saldo_fim", 0.0))
            hub_amort = float(h.get("amortizacao", 0.0))
            hub_emp_nc = float(h.get("emprestimos_nc", 0.0))
            hub_emp_c = float(h.get("emprestimos_c", 0.0))

            cap_fim += hub_saldo
            amort += hub_amort
            emp_nc += hub_emp_nc
            emp_c += hub_emp_c

            hub_cap_fim = hub_saldo
            hub_incluido = True

        rows.append(
            {
                "ano": y,
                "juros_total": juros + hub_juros,
                "juros_base": juros,
                "juros_hub": hub_juros,
                "capital_divida_total_fim": cap_fim,
                "amortizacoes_capital": amort,
                "emprestimos_NC": emp_nc,
                "emprestimos_C": emp_c,
                "hub_capital_fim": hub_cap_fim,
                "hub_incluido": hub_incluido,
            }
        )

    return pd.DataFrame(rows)