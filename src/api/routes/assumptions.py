"""Rotas de pressupostos e configura??o."""

from fastapi import APIRouter, Query

from src.api.serializers import _build_assumptions_response
from src.engine.operacional.fse import fse_rubricas_ordered

router = APIRouter(prefix="/api")


@router.get("/assumptions/effective")
def get_assumptions_effective(
    cenario: str = Query("Base"),
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(False),
):
    return _build_assumptions_response(cenario, hub_on, ecogres_on)


@router.get("/config/fse-rubricas")
def get_fse_rubricas():
    """Devolve rubricas de FSE declaradas em contrato."""
    return {
        "rubricas": [
            {"yaml_key": yaml_key, "dr_col": dr_col, "label": label}
            for yaml_key, dr_col, label in fse_rubricas_ordered()
        ]
    }


@router.get("/config/years")
def get_config_years():
    return {"years": [2024, 2025, 2026, 2027, 2028, 2029]}

