"""
Módulo: engine/statements/balanco.py — Balanço / Demonstração da Situação Financeira (2024-2029)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
O Balanço apresenta a posição financeira de uma empresa numa data específica (fim de ano).
Segue a equação fundamental: ATIVO = PASSIVO + PATRIMÔNIO

ESTRUTURA DO BALANÇO:

┌─────────────────────────────────────────────────────────────────┐
│ ATIVO (Aplicação de Recursos)                                   │
├─────────────────────────────────────────────────────────────────┤
│ A. ATIVO CORRENTE (Curto Prazo: < 12 meses)                    │
│    1. Disponibilidades (Caixa, Bancos): dinheiro disponível    │
│    2. Contas a Receber (Clientes): crédito concedido          │
│    3. Inventários (Stock): mercadorias, matérias-primas        │
│    4. Outros ativos correntes (devedores diversos)             │
│                                                                 │
│ B. ATIVO NÃO CORRENTE (Longo Prazo: > 12 meses)               │
│    1. Imobilizado Corpóreo: máquinas, edifícios, equipamento   │
│    2. Imobilizado Incorpóreo: software, marcas, patentes       │
│    3. Investimentos Financeiros: ações em associadas          │
│    4. Créditos a Longo Prazo: empréstimos a clientes          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PASSIVO (Origem de Recursos - Obrigações)                       │
├─────────────────────────────────────────────────────────────────┤
│ A. PASSIVO CORRENTE (Curto Prazo: a pagar < 12 meses)         │
│    1. Contas a Pagar (Fornecedores): dívida a fornecedores    │
│    2. Outros Credores: salários a pagar, impostos a pagar      │
│    3. Empréstimos Bancários Curto Prazo: parcela 1 ano        │
│                                                                 │
│ B. PASSIVO NÃO CORRENTE (Longo Prazo: a pagar > 12 meses)    │
│    1. Empréstimos Bancários Longo Prazo: dívida futura        │
│    2. Outras Obrigações Financeiras: arrendamentos, etc.      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PATRIMÔNIO (Capital Próprio / Equity)                           │
├─────────────────────────────────────────────────────────────────┤
│    1. Capital Social: investimento inicial dos acionistas      │
│    2. Reservas: lucros retidos de anos anteriores              │
│    3. Resultado do Exercício: lucro/prejuízo do ano corrente   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

LÓGICA DE CÁLCULO:
  1. Inicia com saldos 2024 reais (inputs base.saldos)
  2. Calcula variações anuais de cada conta:
     - Caixa: Saldo Anterior ± Fluxo Operacional ± Invest. ± Financ.
     - Clientes: crescem com receita de vendas
     - Inventário: cresce com CMVMC
     - Fornecedores: crescem com compras (CMVMC)
     - Empréstimos: amortizam segundo plano de financiamento
     - Patrimônio: acumula resultados (lucro retido)
  3. Reconciliação: Ativo Total = Passivo + Patrimônio (sempre, por construção)

RECONCILIAÇÃO COM DEMONSTRAÇÃO DE RESULTADOS:
  - Lucro Retido = Resultado Líquido da DR
  - Variação de Clientes = origem/aplicação de caixa na DFC
  - Variação de Fornecedores = origem/aplicação de caixa na DFC
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS, YEARS
from ..operacional import vendas
from ..operacional import fse
from ..investimento import investimento
from ..financiamento import financiamento
from ..operacional import cmvmc
from ..operacional import clientes as conta_clientes
from ..modelo import eoep
from ..operacional import inventarios
from ..operacional import fornecedores


def _get_eoep_credor_2024(base: Base2024) -> float:
    """Obtém EOEP credor 2024 a partir dos dados base, com fallback seguro.

    Evita usar o valor hardcoded 460472.58.
    """
    candidates = [
        ("saldos", "EOEP_credor"),
        ("saldos", "eoep_credor"),
        ("saldos", "EOEP_Credor"),
    ]

    for attr, key in candidates:
        try:
            return float(getattr(base, attr)[key])
        except (AttributeError, KeyError, TypeError, ValueError):
            pass

    try:
        return float(base.raw["saldos"]["EOEP_credor"])
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    try:
        return float(base.raw["saldos"]["eoep_credor"])
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    # Fallback antigo para não quebrar caso a chave ainda não exista no YAML.
    return 460_472.58


def build_balanco(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_dr: pd.DataFrame,
) -> pd.DataFrame:
    """Constrói o Balanço 2024-2029 com treasury plug."""
    df_prod = vendas.vendas_anuais(a, base, sched)
    df_merc = vendas.vendas_mercadorias_anuais(a, base)
    df_total = vendas.resumo_anual(df_prod, df_merc)

    vn_2024_b = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025_b = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])

    factor_2025 = vn_2025_b / vn_2024_b if vn_2024_b else 1.0

    df_fse = fse.fse_anual(a, base, factor_2025)
    df_inv = investimento.investimento_anual(a, base, sched)
    df_fin = financiamento.financiamento_anual(sched, a)
    df_cmvmc = cmvmc.cmvmc_anual(a, base, df_prod, df_merc)
    df_cli = conta_clientes.clientes_anual(a, base, df_total)
    df_inv_st = inventarios.inventarios_anual(a, base, df_cmvmc)
    df_forn = fornecedores.fornecedores_anual(base, df_cmvmc, df_fse, a)

    cp = base.balanco["capital_proprio"]

    capital_social = cp["Capital_Social"]
    premios = cp["Premios_Emissao"]
    outros_ic = cp["Outros_IC_Proprio"]
    reservas = cp["Reservas_Legais"]
    ajust_af = cp["Ajust_AF"]
    outras_var = cp["Outras_Var_CP"]

    payout = a.distribuicao["payout_ratio"]
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    rt = {
        2024: cp["Resultados_Transitados"],
    }

    for y in YEARS:
        rl_prev = float(df_dr[df_dr.ano == (y - 1)]["rl"].iloc[0])
        rl_cur = float(df_dr[df_dr.ano == y]["rl"].iloc[0])

        if y == 2025:
            rt[y] = rt[y - 1] + base.balanco["capital_proprio"]["RL_2024"]
        else:
            div = rl_prev * payout if rl_cur > 0 and y >= inicio_div else 0.0
            rt[y] = rt[y - 1] + rl_prev - div

    irc_dict = {
        y: -float(df_dr[df_dr.ano == y]["irc"].iloc[0])
        for y in ALL_YEARS
    }

    df_eoep = eoep.eoep_anual(a, base, sched, irc_dict)

    base_outros_ac = base.balanco["ativo_corrente"]["Outros_AC"]
    eoep_dev_24 = base.saldos["EOEP_devedor"]
    outros_ac_2024 = base_outros_ac - eoep_dev_24

    eoep_cred_24 = _get_eoep_credor_2024(base)
    base_outros_pc_total = base.balanco["passivo"]["Outros_PC"]

    # Outros_PC operacional, excluindo EOEP credor porque EOEP é apresentado
    # separadamente no Balanço.
    outros_pc_24 = base_outros_pc_total - eoep_cred_24

    ab = sched.plurianual_AB
    g_73 = ab.get("AB73", 0.025)
    g_74 = ab.get("AB74", 0.02)

    out_ac_yr = {
        2024: outros_ac_2024,
    }

    outros_pc_yr = {
        2024: outros_pc_24,
    }

    for y in ALL_YEARS:
        if y == 2024:
            continue

        if y == 2025:
            # Mantém a base 2024 sem EOEP, evitando dupla contagem.
            out_ac_yr[y] = outros_ac_2024
            outros_pc_yr[y] = outros_pc_24
        else:
            out_ac = base_outros_ac

            for k in range(2026, y + 1):
                out_ac *= 1 + (g_73 if k == 2026 else g_74)

            eoep_d_y = float(df_eoep[df_eoep.ano == y]["eoep_devedor"].iloc[0])
            out_ac_yr[y] = out_ac - eoep_d_y

            outros_pc_yr[y] = outros_pc_yr[y - 1] * (1 + g_74)

    rows = []

    caixa_min = a.caixa["minima"]
    caixa_max = a.caixa["maxima"]

    for y in ALL_YEARS:
        aft = float(df_inv[df_inv.ano == y]["aft_liquido_fim"].iloc[0])
        outros_anc = float(
            df_inv[df_inv.ano == y]["goodwill_intang_subs_af_total"].iloc[0]
        )

        impostos_dif_a = base.balanco["ativo_nao_corrente"][
            "Impostos_Diferidos_Ativos"
        ]

        total_anc = aft + outros_anc + impostos_dif_a

        inv_st = float(df_inv_st[df_inv_st.ano == y]["inventarios"].iloc[0])
        cli = float(df_cli[df_cli.ano == y]["saldo_clientes"].iloc[0])
        eoep_d = float(df_eoep[df_eoep.ano == y]["eoep_devedor"].iloc[0])
        out_ac = out_ac_yr[y]

        rl_y = float(df_dr[df_dr.ano == y]["rl"].iloc[0])

        cp_total_pre_caixa = (
            capital_social
            + premios
            + outros_ic
            + reservas
            + ajust_af
            + rt[y]
            + outras_var
            + rl_y
        )

        emp_nc = float(df_fin[df_fin.ano == y]["emprestimos_NC"].iloc[0])
        emp_c = float(df_fin[df_fin.ano == y]["emprestimos_C"].iloc[0])

        imp_dif_p = base.balanco["passivo"]["Impostos_Diferidos_Passivos"]

        forn = float(df_forn[df_forn.ano == y]["fornecedores"].iloc[0])
        eoep_c = float(df_eoep[df_eoep.ano == y]["eoep_credor"].iloc[0])
        out_pc = outros_pc_yr[y]

        passivo_pre = emp_nc + emp_c + imp_dif_p + forn + eoep_c + out_pc
        ac_sem_caixa = inv_st + cli + eoep_d + out_ac

        surplus = cp_total_pre_caixa + passivo_pre - total_anc - ac_sem_caixa

        if y == 2024:
            caixa = base.balanco["ativo_corrente"]["Caixa"]
            aplic_cp = 0.0
            linha_cp = 0.0
        else:
            caixa = min(caixa_max, max(caixa_min, surplus))
            aplic_cp = max(0.0, surplus - caixa_max)
            linha_cp = max(0.0, caixa_min - surplus)

        total_ac = aplic_cp + inv_st + cli + eoep_d + out_ac + caixa
        passivo_total = passivo_pre + linha_cp
        cp_total = cp_total_pre_caixa
        total_passivo_cp = cp_total + passivo_total
        total_ativo = total_anc + total_ac

        rows.append(
            {
                "ano": y,
                "aft_liquido": aft,
                "goodwill_intang_subs_af": outros_anc,
                "impostos_dif_ativos": impostos_dif_a,
                "total_anc": total_anc,
                "aplicacoes_fin_cp": aplic_cp,
                "inventarios": inv_st,
                "clientes": cli,
                "eoep_devedor": eoep_d,
                "outros_ac": out_ac,
                "caixa": caixa,
                "total_ac": total_ac,
                "total_ativo": total_ativo,
                "capital_social": capital_social,
                "premios_emissao": premios,
                "outros_ic_proprio": outros_ic,
                "reservas_legais": reservas,
                "ajust_af": ajust_af,
                "resultados_transitados": rt[y],
                "outras_var_cp": outras_var,
                "rl": rl_y,
                "total_cp": cp_total,
                "emprestimos_nc": emp_nc,
                "emprestimos_c": emp_c,
                "imp_dif_passivos": imp_dif_p,
                "fornecedores": forn,
                "eoep_credor": eoep_c,
                "outros_pc": out_pc,
                "linha_credito_cp": linha_cp,
                "total_passivo": passivo_total,
                "total_cp_passivo": total_passivo_cp,
                "controlo": total_passivo_cp - total_ativo,
            }
        )

    return pd.DataFrame(rows)