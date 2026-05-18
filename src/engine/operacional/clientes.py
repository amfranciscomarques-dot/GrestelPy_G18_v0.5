"""
Módulo: engine/financas/clientes.py — Clientes / Contas a Receber (Crédito)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula o saldo de Clientes (Contas a Receber), que é o dinheiro que a empresa
ainda aguarda receber de clientes pelos produtos/serviços vendidos.

CONCEITO CONTABILÍSTICO:

  Clientes = Crédito Comercial Concedido aos Clientes

  Fluxo:
    1. Empresa vende produto (receita reconhecida na DR)
    2. Cliente não paga imediatamente (no crédito)
    3. Cliente pagará em dias/semanas futuras (30-60-90 dias)
    4. Até lá, a empresa tem "Clientes" (ativo no balanço)

┌─────────────────────────────────────────────────────────────────┐
│ CÁLCULO DO SALDO DE CLIENTES (Método PMR)                      │
│                                                                 │
│ Saldo = VN com IVA × PMR / 365                                │
│                                                                 │
│ Conceitos:                                                     │
│   PMR (Prazo Médio de Recebimento): dias até cobrar           │
│   IVA (Imposto sobre Valor Acrescentado): 23% (standard)      │
│   VN (Volume de Negócios): receita sem IVA                    │
│   VN com IVA: VN × (1 + 0,23)                                 │
│                                                                 │
│ EXEMPLO:                                                       │
│   VN Anual: €10.000.000                                       │
│   IVA: 23%                                                    │
│   VN com IVA: €10.000.000 × 1,23 = €12.300.000              │
│   PMR: 45 dias (cliente paga em média após 45 dias)          │
│   Saldo de Clientes: €12.300.000 × 45 / 365 = €1.520.548    │
│                                                                 │
│ Interpretação:                                                 │
│   - A qualquer momento, a empresa tem ~€1,5M em crédito        │
│   - Dinheiro que não recebeu ainda (futuro pagamento)          │
│   - Capital circulante imobilizado em crédito                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

IMPACTO NA GESTÃO FINANCEIRA:

  1. Capital Circulante (Working Capital):
     - Clientes + Inventário - Fornecedores = Ciclo de Caixa
     - Clientes altos = capital circulante alto = menos caixa livre
     - Reduzir PMR (cobrar mais rápido) = liberta caixa

  2. Fluxo de Caixa:
     - Variação de Clientes é ajustamento na DFC
     - Se clientes sobem: caixa desce (faturação não recebida)
     - Se clientes descem: caixa sobe (recuperação de dívidas)

  3. Análise de Cobrança:
     - Rotação de Clientes = Receita / Clientes Médio
       * Exemplo: €10M / €1.5M = 6,6× rotação/ano
       → Cliente paga ~55 dias (365 / 6,6)
     - Métrica de eficiência: menor PMR = melhor gestão

  4. Risco de Crédito:
     - Clientes altos + crescimento rápido = risco de insolvência
     - Clientes antigos/atrasados = imparidades (cobrado como perda)
     - PMR crescente = sinais de problemas de cobrança

DINÂMICA DO CRESCIMENTO:

  Se VN cresce, clientes crescem proporcionalmente:
    Ano 1: VN €10M → Clientes = (€10M × 1,23) × 45/365 = €1,52M
    Ano 2: VN €11M → Clientes = (€11M × 1,23) × 45/365 = €1,67M
           Variação: +€150K (investimento em crédito = caixa negativa)

  Se PMR reduz (cobrança mais rápida), clientes descem:
    Redução PMR de 45 para 40 dias → Clientes descem
    Libertação de Caixa ≈ VN × (5/365) = €169K (cash positivo)

EXEMPLO COMPLETO (Análise de Crédito):
  Saldo Clientes: €1.500.000
  PMR: 50 dias
  Imparidades: 0,5% × €1.500.000 = €7.500 (provisão para perda)
  Clientes Líquidos: €1.500.000 - €7.500 = €1.492.500

  Interpretação:
    - Crédito saudável (50 dias é razoável em B2B)
    - Risco estimado baixo (0,5% perda esperada)
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024


def iva_efetivo_vendas(a: Assumptions) -> float:
    """Taxa efectiva de IVA sobre vendas, ponderada pelo mix de mercados.

    Apenas o Mercado Interno PT aplica IVA à taxa normal (23%).
    Exportações para UE são isentas (RITI art. 14.º — transmissões intracom.).
    Exportações para fora da UE são isentas (CIVA art. 14.º n.º 1 al. a)).
    """
    iva = float(a.impostos.get("IVA_Vendas", 0.23))
    pct_pt = float(a.mercados.get("PT", {}).get("peso_global", 0.0))
    return pct_pt * iva


def clientes_anual(
    a: Assumptions,
    base: Base2024,
    vn_total: pd.DataFrame,
) -> pd.DataFrame:
    """Calcula o saldo anual de clientes via PMR.

    Fórmula:
        Saldo de clientes = VN com IVA efectivo × PMR / 365
        VN com IVA efectivo = VN × (1 + iva_efetivo_vendas)

    Onde iva_efetivo pondera pelo mix de mercados:
      • PT (mercado interno): IVA à taxa normal
      • UE / USA / ROW (exportações): IVA 0 %

    2024 usa o valor auditado do balanço de abertura.
    """
    pmr = float(a.prazos["PMR_dias"])
    iva = iva_efetivo_vendas(a)

    rows = []

    for _, r in vn_total.iterrows():
        ano = int(r["ano"])
        vn = float(r["vn_total"])
        vn_com_iva = vn * (1 + iva)

        if ano == 2024:
            saldo = float(base.balanco["ativo_corrente"]["Clientes"])
        else:
            saldo = vn_com_iva * pmr / 365

        rows.append(
            {
                "ano": ano,
                "vn_com_iva": vn_com_iva,
                "saldo_clientes": saldo,
            }
        )

    return pd.DataFrame(rows)