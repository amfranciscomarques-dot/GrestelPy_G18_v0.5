"""Schemas Pydantic usados pela API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RunRequest(BaseModel):
    cenario: str = "Base"
    hub_on: bool = False
    ecogres_on: bool = False
    assumptions: dict[str, Any] | None = None
    persist: bool = False


class CustomScenarioPayload(BaseModel):
    label: str = ""
    description: str = ""
    overrides: dict[str, Any] | None = None
