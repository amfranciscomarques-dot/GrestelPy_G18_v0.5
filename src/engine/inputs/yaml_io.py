"""Leitura e normaliza??o de YAML para o modelo."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


def _yaml_load(path: Path, required: bool = True) -> dict[str, Any]:
    """L? um ficheiro YAML e devolve um dicion?rio."""
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Ficheiro YAML n?o encontrado: {path}")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_update(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Atualiza recursivamente um dicion?rio com outro."""
    result = copy.deepcopy(base)

    for key, value in (overrides or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def _load_yaml_layers(paths: list[Path]) -> dict[str, Any]:
    """Carrega uma sequ?ncia de YAMLs e faz merge profundo."""
    out: dict[str, Any] = {}
    for path in paths:
        if path.exists():
            out = _deep_update(out, _yaml_load(path, required=False))
    return out


def _normalizar_chaves_ano(obj: Any) -> Any:
    """Converte chaves de ano em string para int, quando aplic?vel."""
    if isinstance(obj, dict):
        out = {}

        for k, v in obj.items():
            nk = int(k) if isinstance(k, str) and k.isdigit() else k
            out[nk] = _normalizar_chaves_ano(v)

        return out

    if isinstance(obj, list):
        return [_normalizar_chaves_ano(v) for v in obj]

    return obj


def _alias_mercadoria(nome: str) -> str:
    """Normaliza nomes de mercadorias para os identificadores usados no modelo."""
    aliases = {
        "Vidros_&_Cristais": "Vidros_Cristais",
        "Vidros_e_Cristais": "Vidros_Cristais",
        "T?xteis_&_acess?rios": "Texteis_Acessorios",
        "Texteis_&_acessorios": "Texteis_Acessorios",
        "Texteis_e_Acessorios": "Texteis_Acessorios",
        "T?xteis_&_acessorios": "Texteis_Acessorios",
    }

    return aliases.get(nome, nome)


def _normalizar_mercadorias(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza chaves conhecidas em merchandise_families."""
    fams = data.get("merchandise_families", {}) or {}

    if not fams:
        return data

    normalizadas = {}

    for nome, bloco in fams.items():
        normalizadas[_alias_mercadoria(nome)] = bloco or {}

    data = dict(data)
    data["merchandise_families"] = normalizadas

    return data
