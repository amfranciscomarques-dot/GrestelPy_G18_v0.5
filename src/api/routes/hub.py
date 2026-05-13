"""Rotas do hub log?stico."""

from fastapi import APIRouter, Query

from src.engine.projetos.hub_logistico import load as hub_load, tornado_hub, viabilidade_hub

router = APIRouter(prefix="/api")


@router.get("/hub/viability")
def get_hub_viability(irc_taxa: float = Query(0.225)):
    hub = hub_load()
    res = viabilidade_hub(hub, irc_taxa=irc_taxa)

    return {
        "vpl": res.get("vpl"),
        "tir": res.get("tir"),
        "payback_simples": res.get("payback_simples"),
        "payback_atualizado": res.get("payback_atualizado"),
        "valor_terminal": res.get("valor_terminal"),
        "fcf": [float(v) for v in res.get("fcf_df", {}).get("fcf_livre", [])]
        if hasattr(res.get("fcf_df"), "get") else [],
        "parametros": res.get("parametros", {}),
    }


@router.get("/hub/tornado")
def get_hub_tornado(irc_taxa: float = Query(0.225)):
    df = tornado_hub(irc_taxa=irc_taxa)
    return {"rows": df.to_dict(orient="records")}
