"""
Módulo: engine/analitica/kpis.py — KPIs Financeiros (Indicadores de Desempenho)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula um painel de Indicadores-Chave de Desempenho (KPIs) financeiros que permite
avaliação rápida da saúde financeira da empresa sem necessidade de ler demonstrações completas.

KPIs SÃO MÉTRICAS AGREGADAS CRÍTICAS:
  - Resumem informação de páginas de demonstrações em números-chave
  - Permitem comparação inter-anual (Ano 1 vs Ano 2)
  - Permitem benchmarking (empresa vs. indústria)
  - Guiam decisões de gestão e investimento

┌─────────────────────────────────────────────────────────────────┐
│ CATEGORIAS DE KPIs                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. KPIs DE RENTABILIDADE (Lucro ÷ Receita ou Ativo)           │
│    - Margem de EBITDA: EBITDA / VN × 100%                     │
│      Interpreta: lucro operacional antes de depr./juros        │
│      Benchmark: 15-25% para indústria (varia muito)            │
│                                                                 │
│    - Margem de EBIT: EBIT / VN × 100%                         │
│      Interpreta: lucro operacional após depreciação            │
│      Benchmark: 10-20% (produto de EBITDA - depr./VN)         │
│                                                                 │
│    - Margem Líquida: Resultado Líquido / VN × 100%            │
│      Interpreta: lucro final disponível para acionistas        │
│      Benchmark: 5-15% (após juros e impostos)                  │
│                                                                 │
│    - ROE (Return on Equity): Resultado Líquido / Patrimônio    │
│      Interpreta: rentabilidade do capital do acionista         │
│      Benchmark: >15% (bom), 10-15% (aceitável), <10% (fraco)  │
│                                                                 │
│    - ROA (Return on Assets): Resultado Líquido / Ativo Total   │
│      Interpreta: eficiência na utilização dos ativos           │
│      Benchmark: 5-10% (varia muito por setor)                  │
│                                                                 │
│    - ROIC (Return on Invested Capital): EBIT(1-IR) / Capital   │
│      Interpreta: retorno do capital total investido            │
│      Benchmark: >10% (positivo para valor)                     │
│                                                                 │
│ 2. KPIs DE LIQUIDEZ (Caixa vs. Obrigações Curto Prazo)        │
│    - Current Ratio: Ativo Corrente / Passivo Corrente          │
│      Interpreta: capacidade de pagar contas curto prazo        │
│      Benchmark: 1.0-2.0 (abaixo 1 = perigo)                   │
│                                                                 │
│    - Liquidez Imediata: Caixa / Passivo Corrente               │
│      Interpreta: capacidade de pagar HOJE (sem vender ativos)  │
│      Benchmark: >0.5 (conservador)                             │
│                                                                 │
│ 3. KPIs DE SOLVÊNCIA (Dívida vs. Patrimônio)                  │
│    - Debt-to-Equity: Dívida Total / Patrimônio                 │
│      Interpreta: alavancagem (quanto dinheiro emprestado)      │
│      Benchmark: <1.5 (conservador <1.0, agressivo >2.0)       │
│                                                                 │
│    - Debt-to-EBITDA: Dívida / EBITDA                           │
│      Interpreta: quantos anos até pagar dívida com lucro       │
│      Benchmark: <3 anos (capacidade de reembolso)              │
│                                                                 │
│    - Cobertura de Juros: EBIT / Juros                          │
│      Interpreta: quantas vezes o lucro cobre a carga juro      │
│      Benchmark: >5 (excelente), 3-5 (bom), <2 (risco)         │
│                                                                 │
│ 4. KPIs DE EFICIÊNCIA (Ciclo de Caixa)                         │
│    - Ciclo de Caixa: PMR + DMI - PMP (dias)                    │
│      Interpreta: dias de capital circulante necessário         │
│      Benchmark: <60 dias (bom), 60-90 (aceitável), >90 (risco)│
│      Fórmula: (Clientes + Inventário - Fornecedores) em dias   │
│                                                                 │
│    - Rotação de Ativo: VN / Ativo Total (vezes/ano)           │
│      Interpreta: eficiência de geração de receita com ativos   │
│      Benchmark: >1.5 (boa utilização de ativos)                │
│                                                                 │
│ 5. KPIs DE CRESCIMENTO (Evolução Ano a Ano)                   │
│    - Crescimento de Receita: (VN_ano2 / VN_ano1 - 1) × 100%   │
│      Interpreta: expansão do negócio                           │
│      Benchmark: 3-10% (sustentável)                            │
│                                                                 │
│    - Crescimento de EBITDA: (EBITDA_ano2 / EBITDA_ano1 - 1)   │
│      Interpreta: expansão de lucro operacional                 │
│      Benchmark: > Crescimento Receita (melhor margem)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

UTILIDADE PRÁTICA:
  - Gestão: monitorar mensalmente para alertas rápidos
  - Bancos: para decisões de crédito (capacidade de reembolso)
  - Acionistas: para avaliar retorno do investimento
  - Investidores: para comparar empresas dentro do setor
  - Reguladores: para monitorar riscos sistémicos

LIMITAÇÕES:
  - KPIs são "retratos" (histórico) não "previsões" (futuro)
  - Não capturam qualidade de gestão (governança)
  - Podem ser manipulados ("creative accounting")
  - Requerem contexto de indústria para interpretação
  - Mudanças contabilísticas afetam comparabilidade
"""

