"""Configuration helpers for the Grestel Financial Model engine."""

from __future__ import annotations

# ── Horizonte temporal do modelo ─────────────────────────────────────────────
ANO_BASE: int = 2024          # último ano histórico (dados reais R&C)
ANO_ARRANQUE: int = 2025      # primeiro ano de projeção
ANO_FIM: int = 2029           # último ano de projeção

ANOS_PROJECAO: list[int] = list(range(ANO_ARRANQUE, ANO_FIM + 1))  # [2025..2029]
ANOS_MODELO: list[int] = [ANO_BASE] + ANOS_PROJECAO                # [2024..2029]
