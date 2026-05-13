"""server.py — FastAPI backend do modelo financeiro Grestel.

Como correr:
    uvicorn server:app --reload --port 8000
"""

import logging
import sys
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

from src.api.routes import router as api_router

app = FastAPI(title="GrestelPy")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled error em %s", request.url.path)
    traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url.path),
        },
    )


app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

try:
    from src.api.summary import router as summary_router
    app.include_router(summary_router)
except Exception:
    pass


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def root():
    return RedirectResponse("/interface/")


app.mount("/interface", StaticFiles(directory=str(BASE_DIR / "interface"), html=True), name="interface")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
