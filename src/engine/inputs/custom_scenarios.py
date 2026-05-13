"""Gest?o dos cen?rios customizados."""

from __future__ import annotations

from typing import Any

import yaml

from .paths import CUSTOM_SCENARIOS_FILE
from .yaml_io import _yaml_load


def load_custom_scenarios() -> dict[str, Any]:
    """Carrega cenários customizados."""
    if not CUSTOM_SCENARIOS_FILE.exists():
        return {"scenarios": {}}

    data = _yaml_load(CUSTOM_SCENARIOS_FILE, required=False)
    data.setdefault("scenarios", {})

    return data


def save_custom_scenarios(data: dict[str, Any]) -> None:
    """Guarda cenários customizados."""
    data.setdefault("scenarios", {})

    with open(CUSTOM_SCENARIOS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def custom_scenario_names() -> list[str]:
    """Lista nomes de cenários customizados."""
    return list(load_custom_scenarios().get("scenarios", {}).keys())


def get_custom_scenario(name: str) -> dict[str, Any] | None:
    """Obtém um cenário customizado pelo nome."""
    if name == "Base":
        return None

    return load_custom_scenarios().get("scenarios", {}).get(name)


def upsert_custom_scenario(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Cria ou actualiza um cenário customizado."""
    if not name or name == "Base":
        raise ValueError("Nome de cenário inválido")

    data = load_custom_scenarios()
    scenarios = data.setdefault("scenarios", {})

    existing = scenarios.get(name, {})
    overrides = payload.get("overrides", existing.get("overrides", {})) or {}

    scenarios[name] = {
        "label": payload.get("label", existing.get("label", name)),
        "description": payload.get("description", existing.get("description", "")),
        "overrides": overrides,
    }

    save_custom_scenarios(data)

    return scenarios[name]


def delete_custom_scenario(name: str) -> bool:
    """Apaga um cenário customizado."""
    data = load_custom_scenarios()
    scenarios = data.setdefault("scenarios", {})

    if name not in scenarios:
        return False

    del scenarios[name]
    save_custom_scenarios(data)

    return True
