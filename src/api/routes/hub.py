"""Rotas do hub logistico."""

from fastapi import APIRouter, Query

from src.engine.projetos.hub_logistico import (
    load as hub_load,
    tornado_hub,
    viabilidade_hub,
    mapa_servico_divida,
    hub_capex,
    hub_nfm,
)

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
            "low": round((r["vpl_low"] - r["vpl_base"]) / 1e6, 2),
            "high": round((r["vpl_high"] - r["vpl_base"]) / 1e6, 2),
        }
        for r in df.to_dict(orient="records")
    ]
    return {"rows": rows}


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
