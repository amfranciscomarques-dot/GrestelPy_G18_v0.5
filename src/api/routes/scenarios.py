"""Rotas para execu??o e compara??o de cen?rios."""

from fastapi import APIRouter, Query

from src.api.schemas import RunRequest
from src.api.serializers import _fse_mensal_to_rows, _wrap_rows
from src.engine.inputs import upsert_custom_scenario
from src.engine.inputs.loader import CENARIOS
from src.engine.modelo.model import dataframe_to_records, run_model

router = APIRouter(prefix="/api")


@router.get("/scenarios/all")
def get_scenarios_all(
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(False),
):
    """Corre todos os cen?rios e devolve DR/Balan?o/DFC/KPIs + detalhe FSE."""
    result = {}

    for sc in CENARIOS:
        dfs = run_model(cenario=sc, hub_on=hub_on, ecogres_on=ecogres_on)
        rec = dataframe_to_records(dfs)

        fse_det_anual_rec = rec.get("fse_detalhe_anual", [])
        fse_det_mensal = dfs.get("fse_detalhe_mensal_2025", {})

        result[sc] = {
            "dr": _wrap_rows(rec.get("dr")),
            "balanco": _wrap_rows(rec.get("balanco")),
            "dfc": _wrap_rows(rec.get("dfc")),
            "kpis": _wrap_rows(rec.get("kpis")),
            "fse_detalhe_anual": _wrap_rows(fse_det_anual_rec) if fse_det_anual_rec else {"rows": []},
            "fse_detalhe_mensal_2025": {"rows": _fse_mensal_to_rows(fse_det_mensal)},
        }

    return result


@router.post("/run")
def post_run(body: RunRequest):
    overrides = body.assumptions or {}

    if overrides and body.persist:
        upsert_custom_scenario(body.cenario, {
            "label": body.cenario,
            "description": "Custom run",
            "overrides": overrides,
        })

    dfs = run_model(
        cenario=body.cenario,
        hub_on=body.hub_on,
        ecogres_on=body.ecogres_on,
        assumptions_overrides=overrides,
    )

    return {"status": "ok", "outputs": dataframe_to_records(dfs)}

