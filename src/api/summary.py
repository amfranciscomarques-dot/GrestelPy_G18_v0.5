import time
import traceback
import hashlib
import json
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["summary"])

# Simple in-memory cache: key -> (timestamp, payload)
_CACHE: dict = {}
_TTL = 300  # seconds

def _key(**kwargs) -> str:
    return hashlib.sha1(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()


@router.get("/summary")
def summary(hub_on: bool = False, ecogres_on: bool = False, cenario: str = "Base"):
    k = _key(hub_on=hub_on, ecogres_on=ecogres_on, cenario=cenario)
    now = time.time()
    if k in _CACHE and now - _CACHE[k][0] < _TTL:
        return _CACHE[k][1]

    try:
        # import here to avoid heavy imports during server start if engine missing
        from src.engine.modelo.model import run_model

        res = run_model(cenario=cenario, hub_on=hub_on, ecogres_on=ecogres_on)

        # Extract lightweight KPIs. Adjust attribute names to match run_model outputs.
        kpis = {
            "cenario": cenario,
            "hub_on": hub_on,
            "ecogres_on": ecogres_on,
            "receita_total": float(getattr(res, "receita_total", 0) or 0),
            "ebitda": float(getattr(res, "ebitda", 0) or 0),
            "n_linhas": int(len(res)) if hasattr(res, "__len__") else None,
        }

        _CACHE[k] = (now, kpis)
        return kpis
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": str(e), "trace": traceback.format_exc().splitlines()[-5:]},
        )
