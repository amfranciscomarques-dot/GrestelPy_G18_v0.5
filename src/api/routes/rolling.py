"""Rotas do rolling forecast."""

from fastapi import APIRouter, Query

from src.engine.inputs import load
from src.engine.demonstracoes.rolling_forecast_mensal import build_rolling_forecast

router = APIRouter(prefix="/api")


def _df_to_records(df):
    return df.to_dict(orient="records") if hasattr(df, "to_dict") else []


@router.get("/rolling-forecast/mensal")
def get_rolling_forecast(scenario: str = Query("Base")):
    a, base, sched = load(cenario=scenario)
    rf = build_rolling_forecast(a, base, sched)

    stmt_m6 = rf.get("stmt_m6", {})

    return {
        "dr_mensal": _df_to_records(rf.get("dr_mensal")),
        "balanco_mensal": _df_to_records(rf.get("balanco_mensal")),
        "dfc_mensal": _df_to_records(rf.get("dfc_mensal")),
        "nfm_mensal": _df_to_records(rf.get("nfm_mensal")),
        "tesouraria": _df_to_records(rf.get("tesouraria_completa")),
        "reconciliacao_anual": rf.get("reconciliacao_anual", {}),
        # Demonstrações anuais M6 — Opção B: Balanço 2025 ancorado no fecho mensal Dez
        "stmt_m6": {
            "dr": _df_to_records(stmt_m6.get("dr")),
            "balanco": _df_to_records(stmt_m6.get("balanco")),
            "dfc": _df_to_records(stmt_m6.get("dfc")),
        },
    }


@router.post("/rolling-forecast/update")
def post_rolling_forecast(body: dict):
    """Atualiza rolling forecast com valores realizados."""
    return {"status": "ok", "message": "Not implemented"}
