"""engine/modelo/smart.py — Tracker de objetivos SMART."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

_SMART_YAML = Path(__file__).parent.parent / "data" / "master" / "smart_objetivos.yaml"

_MARGEM_RISCO = 0.05  # desvio máximo antes de ser "cumprido" vs "em_risco"


def _load_objetivos() -> list[dict]:
    with open(_SMART_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)["objetivos"]


def _status(valor: float, alvo: float, operador: str) -> str:
    """Classifica cumprimento: cumprido / em_risco / nao_cumprido."""
    if operador == "gte":
        if valor >= alvo:
            return "cumprido"
        if valor >= alvo * (1 - _MARGEM_RISCO):
            return "em_risco"
        return "nao_cumprido"
    # lte
    if valor <= alvo:
        return "cumprido"
    if valor <= alvo * (1 + _MARGEM_RISCO):
        return "em_risco"
    return "nao_cumprido"


def build_smart_tracker(
    df_kpis: pd.DataFrame,
    df_gas: pd.DataFrame,
) -> pd.DataFrame:
    """Constrói o tracker SMART comparando projeção vs. alvo por objetivo e ano.

    Args:
        df_kpis: output de kpis.build_kpis() — colunas incluem vn, margem_ebitda,
                 autonomia_financeira, ciclo_caixa, etc.
        df_gas:  output de kpis.gas_por_peca_anual() — colunas incluem var_vs_2024.

    Returns:
        DataFrame com uma linha por (objetivo × ano_alvo):
            id, nome, categoria, descricao, ano, kpi_field,
            valor, alvo, operador, unidade, status, desvio_pct
    """
    fontes = {"kpis": df_kpis, "gas": df_gas}
    rows = []

    for obj in _load_objetivos():
        df_fonte = fontes[obj["fonte"]]
        alvo = float(obj["alvo"])

        for ano in obj["anos_alvo"]:
            mask = df_fonte["ano"] == ano
            if not mask.any():
                continue

            valor = float(df_fonte.loc[mask, obj["kpi_field"]].iloc[0])
            desvio = (valor - alvo) / abs(alvo) if alvo else 0.0

            rows.append(
                {
                    "id": obj["id"],
                    "nome": obj["nome"],
                    "categoria": obj["categoria"],
                    "descricao": obj["descricao"],
                    "ano": ano,
                    "kpi_field": obj["kpi_field"],
                    "valor": valor,
                    "alvo": alvo,
                    "operador": obj["operador"],
                    "unidade": obj["unidade"],
                    "status": _status(valor, alvo, obj["operador"]),
                    "desvio_pct": desvio,
                }
            )

    return pd.DataFrame(rows)
