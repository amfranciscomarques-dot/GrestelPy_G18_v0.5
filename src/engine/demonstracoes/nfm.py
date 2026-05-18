"""NFM — Necessidades de Fundo de Maneio (Working Capital Needs).

Mapa funcional exigido pelo manual da UC PEF 2025-26.

Definição:
  NFM = Ativo Cíclico - Passivo Cíclico
      = (Clientes + Inventários + EOEP devedor + Outros AC cíclicos)
        - (Fornecedores + EOEP credor + Outros PC cíclicos)

Interpretação:
  NFM > 0 → a empresa necessita de financiamento para cobrir o ciclo operacional
  NFM < 0 → o ciclo operacional é autofinanciado pelos fornecedores e Estado

Variação de NFM (ΔNFM):
  ΔNFM > 0 → absorve caixa (necessidade crescente de capital de giro)
  ΔNFM < 0 → liberta caixa (capital de giro diminui)

Rácios de referência (dias de ciclo operacional):
  PMR  = Clientes / (VN × (1+IVA)) × 365   — prazo médio de recebimento
  DMI  = Inventários / CMVMC × 365          — duração média de inventário
  PMP  = Fornecedores / (Compras × (1+IVA)) × 365 — prazo médio de pagamento
  Ciclo_Caixa = PMR + DMI - PMP
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, ALL_YEARS
from ..operacional.clientes import iva_efetivo_vendas


def ciclo_caixa_dias(
    clientes: float,
    inventarios: float,
    fornecedores: float,
    vn: float,
    cmvmc: float,
    fse: float,
    iva_venda: float,
    iva_compra: float,
) -> tuple[float, float, float, float]:
    """Calcula PMR, DMI, PMP e ciclo de caixa em dias.

    O helper é partilhado entre NFM e KPIs para evitar duplicação da fórmula.
    """
    compras = abs(cmvmc) + abs(fse)

    pmr = clientes / (vn * (1 + iva_venda)) * 365 if vn > 0 else 0.0
    dmi = inventarios / abs(cmvmc) * 365 if cmvmc else 0.0
    pmp = fornecedores / (compras * (1 + iva_compra)) * 365 if compras > 0 else 0.0
    ciclo_caixa = pmr + dmi - pmp

    return pmr, dmi, pmp, ciclo_caixa


def nfm_anual(
    a: Assumptions,
    base: Base2024,
    df_balanco: pd.DataFrame,
    df_dr: pd.DataFrame,
) -> pd.DataFrame:
    """Mapa de NFM anual 2024-2029.

    Usa saldos do Balanço e rubricas da DR para calcular NFM e rácios.

    Args:
        a: Pressupostos carregados via inputs.py.
        base: Dados base 2024 carregados via inputs.py.
        df_balanco: output de build_balanco().
        df_dr: output de build_dr().

    Returns:
        DataFrame com colunas:
        ano, clientes, inventarios, eoep_devedor, outros_ac_ciclico,
        ativo_ciclico, fornecedores, eoep_credor, outros_pc_ciclico,
        passivo_ciclico, nfm, variacao_nfm,
        pmr_dias, dmi_dias, pmp_dias, ciclo_caixa_dias.
    """
    iva_venda = iva_efetivo_vendas(a)
    iva_compra = a.impostos.get("IVA_FSE", 0.15)

    rows = []
    nfm_anterior = None

    for y in ALL_YEARS:
        b = df_balanco[df_balanco.ano == y].iloc[0]
        d = df_dr[df_dr.ano == y].iloc[0]

        # Ativo cíclico operacional — excluindo caixa e aplicações financeiras
        cli = float(b["clientes"])
        inv = float(b["inventarios"])
        eoep_dev = float(b["eoep_devedor"])

        # Outros AC cíclico: Outros_AC menos aplicações financeiras CP
        outros_ac = float(b.get("outros_ac", 0.0))
        ativo_ciclico = cli + inv + eoep_dev + outros_ac

        # Passivo cíclico operacional — excluindo dívida financeira
        forn = float(b["fornecedores"])
        eoep_cred = float(b["eoep_credor"])
        outros_pc = float(b.get("outros_pc", 0.0))
        passivo_ciclico = forn + eoep_cred + outros_pc

        nfm = ativo_ciclico - passivo_ciclico
        variacao_nfm = nfm - nfm_anterior if nfm_anterior is not None else 0.0
        nfm_anterior = nfm

        # Rácios em dias
        vn = float(d["vn"])
        cmvmc = float(d["cmvmc"])
        fse_val = float(d["fse"])

        pmr, dmi, pmp, ciclo_caixa = ciclo_caixa_dias(
            cli,
            inv,
            forn,
            vn,
            cmvmc,
            fse_val,
            iva_venda,
            iva_compra,
        )

        rows.append(
            {
                "ano": y,
                "clientes": cli,
                "inventarios": inv,
                "eoep_devedor": eoep_dev,
                "outros_ac_ciclico": outros_ac,
                "ativo_ciclico": ativo_ciclico,
                "fornecedores": forn,
                "eoep_credor": eoep_cred,
                "outros_pc_ciclico": outros_pc,
                "passivo_ciclico": passivo_ciclico,
                "nfm": nfm,
                "variacao_nfm": variacao_nfm,
                "pmr_dias": round(pmr, 1),
                "dmi_dias": round(dmi, 1),
                "pmp_dias": round(pmp, 1),
                "ciclo_caixa_dias": round(ciclo_caixa, 1),
            }
        )

    return pd.DataFrame(rows)
