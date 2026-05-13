"""
engine/model.py — Lógica comum para CLI e API do modelo financeiro.

Funções:
- run_model() — executa o modelo (DR, Balanço, DFC, KPIs)
- dataframe_to_records() — converte DataFrames para dict JSON
- export_outputs() — exporta para CSV
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import pandas as pd
import numpy as np

from ..inputs import Assumptions, Base2024, Schedules, load, MESES
from ..inputs.yaml_io import _deep_update
from ..demonstracoes import statements
from ..operacional import fse as fse_mod
from ..operacional import vendas as vendas_mod


try:
    from . import kpis as kpis_mod
    HAS_KPIS = True
except ImportError:
    HAS_KPIS = False


class ModelOutput:
    """Contentor simples para resultados dos cenários principais."""

    def __init__(self, cenario: str, dr, balanco, dfc, kpis):
        self.cenario = cenario
        self.dr = dr
        self.balanco = balanco
        self.dfc = dfc
        self.kpis = kpis


def run_model(
    cenario: str = "Base",
    hub_on: bool = False,
    ecogres_on: bool = False,
    assumptions_overrides: dict[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Executa o modelo financeiro anual.

    Args:
        cenario: Nome do cenário (ex: "Base")
        hub_on: Ativa o Hub Logístico M6
        ecogres_on: Ativa a subsidiária Ecogres

    Returns:
        dict com DataFrames:
        - dr: Demonstração de Resultados
        - balanco: Balanço
        - dfc: Demonstração de Fluxos de Caixa
        - kpis: KPIs (se disponível)
        - fse_detalhe_mensal_2025: Dict mensal de FSE por rubrica (2025)
        - fse_detalhe_anual: DataFrame com detalhe anual por rubrica
    """
    a, base, sched = load(cenario=cenario)

    if assumptions_overrides:
        a.raw = _deep_update(a.raw, assumptions_overrides)

    a.raw.setdefault("hub_logistico", {})
    a.raw["hub_logistico"]["incluir_hub"] = bool(hub_on)

    a.raw.setdefault("ecogres", {})
    a.raw["ecogres"]["incluir_ecogres"] = bool(ecogres_on)

    dfs = statements.build_statements(a, base, sched)

    if HAS_KPIS:
        dfs["kpis"] = kpis_mod.build_kpis(
            dfs["dr"],
            dfs["balanco"],
            dfs["dfc"],
        )

    # Calcular Factor de vendas 2025
    df_prod = vendas_mod.vendas_anuais(a, base, sched)
    df_merc = vendas_mod.vendas_mercadorias_anuais(a, base)
    df_total = vendas_mod.resumo_anual(df_prod, df_merc)

    vn_2024 = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])
    factor_vn = vn_2025 / vn_2024 if vn_2024 > 0 else 1.0

    # FSE detalhe anual (todas as rubricas, 2024-2029)
    try:
        df_fse_det_anual = fse_mod.fse_detalhe_anual(a, base, factor_vn)
        dfs["fse_detalhe_anual"] = df_fse_det_anual
    except Exception:
        dfs["fse_detalhe_anual"] = pd.DataFrame(columns=["ano", "rubrica", "valor"])

    # FSE detalhe mensal 2025 (por rubrica)
    try:
        # Sazonalidade uniforme como default
        dist_saz = {m: 1.0 / 12.0 for m in MESES}
        fse_det_mensal = fse_mod.fse_detalhe_mensal_2025(a, base, factor_vn, dist_saz)
        dfs["fse_detalhe_mensal_2025"] = fse_det_mensal
    except Exception:
        dfs["fse_detalhe_mensal_2025"] = {}

    return dfs


def dataframe_to_records(dfs: dict[str, pd.DataFrame]) -> dict[str, list[dict[str, Any]]]:
    """
    Converte DataFrames em dicts JSON-serializáveis.

    Substitui NaN/Inf por None e converte dtypes para tipos Python básicos.

    Args:
        dfs: dict com DataFrames (ex: {"dr": df, "balanco": df, ...})

    Returns:
        dict com records (ex: {"dr": [{"ano": 2024, "vn": 1000, ...}, ...], ...})
    """
    result = {}

    for name, df in dfs.items():
        # Skip dict values (like fse_detalhe_mensal_2025) - handled separately
        if isinstance(df, dict):
            result[name] = df
            continue

        if not isinstance(df, pd.DataFrame):
            result[name] = []
            continue

        records = []
        for _, row in df.iterrows():
            record = {}
            for col, val in row.items():
                # Substituir NaN/Inf por None
                if isinstance(val, float):
                    if np.isnan(val) or np.isinf(val):
                        record[col] = None
                    else:
                        record[col] = val
                # Converter numpy types para Python nativas
                elif isinstance(val, (np.integer, np.floating)):
                    record[col] = val.item()
                elif isinstance(val, np.bool_):
                    record[col] = bool(val)
                else:
                    record[col] = val
            records.append(record)
        result[name] = records

    return result


def export_outputs(dfs: dict[str, pd.DataFrame], output_dir: Path = None):
    """
    Exporta DataFrames para CSV.

    Args:
        dfs: dict com DataFrames
        output_dir: diretório de saída (default: "outputs")
    """
    if output_dir is None:
        output_dir = Path("outputs")

    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in dfs.items():
        df.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
        print(f"Exportado: {output_dir / f'{name}.csv'}")


def run(cenario: str = "Base") -> ModelOutput:
    """Executa o modelo e devolve o formato histórico de cenários."""
    dfs = run_model(cenario=cenario)

    return ModelOutput(
        cenario=cenario,
        dr=dfs["dr"],
        balanco=dfs["balanco"],
        dfc=dfs["dfc"],
        kpis=dfs["kpis"],
    )


def run_all_scenarios() -> dict[str, ModelOutput]:
    """Executa todos os cenários principais."""
    return {
        sc: run(sc)
        for sc in ("Base", "Upside", "Downside", "Stress")
    }
