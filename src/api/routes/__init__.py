"""Agregador dos sub-routers da API."""

from fastapi import APIRouter

from .assumptions import get_assumptions_effective, get_fse_rubricas, get_config_years
from .assumptions import router as assumptions_router
from .custom_scenarios import (
    delete_custom_scenario_route,
    get_custom_scenarios,
    post_custom_scenario,
)
from .custom_scenarios import router as custom_router
from .ecogres import get_ecogres
from .ecogres import router as ecogres_router
from .hub import get_hub_tornado, get_hub_viability
from .hub import router as hub_router
from .pressupostos import get_pressupostos
from .pressupostos import router as pressupostos_router
from .rolling import get_rolling_forecast, post_rolling_forecast
from .rolling import router as rolling_router
from .scenarios import get_scenarios_all, post_run
from .scenarios import router as scenarios_router

router = APIRouter()
router.include_router(pressupostos_router)
router.include_router(scenarios_router)
router.include_router(assumptions_router)
router.include_router(hub_router)
router.include_router(ecogres_router)
router.include_router(custom_router)
router.include_router(rolling_router)