from __future__ import annotations

import pandas as pd

from ..inputs import ALL_YEARS, YEARS
from ..demonstracoes.nfm import ciclo_caixa_dias


def _effective_tax_rate(dr_row: pd.Series) -> float:
    """Calcula taxa efetiva de IRC a partir da DR.

    A versão anterior usava 0.20 hardcoded no ROIC.
    Aqui usamos a própria DR:
        taxa efetiva = IRC / RAI

    Nota:
        Na DR, o IRC está normalmente com sinal negativo.
        Por isso usamos abs(irc).
    """
    rai = float(dr_row.get("rai", 0.0))
    irc = float(dr_row.get("irc", 0.0))

    if rai <= 0:
        return 0.0

    taxa = abs(irc) / rai

    # Proteção contra valores anómalos.
    return max(0.0, min(taxa, 1.0))


def build_kpis(
    df_dr: pd.DataFrame,
    df_balanco: pd.DataFrame,
    df_dfc: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula KPIs financeiros a partir da DR, Balanço e DFC."""
    rows = []

    # Mantido por compatibilidade: df_dfc pode ser usado futuramente para KPIs de cash-flow.
    _ = df_dfc

    for y in ALL_YEARS:
        dr = df_dr[df_dr.ano == y].iloc[0]
        bs = df_balanco[df_balanco.ano == y].iloc[0]

        vn = float(dr["vn"])

        ebitda = float(dr["ebitda"])
        ebit = float(dr["ebit"])
        rl = float(dr["rl"])

        margem_ebitda = ebitda / vn if vn else 0.0
        margem_ebit = ebit / vn if vn else 0.0
        margem_rl = rl / vn if vn else 0.0

        if y > 2024:
            dr_prev = df_dr[df_dr.ano == (y - 1)].iloc[0]
            vn_prev = float(dr_prev["vn"])
            cresc_vn = (vn / vn_prev - 1) if vn_prev else 0.0
        else:
            cresc_vn = 0.0

        ativo_corrente = float(bs["total_ac"])
        passivo = float(bs["total_passivo"])
        cp = float(bs["total_cp"])
        ativo = float(bs["total_ativo"])
        emprestimos_nc = float(bs["emprestimos_nc"])
        emprestimos_c = float(bs["emprestimos_c"])
        caixa = float(bs.get("caixa", 0.0))

        passivo_corrente = (
            float(bs["fornecedores"])
            + float(bs["eoep_credor"])
            + float(bs["outros_pc"])
            + float(bs["emprestimos_c"])
            + float(bs.get("linha_credito_cp", 0.0))
        )

        liquidez_geral = (
            ativo_corrente / passivo_corrente
            if passivo_corrente
            else 0.0
        )

        liquidez_reduzida = (
            (ativo_corrente - float(bs["inventarios"])) / passivo_corrente
            if passivo_corrente
            else 0.0
        )

        autonomia = cp / ativo if ativo else 0.0
        solvabilidade = cp / passivo if passivo else 0.0
        endividamento = passivo / ativo if ativo else 0.0
        debt_equity = passivo / cp if cp else 0.0

        divida_financeira = emprestimos_nc + emprestimos_c
        divida_liquida = divida_financeira - caixa

        nd_ebitda = divida_liquida / ebitda if ebitda else 0.0
        debt_ebitda = nd_ebitda

        roa = rl / ativo if ativo else 0.0
        roe = rl / cp if cp else 0.0
        roce = ebit / (cp + divida_financeira) if (cp + divida_financeira) else 0.0

        capital_investido = cp + divida_financeira
        taxa_irc_efetiva = _effective_tax_rate(dr)

        roic = (
            float(dr["ebit"]) * (1 - taxa_irc_efetiva) / capital_investido
            if capital_investido
            else 0.0
        )

        pmr, dmi, pmp, ciclo_caixa = ciclo_caixa_dias(
            float(bs["clientes"]),
            float(bs["inventarios"]),
            float(bs["fornecedores"]),
            vn,
            float(dr["cmvmc"]),
            float(dr["fse"]),
            0.0,
            0.0,
        )

        juros_abs = abs(float(dr["juros"]))

        cob_juros = ebit / juros_abs if juros_abs else 0.0

        rows.append(
            {
                "ano": y,
                "vn": vn,
                "ebitda": ebitda,
                "ebit": ebit,
                "rl": rl,
                "cmvmc": float(dr["cmvmc"]),
                "fse": float(dr["fse"]),
                "gastos_pessoal": float(dr["gastos_pessoal"]),
                "ebitda_margin": margem_ebitda,
                "ebit_margin": margem_ebit,
                "rl_margin": margem_rl,
                "margem_ebitda": margem_ebitda,
                "margem_ebit": margem_ebit,
                "margem_rl": margem_rl,
                "cresc_vn": cresc_vn,
                "liquidez_geral": liquidez_geral,
                "liquidez_reduzida": liquidez_reduzida,
                "current_ratio": liquidez_geral,
                "autonomia_financeira": autonomia,
                "solvabilidade": solvabilidade,
                "endividamento": endividamento,
                "debt_equity": debt_equity,
                "debt_ebitda": debt_ebitda,
                "nd_ebitda": nd_ebitda,
                "emprestimos_nc": emprestimos_nc,
                "emprestimos_c": emprestimos_c,
                "caixa": caixa,
                "divida_liquida": divida_liquida,
                "total_ativo": ativo,
                "cp": cp,
                "roa": roa,
                "roe": roe,
                "roce": roce,
                "ROA": roa,
                "ROE": roe,
                "ROIC": roic,
                "taxa_irc_efetiva": taxa_irc_efetiva,
                "PMR": pmr,
                "PMP": pmp,
                "DMI": dmi,
                "ciclo_caixa": ciclo_caixa,
                "cobertura_juros": cob_juros,
            }
        )

    return pd.DataFrame(rows)


def gas_por_peca_anual(a, base) -> pd.DataFrame:
    """Projeta consumo de gás natural por peça produzida 2024-2029."""
    esg = base.raw.get("esg_2024", {})

    gas_base = esg.get("gas_natural_kwh", 0)
    pecas_base = esg.get("producao_total_pecas", 0)

    gpeca_base = esg.get(
        "gas_por_peca_kwh",
        gas_base / pecas_base if pecas_base else 0,
    )

    esg_a = a.raw.get("esg", {})
    cresc_pecas = esg_a.get("crescimento_producao_pecas", {})
    efic_gas = esg_a.get("eficiencia_gas_anual", {})

    rows = [
        {
            "ano": 2024,
            "gas_kwh_total": gas_base,
            "producao_pecas": pecas_base,
            "gas_por_peca_kwh": gpeca_base,
            "var_vs_2024": 0.0,
        }
    ]

    prev_pecas = pecas_base
    prev_gpeca = gpeca_base

    for y in YEARS:
        prev_pecas = prev_pecas * (1 + cresc_pecas.get(y, 0.03))
        prev_gpeca = prev_gpeca * (1 + efic_gas.get(y, 0.0))

        gas_total = prev_pecas * prev_gpeca
        var = (prev_gpeca / gpeca_base - 1) if gpeca_base else 0.0

        rows.append(
            {
                "ano": y,
                "gas_kwh_total": gas_total,
                "producao_pecas": prev_pecas,
                "gas_por_peca_kwh": prev_gpeca,
                "var_vs_2024": var,
            }
        )

    return pd.DataFrame(rows)
