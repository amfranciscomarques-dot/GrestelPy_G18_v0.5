"""
Módulo: engine/statements/dfc.py — Demonstração de Fluxos de Caixa (2024-2029)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
A Demonstração de Fluxos de Caixa (DFC) mostra como a caixa da empresa evoluiu,
dividindo as atividades em três categorias:

ESTRUTURA DA DFC:

┌─────────────────────────────────────────────────────────────────┐
│ FLUXOS DE CAIXA DO EXERCÍCIO                                    │
├─────────────────────────────────────────────────────────────────┤
│ A. ATIVIDADES OPERACIONAIS (Lucro → Caixa)                     │
│    Início: Resultado Líquido (da DR)                           │
│    Ajustamentos (não-caixa):                                   │
│      + Depreciação (redução de ativo, não caixa)              │
│      + Imparidades (provisão de crédito, não caixa)           │
│      - Variação de Clientes (↑ clientes = caixa negativa)     │
│      + Variação de Fornecedores (↑ fornecedores = caixa +)    │
│      - Variação de Inventário (↑ stock = caixa negativa)      │
│    Fluxo de Caixa Operacional (FCO)                           │
│                                                                 │
│ B. ATIVIDADES DE INVESTIMENTO (Ativo Fixo)                     │
│    - Aquisição de imobilizado (máquinas, edifícios)           │
│    + Venda de ativos/imobilizado (recuperação caixa)          │
│    Fluxo de Caixa de Investimento (FCI)                       │
│                                                                 │
│ C. ATIVIDADES DE FINANCIAMENTO (Estrutura Financeira)         │
│    + Novos empréstimos/capital                                │
│    - Reembolso de empréstimos (amortizações)                 │
│    - Pagamento de juros (carga financeira)                    │
│    Fluxo de Caixa de Financiamento (FCF)                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ VARIAÇÃO LÍQUIDA DE CAIXA = FCO + FCI + FCF                    │
│                                                                 │
│ Caixa Final = Caixa Inicial + Variação Líquida                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MÉTODO INDIRETO vs MÉTODO DIRETO:
  Este modelo usa MÉTODO INDIRETO:
    1. Começa pelo Resultado Líquido (lucro contabilístico)
    2. Adiciona/subtrai ajustamentos (despesas não-caixa)
    3. Ajusta variações de contas correntes (clientes, fornecedores)
    4. Resultado: Fluxo de Caixa Operacional (mais realista que lucro)

LÓGICA CRÍTICA (Por que DR ≠ Fluxo de Caixa):
  Exemplo: Empresa com Lucro €100K mas Clientes em crescimento
    - DR: Lucro = €100K (receita reconhecida, ainda não cobrada)
    - Clientes aumentaram €30K (dinheiro ainda não recebido)
    - Caixa Real = €100K - €30K = €70K

  Motivo: Contabilidade vs Caixa:
    - Contabilidade (Acuidade): reconhece receita ao momento da venda
    - Caixa (Tesouraria): conta só o dinheiro efetivamente recebido

IMPORTÂNCIA PRÁTICA:
  - Uma empresa pode ser lucrativa (DR positiva) mas sem caixa (insolvente)
  - Fluxo de caixa é crítico para: pagamentos, investimentos, sobrevivência
  - Gestão de tesouraria foca no fluxo de caixa, não no lucro
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS


def _load_hub_dr(a: Assumptions) -> dict[int, dict] | None:
    """Carrega impactos do Hub na DR, necessários para NFM/inventário libertado."""
    try:
        if not a.raw.get("hub_logistico", {}).get("incluir_hub", False):
            return None

        from ..subsidiarias import hub_logistico as hub_mod

        hub = hub_mod.load()
        return hub_mod.hub_dr_impact(hub)
    except Exception:
        return None


def _load_hub_dfc(a: Assumptions) -> dict[int, dict] | None:
    """Carrega impactos do Hub na DFC, ou None se o Hub estiver desativado."""
    try:
        if not a.raw.get("hub_logistico", {}).get("incluir_hub", False):
            return None

        from ..subsidiarias import hub_logistico as hub_mod

        hub = hub_mod.load()
        return hub_mod.hub_dfc_impact(hub)
    except Exception:
        return None


def build_dfc(
    a: Assumptions,
    df_dr: pd.DataFrame,
    df_balanco: pd.DataFrame,
    sched: Schedules,
    base: Base2024,
) -> pd.DataFrame:
    """Constrói a Demonstração de Fluxos de Caixa pelo método indireto."""
    rows = []

    payout = a.distribuicao["payout_ratio"]
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    hub_dfc = _load_hub_dfc(a)
    hub_dr = _load_hub_dr(a)

    for y in ALL_YEARS:
        rl = float(df_dr[df_dr.ano == y]["rl"].iloc[0])
        dep = -float(df_dr[df_dr.ano == y]["depreciacoes"].iloc[0])
        imp = -float(df_dr[df_dr.ano == y]["imparidades"].iloc[0])
        juros = -float(df_dr[df_dr.ano == y]["juros"].iloc[0])
        rend_fin = float(df_dr[df_dr.ano == y]["rend_financeiros"].iloc[0])
        irc = -float(df_dr[df_dr.ano == y]["irc"].iloc[0])

        if y == 2024:
            d24 = base.raw["dfc_2024_real"]

            fluxo_op = d24["fluxo_operacional"]
            op_pre_nfm = rl + dep + imp + juros - rend_fin

            # Mantém a lógica original para derivar variação de NFM implícita em 2024.
            var_nfm = fluxo_op - op_pre_nfm - (-irc)

            fluxo_inv = d24["fluxo_investimento"]
            fluxo_fin = d24["fluxo_financiamento"]
            var_caixa = fluxo_op + fluxo_inv + fluxo_fin

            rows.append(
                {
                    "ano": 2024,
                    "rl": rl,
                    "dep_amort": dep,
                    "imparidades": imp,
                    "juros_pagos": juros,
                    "rend_fin": -rend_fin,
                    "op_pre_nfm": op_pre_nfm,
                    "var_nfm": var_nfm,
                    "irc_pago": -irc,
                    "fluxo_operacional": fluxo_op,
                    "pag_aft": d24["capex_aft"],
                    "pag_intang": 0.0,
                    "div_recebidos": d24["dividendos_recebidos"],
                    "hub_capex": 0.0,
                    "hub_pt2030": 0.0,
                    "fluxo_investimento": fluxo_inv,
                    "rec_emprestimos": d24["rec_emprestimos"],
                    "pag_emprestimos": d24["pag_emprestimos"],
                    "juros_pagos_fin": -juros,
                    "hub_amortizacao": 0.0,
                    "var_linha_cp": 0.0,
                    "pag_dividendos": 0.0,
                    "fluxo_financiamento": fluxo_fin,
                    "variacao_caixa": var_caixa,
                }
            )

            continue

        row_y = df_balanco[df_balanco.ano == y].iloc[0]
        row_p = df_balanco[df_balanco.ano == (y - 1)].iloc[0]

        d_inv = row_p["inventarios"] - row_y["inventarios"]
        d_cli = row_p["clientes"] - row_y["clientes"]
        d_eoep_d = row_p["eoep_devedor"] - row_y["eoep_devedor"]
        d_out_ac = row_p["outros_ac"] - row_y["outros_ac"]

        d_forn = row_y["fornecedores"] - row_p["fornecedores"]
        d_eoep_c = row_y["eoep_credor"] - row_p["eoep_credor"]
        d_out_pc = row_y["outros_pc"] - row_p["outros_pc"]

        hub_inventario = (
            hub_dr[y].get("inventario_libertado", 0.0)
            if hub_dr and y in hub_dr
            else 0.0
        )

        op_pre_nfm = rl + dep + imp + juros - rend_fin

        var_nfm = (
            d_inv
            + d_cli
            + d_eoep_d
            + d_out_ac
            + d_forn
            + d_eoep_c
            + d_out_pc
            + hub_inventario
        )

        fluxo_op = op_pre_nfm + var_nfm - irc

        inv_aft = sched.investimento["investimento_aft_dfc"][y]
        inv_int = sched.investimento["investimento_intang_dfc"][y]
        div_recebidos = sched.investimento["dividendos_dfc"][y]

        hub_capex_y = 0.0
        hub_pt2030_y = 0.0

        if hub_dfc and y in hub_dfc:
            hub_capex_y = hub_dfc[y]["capex_hub"]
            hub_pt2030_y = hub_dfc[y]["pt2030_recebimento"]

        fluxo_inv = (
            -inv_aft
            - inv_int
            + div_recebidos
            + rend_fin
            + hub_capex_y
            + hub_pt2030_y
        )

        amort_base = sched.financiamento["amortizacoes_capital"][y]

        hub_amort_y = 0.0
        if hub_dfc and y in hub_dfc:
            hub_amort_y = hub_dfc[y]["amortizacao_banco"]

        amort_total = amort_base + abs(hub_amort_y)

        d_emp_total = (
            row_y["emprestimos_nc"]
            + row_y["emprestimos_c"]
            - row_p["emprestimos_nc"]
            - row_p["emprestimos_c"]
        )

        rec_emp = d_emp_total + amort_total
        d_linha_cp = row_y["linha_credito_cp"] - row_p["linha_credito_cp"]

        rl_prev = float(df_dr[df_dr.ano == (y - 1)]["rl"].iloc[0])
        rl_cur = float(df_dr[df_dr.ano == y]["rl"].iloc[0])

        pag_div = (
            -rl_prev * payout
            if rl_cur > 0 and y >= inicio_div
            else 0.0
        )

        fluxo_fin = rec_emp - amort_total - juros + d_linha_cp + pag_div
        var_caixa = fluxo_op + fluxo_inv + fluxo_fin

        rows.append(
            {
                "ano": y,
                "rl": rl,
                "dep_amort": dep,
                "imparidades": imp,
                "juros_pagos": juros,
                "rend_fin": -rend_fin,
                "op_pre_nfm": op_pre_nfm,
                "var_nfm": var_nfm,
                "irc_pago": -irc,
                "fluxo_operacional": fluxo_op,
                "pag_aft": -inv_aft,
                "pag_intang": -inv_int,
                "div_recebidos": div_recebidos,
                "hub_capex": hub_capex_y,
                "hub_pt2030": hub_pt2030_y,
                "fluxo_investimento": fluxo_inv,
                "rec_emprestimos": rec_emp,
                "pag_emprestimos": -amort_total,
                "juros_pagos_fin": -juros,
                "hub_amortizacao": hub_amort_y,
                "var_linha_cp": d_linha_cp,
                "pag_dividendos": pag_div,
                "fluxo_financiamento": fluxo_fin,
                "variacao_caixa": var_caixa,
            }
        )

    return pd.DataFrame(rows)