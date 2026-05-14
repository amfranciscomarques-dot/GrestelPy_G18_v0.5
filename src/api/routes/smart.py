"""Rota do tracker de objetivos SMART."""

from fastapi import APIRouter, Query

from src.engine.inputs import load
from src.engine.modelo import kpis as kpis_mod
from src.engine.modelo import smart as smart_mod
from src.engine.modelo.model import run_model

router = APIRouter(prefix="/api")


@router.get("/smart/tracker")
def get_smart_tracker(
    cenario: str = Query("Base"),
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(False),
):
    """Devolve o tracker SMART com status por objetivo e ano.

    Campos de resposta por linha:
        id, nome, categoria, descricao, ano, kpi_field,
        valor, alvo, operador, unidade, status, desvio_pct

    status: cumprido | em_risco | nao_cumprido
    """
    dfs = run_model(cenario=cenario, hub_on=hub_on, ecogres_on=ecogres_on)
    df_kpis = dfs["kpis"]

    a, base, _ = load(cenario=cenario)
    df_gas = kpis_mod.gas_por_peca_anual(a, base)

    df_tracker = smart_mod.build_smart_tracker(df_kpis, df_gas)
    return {"tracker": df_tracker.to_dict(orient="records")}
