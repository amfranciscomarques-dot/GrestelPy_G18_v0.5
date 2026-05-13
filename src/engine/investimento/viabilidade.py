"""Viabilidade do Projeto M6 — Costa Nova Logistics Hub 4.0.

NPV, TIR, Payback simples e atualizado, análise de sensibilidade.

Perspetiva: FCF unlevered (antes de financiamento) — WACC 6,41%

FCF = NOPAT + Dep - CAPEX - ΔNFM
    = [EBIT × (1-t)] + Dep - CAPEX + InventárioLibertado

EBIT Hub = Benefício Operacional Líquido (810K base) + Subsídio PT2030 (192.5K) - Dep (550K)

Referência M6:
  Payback simples Base:   6,79 anos (sem ajuste inventário)
  Payback ajustado:       5,31 anos = (5.5M - 1.2M) / 0.81M
  WACC: 6,41% | Ke: 12,33% | Kd líquido: 2,22%
"""

from __future__ import annotations

from ..projetos import hub_logistico as hub_mod


# Re-exportar as funções principais do hub_logistico para compatibilidade.
viabilidade_hub = hub_mod.viabilidade_hub
sensibilidade_hub = hub_mod.sensibilidade_hub
tornado_hub = hub_mod.tornado_hub
hub_fcf = hub_mod.hub_fcf
hub_dr_impact = hub_mod.hub_dr_impact
hub_capex = hub_mod.hub_capex
hub_financing = hub_mod.hub_financing


def load_hub() -> dict:
    """Carrega pressupostos do Hub Logístico."""
    return hub_mod.load()


def resumo_viabilidade(
    hub: dict | None = None,
    irc_taxa: float = 0.225,
    wacc: float | None = None,
) -> dict:
    """Resumo executivo da viabilidade do Hub Logístico.

    Returns:
        dict com métricas formatadas para dashboard e relatório:
        vpl_str          — VPL formatado (€)
        tir_str          — TIR formatada (%)
        payback_str      — Payback simples (anos)
        payback_adj_str  — Payback atualizado (anos)
        critica          — avaliação qualitativa
        + todos os campos de viabilidade_hub().
    """
    if hub is None:
        hub = load_hub()

    res = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc)

    vpl = res["vpl"]
    tir = res["tir"]
    pb = res["payback_simples"]
    pb_disc = res["payback_atualizado"]

    wacc_used = res["parametros"]["wacc"]

    # Avaliação qualitativa
    if vpl is not None and vpl > 0 and tir is not None and tir > wacc_used:
        critica = "VIÁVEL — VPL positivo e TIR superior ao WACC"
    elif vpl is not None and vpl > 0:
        critica = "MARGINALMENTE VIÁVEL — VPL positivo mas TIR próxima do WACC"
    else:
        critica = "NÃO VIÁVEL — VPL negativo"

    res["vpl_str"] = f"{vpl:,.0f} €" if vpl is not None else "n/d"
    res["tir_str"] = f"{tir:.2%}" if tir is not None else "n/d"
    res["payback_str"] = f"{pb:.2f} anos" if pb is not None else "n/d"
    res["payback_adj_str"] = f"{pb_disc:.2f} anos" if pb_disc is not None else "n/d"
    res["critica"] = critica

    return res