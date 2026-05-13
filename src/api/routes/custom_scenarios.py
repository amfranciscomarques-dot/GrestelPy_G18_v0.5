"""Rotas para cenários customizados."""

from fastapi import APIRouter, HTTPException

from src.api.schemas import CustomScenarioPayload
from src.engine.inputs import (
    delete_custom_scenario,
    load_custom_scenarios,
    upsert_custom_scenario,
)

router = APIRouter(prefix="/api")


@router.get("/custom-scenarios")
def get_custom_scenarios():
    data = load_custom_scenarios()
    scenarios = data.get("scenarios", {})

    return {
        "scenarios": [
            {
                "name": name,
                "label": info.get("label", name),
                "description": info.get("description", ""),
                "overrides": info.get("overrides", {}),
            }
            for name, info in scenarios.items()
        ]
    }


@router.post("/custom-scenarios/{name}")
def post_custom_scenario(name: str, body: CustomScenarioPayload):
    try:
        upsert_custom_scenario(name, {
            "label": body.label or name,
            "description": body.description or "",
            "overrides": body.overrides or {},
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "ok", "name": name}


@router.delete("/custom-scenarios/{name}")
def delete_custom_scenario_route(name: str):
    return {"status": "ok" if delete_custom_scenario(name) else "not_found"}

