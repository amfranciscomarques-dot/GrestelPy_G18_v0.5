"""Rotas do rolling forecast."""

from fastapi import APIRouter, Query

from src.engine.inputs import load
from src.engine.analitica.rolling_forecast_mensal import build_rolling_forecast

router = APIRouter(prefix="/api")


@router.get("/rolling-forecast/mensal")
def get_rolling_forecast(scenario: str = Query("Base")):
    a, base, sched = load(cenario=scenario)
    rf = build_rolling_forecast(a, base, sched)

    dr_mensal = rf.get("dr_mensal")
    tesouraria = rf.get("tesouraria_completa")

    return {
        "dr_mensal": dr_mensal.to_dict(orient="records") if hasattr(dr_mensal, "to_dict") else [],
        "tesouraria": tesouraria.to_dict(orient="records") if hasattr(tesouraria, "to_dict") else [],
    }


@router.post("/rolling-forecast/update")
def post_rolling_forecast(body: dict):
    """Atualiza rolling forecast com valores realizados."""
    return {"status": "ok", "message": "Not implemented"}
