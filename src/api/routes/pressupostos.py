"""Rota de pressupostos estruturados."""

from fastapi import APIRouter, Query

from src.engine.modelo.pressupostos import build_pressupostos_summary

router = APIRouter(prefix="/api")


@router.get("/pressupostos")
def get_pressupostos(
    cenario: str = Query("Base"),
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(False),
) -> dict:
    """Retorna resumo estruturado de todos os pressupostos do cenário activo.

    Response schema:
        cenario: str
        hub_ativo: bool
        ecogres_ativo: bool
        sections: [
            {id, label, items: [{label, value, unit, note}]}
        ]
    """
    return build_pressupostos_summary(cenario=cenario, hub_on=hub_on, ecogres_on=ecogres_on)
