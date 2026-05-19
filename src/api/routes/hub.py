"""Rotas do hub logistico."""

from fastapi import APIRouter, Query

from src.engine.projetos.hub_logistico import (
    load as hub_load,
    tornado_hub,
    viabilidade_hub,
    ponto_critico_hub,
    mapa_servico_divida,
    hub_capex,
    hub_nfm,
)
from src.engine.projetos.monte_carlo_hub import monte_carlo_hub
from src.engine.projetos.ecogres import ecogres_dr, load as eco_load
from src.engine.modelo.model import dataframe_to_records, run_model
from src.api.serializers import _wrap_rows

router = APIRouter(prefix="/api")


@router.get("/hub/viability")
def get_hub_viability(irc_taxa: float = Query(None), wacc: float = Query(None)):
    hub = hub_load()
    res = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc)

    return {
        "vpl": res.get("vpl"),
        "tir": res.get("tir"),
        "payback_simples": res.get("payback_simples"),
        "payback_atualizado": res.get("payback_atualizado"),
        "indice_rendibilidade": res.get("indice_rendibilidade"),
        "valor_terminal": res.get("valor_terminal"),
        "valor_residual_ativos": res.get("valor_residual_ativos"),
        "nfm_recovery_terminal": res.get("nfm_recovery_terminal"),
        "capital_vivo_t10": res.get("capital_vivo_t10"),
        "mais_valia": res.get("mais_valia"),
        "imposto_mais_valia": res.get("imposto_mais_valia"),
        "fcf": [float(v) for v in res.get("fcf_df", {}).get("fcf_livre", [])]
        if hasattr(res.get("fcf_df"), "get") else [],
        "parametros": res.get("parametros", {}),
    }


@router.get("/hub/tornado")
def get_hub_tornado(irc_taxa: float = Query(0.245)):
    df = tornado_hub(irc_taxa=irc_taxa)
    rows = [
        {
            "variavel": r["label"],
            "driver": r["driver"],
            "desc_low": r.get("desc_low", ""),
            "desc_high": r.get("desc_high", ""),
            "low": round((r["vpl_low"] - r["vpl_base"]) / 1e6, 3),
            "high": round((r["vpl_high"] - r["vpl_base"]) / 1e6, 3),
            "vpl_base": round(r["vpl_base"] / 1e6, 3),
            "vpl_low_abs": round(r["vpl_low"] / 1e6, 3),
            "vpl_high_abs": round(r["vpl_high"] / 1e6, 3),
            "impacto_total": round(r["impacto_total"] / 1e6, 3),
        }
        for r in df.to_dict(orient="records")
    ]
    return {"rows": rows, "vpl_base": round(df["vpl_base"].iloc[0] / 1e6, 3) if len(df) else 0}


@router.get("/hub/break-even")
def get_hub_break_even(
    irc_taxa: float = Query(0.245),
    drivers: str = Query("pessoal,inventario,capex,wacc,b2c,crescimento,pt2030_taxa"),
):
    """Ponto crítico por driver: valor que faz VPL = 0."""
    hub = hub_load()
    driver_list = [d.strip() for d in drivers.split(",")]
    results = []
    for drv in driver_list:
        try:
            pc = ponto_critico_hub(drv, hub, irc_taxa)
            results.append(pc)
        except Exception as exc:
            results.append({"driver": drv, "ponto_critico": None, "status": str(exc)})
    return {"break_even": results}


@router.get("/hub/debt-service")
def get_hub_debt_service():
    hub = hub_load()
    df = mapa_servico_divida(hub)
    return {"rows": df.to_dict(orient="records")}


@router.get("/hub/investment-map")
def get_hub_investment_map():
    hub = hub_load()
    proj = hub["projeto_hub"]

    # CAPEX por pool de ativo
    pools = proj["capex"]["pools"]
    capex_rows = []
    for nome, pool in pools.items():
        capex_rows.append({
            "pool": nome,
            "descricao": pool.get("descricao", nome),
            "montante": float(pool["montante"]),
            "ano_inicio": int(pool["ano_inicio"]),
            "taxa_depreciacao": float(pool["taxa_depreciacao"]),
            "vida_util_anos": int(pool["vida_util_anos"]),
        })

    # Cronograma CAPEX por ano
    cron = proj["capex"]["cronograma"]
    capex_anual = [{"ano": int(y), "capex": float(v)} for y, v in cron.items()]

    # NFM por ano
    nfm_map = hub_nfm(hub)
    nfm_rows = [{"ano": y, "delta_nfm": v} for y, v in sorted(nfm_map.items())]

    # PT2030
    pt = proj["financiamento"]["PT2030"]

    return {
        "capex_base": float(proj["capex"]["base"]),
        "pools": capex_rows,
        "capex_anual": capex_anual,
        "nfm": nfm_rows,
        "pt2030_montante": float(pt["montante"]),
        "pt2030_ano": int(pt["ano_recebimento"]),
    }


@router.get("/hub/comparativo")
def get_hub_comparativo(
    cenario: str = Query("Base"),
    ecogres_on: bool = Query(True),
):
    """DR/Balanço/DFC e KPIs comparativos: Grestel sem-Hub vs. com-Hub."""
    dfs_sem = run_model(cenario=cenario, hub_on=False, ecogres_on=ecogres_on)
    dfs_com = run_model(cenario=cenario, hub_on=True, ecogres_on=ecogres_on)
    rec_sem = dataframe_to_records(dfs_sem)
    rec_com = dataframe_to_records(dfs_com)
    return {
        "cenario": cenario,
        "sem_hub": {
            "dr":     _wrap_rows(rec_sem.get("dr")),
            "balanco": _wrap_rows(rec_sem.get("balanco")),
            "dfc":    _wrap_rows(rec_sem.get("dfc")),
            "kpis":   _wrap_rows(rec_sem.get("kpis")),
        },
        "com_hub": {
            "dr":     _wrap_rows(rec_com.get("dr")),
            "balanco": _wrap_rows(rec_com.get("balanco")),
            "dfc":    _wrap_rows(rec_com.get("dfc")),
            "kpis":   _wrap_rows(rec_com.get("kpis")),
        },
    }


