"""Rotas para edição de ficheiros YAML de pressupostos pelo docente."""

import subprocess
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin")

_DATA_DIR = Path(__file__).resolve().parents[3] / "src" / "engine" / "data"

# Whitelist dos ficheiros editáveis — os marcados com ✓ em guia_docentes.md.
# Ficheiros histórico/* e cenarios/custom_scenarios.yaml ficam excluídos.
_EDITABLE: dict[str, tuple[str, str]] = {
    "globais":          ("pressupostos/globais.yaml",                          "Globais · fiscal, prazos, caixa"),
    "macro_2025":       ("pressupostos/2025/macro.yaml",                       "Macro 2025 · inflação, EUR/USD"),
    "vendas_2025":      ("pressupostos/2025/vendas.yaml",                      "Vendas 2025 · crescimento"),
    "custos_2025":      ("pressupostos/2025/custos.yaml",                      "Custos 2025 · FSE, pessoal, CMVMC"),
    "mix_2025":         ("pressupostos/2025/mix.yaml",                         "Mix 2025 · distribuição mensal"),
    "macro_2026_2029":  ("pressupostos/2026_2029/macro.yaml",                  "Macro 2026-2029"),
    "vendas_2026_2029": ("pressupostos/2026_2029/vendas.yaml",                 "Vendas 2026-2029 · crescimento"),
    "custos_2026_2029": ("pressupostos/2026_2029/custos.yaml",                 "Custos 2026-2029"),
    "investimento":     ("pressupostos/investimento.yaml",                     "Investimento · CAPEX e depreciação"),
    "schedules":        ("computed/schedules.yaml",                            "Schedules BAU M6"),
    "hub":              ("subsidiarias/hub_logistico/m6_hub_assumptions.yaml", "Hub Logístico M6"),
    "ecogres":          ("subsidiarias/ecogres/ecogres_assumptions.yaml",      "Ecogres"),
    "smart":            ("master/smart_objetivos.yaml",                        "Objetivos SMART"),
}


def _resolve(key: str) -> Path:
    if key not in _EDITABLE:
        raise HTTPException(status_code=404, detail=f"Ficheiro '{key}' não encontrado na whitelist.")
    rel, _ = _EDITABLE[key]
    return _DATA_DIR / rel


class YamlPayload(BaseModel):
    content: str


@router.get("/yaml-files")
def list_yaml_files():
    files = []
    for key, (rel, label) in _EDITABLE.items():
        path = _DATA_DIR / rel
        files.append({"key": key, "label": label, "path": rel, "exists": path.exists()})
    return {"files": files}


@router.get("/yaml/{key}")
def get_yaml_file(key: str):
    path = _resolve(key)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Ficheiro não encontrado em disco: {path}")
    return {"key": key, "content": path.read_text(encoding="utf-8")}


@router.put("/yaml/{key}")
def put_yaml_file(key: str, body: YamlPayload):
    path = _resolve(key)
    try:
        yaml.safe_load(body.content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML inválido: {exc}") from exc
    path.write_text(body.content, encoding="utf-8")
    return {"status": "ok", "key": key}


@router.post("/yaml/{key}/restore")
def restore_yaml_file(key: str):
    path = _resolve(key)
    repo_root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        ["git", "restore", str(path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"git restore falhou: {result.stderr.strip()}")
    return {"status": "ok", "key": key, "content": path.read_text(encoding="utf-8")}
