"""Rotas do rolling forecast."""

from fastapi import APIRouter, Query

from src.engine.inputs import load
from src.engine.demonstracoes.rolling_forecast_mensal import build_rolling_forecast

router = APIRouter(prefix="/api")


def _df_to_records(df):
    return df.to_dict(orient="records") if hasattr(df, "to_dict") else []


def _reconciliacao_dfc(dfc_mensal, sched, cenario: str) -> dict:
    """Compara soma da DFC mensal com os valores anuais de referência do schedules."""
    if dfc_mensal is None or not hasattr(dfc_mensal, "sum"):
        return {}

    soma_op = int(dfc_mensal["fluxo_operacional"].sum())
    soma_inv = int(dfc_mensal["fluxo_investimento"].sum())
    soma_fin = int(dfc_mensal["fluxo_financiamento"].sum())
    soma_var_caixa = int(dfc_mensal["variacao_caixa"].sum())
    caixa_abertura = int(dfc_mensal["caixa_abertura"].iloc[0])
    caixa_fecho_dez = int(dfc_mensal["caixa_fecho"].iloc[-1])
    delta_caixa = caixa_fecho_dez - caixa_abertura

    # Referência anual 2025 do schedules.yaml
    ref_dr = sched.reference_dr
    ref_b = sched.reference_balanco
    ref_caixa_ini = ref_b.get("caixa", {}).get(2024, 0)
    ref_caixa_fin = ref_b.get("caixa", {}).get(2025, 0)

    return {
        "cenario": cenario,
        "soma_mensal": {
            "fluxo_operacional": soma_op,
            "fluxo_investimento": soma_inv,
            "fluxo_financiamento": soma_fin,
            "variacao_caixa": soma_var_caixa,
        },
        "caixa_abertura_jan": caixa_abertura,
        "caixa_fecho_dez": caixa_fecho_dez,
        "delta_caixa_mensal": delta_caixa,
        "referencia_anual_2025": {
            "caixa_ini_2024": round(ref_caixa_ini),
            "caixa_fin_2025": round(ref_caixa_fin),
            "delta_caixa_anual": round(ref_caixa_fin - ref_caixa_ini),
        },
        "desvio_variacao_caixa": soma_var_caixa - delta_caixa,
    }


@router.get("/rolling-forecast/mensal")
def get_rolling_forecast(scenario: str = Query("Base")):
    a, base, sched = load(cenario=scenario)
    rf = build_rolling_forecast(a, base, sched)

    dfc_mensal = rf.get("dfc_mensal")

    return {
        "dr_mensal": _df_to_records(rf.get("dr_mensal")),
        "balanco_mensal": _df_to_records(rf.get("balanco_mensal")),
        "dfc_mensal": _df_to_records(dfc_mensal),
        "nfm_mensal": _df_to_records(rf.get("nfm_mensal")),
        "tesouraria": _df_to_records(rf.get("tesouraria_completa")),
        "reconciliacao_dfc": _reconciliacao_dfc(dfc_mensal, sched, scenario),
    }


@router.post("/rolling-forecast/update")
def post_rolling_forecast(body: dict):
    """Atualiza rolling forecast com valores realizados."""
    return {"status": "ok", "message": "Not implemented"}