@router.get("/hub/monte-carlo")
def get_hub_monte_carlo(
    n: int = Query(1000, ge=100, le=5000, description="Número de simulações (100–5 000)"),
    irc_taxa: float = Query(0.245, description="Taxa combinada de IRC (Derrama incluída)"),
    seed: int = Query(None, description="Seed para reprodutibilidade (omitir = aleatório)"),
):
    """Monte Carlo da viabilidade do Hub Logístico 4.0.

    Corre N simulações amostrando 6 drivers de risco de distribuições contínuas
    (triangulares e normal truncada) e retorna:
    - Distribuição do VAL e TIR (percentis P5–P95)
    - P(VAL > 0): probabilidade de viabilidade do projeto
    - P(TIR > WACC_base): probabilidade de excesso de retorno
    - Correlações de Pearson driver → VAL (ranking de importância dos riscos)
    - Histograma do VAL (40 bins) para visualização
    """
    hub = hub_load()
    return monte_carlo_hub(hub=hub, n_simulations=n, irc_taxa=irc_taxa, seed=seed)


@router.get("/hub/consolidado")
def get_hub_consolidado(
    cenario: str = Query("Base"),
    irc_taxa: float = Query(None),
    wacc: float = Query(None),
):
    """VAL, TIR, Payback consolidados — Hub Logístico + Ecogres + Grestel grupo."""
    hub = hub_load()
    hub_res = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc)

    # Ecogres — P&L projetado (com hub ativo para capturar transferência interna)
    eco = eco_load()
    df_eco = ecogres_dr(eco, hub_ativo=True)
    eco_records = df_eco.to_dict(orient="records")
    eco_anos = [int(r["ano"]) for r in eco_records]
    eco_rl = [float(r["rl"]) for r in eco_records]
    eco_ebitda = [float(r["ebitda"]) for r in eco_records]
    eco_receita = [float(r["receita_total"]) for r in eco_records]
    # Excluir 2024 (histórico) para somas prospetivas
    eco_rl_proj = sum(eco_rl[1:])
    eco_ebitda_2029 = eco_ebitda[-1] if eco_ebitda else 0.0

    # Grestel grupo — DR sem e com hub para calcular impacto incremental
    dfs_sem = run_model(cenario=cenario, hub_on=False, ecogres_on=True)
    dfs_com = run_model(cenario=cenario, hub_on=True, ecogres_on=True)
    rec_sem = dataframe_to_records(dfs_sem)
    rec_com = dataframe_to_records(dfs_com)

    dr_sem = rec_sem.get("dr", [])
    dr_com = rec_com.get("dr", [])
    kpis_sem = rec_sem.get("kpis", [])
    kpis_com = rec_com.get("kpis", [])

    # Impacto incremental hub no grupo (delta EBITDA e RL)
    def _pick(rows, field, default=0.0):
        return [float(r.get(field, default)) for r in rows]

    ebitda_sem = _pick(dr_sem, "ebitda")
    ebitda_com = _pick(dr_com, "ebitda")
    rl_sem     = _pick(dr_sem, "rl")
    rl_com     = _pick(dr_com, "rl")
    anos_dr    = [int(r.get("ano", 0)) for r in dr_com]

    delta_ebitda = [c - s for c, s in zip(ebitda_com, ebitda_sem)]
    delta_rl     = [c - s for c, s in zip(rl_com, rl_sem)]

    return {
        "hub": {
            "vpl": hub_res["vpl"],
            "tir": hub_res["tir"],
            "payback_simples": hub_res["payback_simples"],
            "payback_atualizado": hub_res["payback_atualizado"],
            "indice_rendibilidade": hub_res["indice_rendibilidade"],
            "capex_base": hub_res["parametros"]["capex_base"],
            "wacc": hub_res["parametros"]["wacc"],
            "valor_terminal": hub_res["valor_terminal"],
            "valor_residual_ativos": hub_res.get("valor_residual_ativos"),
            "nfm_recovery_terminal": hub_res.get("nfm_recovery_terminal"),
            "pt2030_montante": hub_res["parametros"]["pt2030_montante"],
        },
        "ecogres": {
            "anos": eco_anos,
            "rl_anual": eco_rl,
            "ebitda_anual": eco_ebitda,
            "receita_anual": eco_receita,
            "rl_acumulado_projetado": eco_rl_proj,
            "ebitda_2029": eco_ebitda_2029,
        },
        "grupo": {
            "anos": anos_dr,
            "ebitda_sem_hub": ebitda_sem,
            "ebitda_com_hub": ebitda_com,
            "rl_sem_hub": rl_sem,
            "rl_com_hub": rl_com,
            "delta_ebitda_hub": delta_ebitda,
            "delta_rl_hub": delta_rl,
            "dr_sem_hub": _wrap_rows(dr_sem),
            "dr_com_hub": _wrap_rows(dr_com),
            "kpis_sem_hub": _wrap_rows(kpis_sem),
            "kpis_com_hub": _wrap_rows(kpis_com),
        },
    }
