"""Módulo: engine/fse.py — Fornecimentos e Serviços Externos."""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, ALL_YEARS, YEARS, DATA_DIR, MESES

import yaml


def fse_detalhe_mensal_2025(
    a: Assumptions,
    base: Base2024,
    vendas_factor_2025: float,
    dist_sazonal: dict[str, float] | None = None,
) -> dict[str, dict[str, float]]:
    """Detalhe mensal de FSE 2025 por rubrica.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        vendas_factor_2025: Fator de crescimento das vendas em 2025.
        dist_sazonal: Distribuição mensal opcional (default: uniforme 1/12).

    Returns:
        Dict {rubrica: {mes: valor}} com custos positivos.
    """
    from ..inputs import Assumptions

    g_fse_2025 = _cresc_fse_2025_efetivo(a)

    pct_prod = a.fse_params.get("pct_producao", 0.4)
    pct_n = a.fse_params.get("pct_nao_producao", 0.6)

    factor_2025 = (1 + g_fse_2025) * (
        pct_prod * vendas_factor_2025
        + pct_n
    )

    base_vals = getattr(base, "fse_detalhe", {}) or {}

    if dist_sazonal is None:
        dist_sazonal = {m: 1.0 / 12.0 for m in MESES}

    # Get annual detail for 2025 (already reconciled) and use for monthly distribution
    df_det_anual = fse_detalhe_anual(a, base, vendas_factor_2025)
    df_2025 = df_det_anual[df_det_anual.ano == 2025]
    annual_2025_by_rub = dict(zip(df_2025["rubrica"], df_2025["valor"]))

    result: dict[str, dict[str, float]] = {}

    for rubica in FSE_DETALHE_KEYS.keys():
        if rubica == "fse_total":
            continue

        # Use already-reconciled annual values for 2025
        val_2025 = annual_2025_by_rub.get(rubica, 0.0)

        # Distribute monthly by sazonalidade
        result[rubica] = {m: val_2025 * dist_sazonal[m] for m in MESES}

    return result


_CONTRATO_FSE_YAML = (DATA_DIR / "_contrato" / "fse.yaml").resolve()


def _load_fse_contrato() -> tuple[dict[str, str], dict[str, str]]:
    """Carrega o contrato de rubricas de FSE (YAML) com fallback compatível.

    Returns:
        (yaml_key_to_dr_col, yaml_key_to_label)
    """
    try:
        if not _CONTRATO_FSE_YAML.exists():
            raise FileNotFoundError

        with open(_CONTRATO_FSE_YAML, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        rubricas = raw.get("rubricas") or []
        map_y2col: dict[str, str] = {}
        labels: dict[str, str] = {}

        for r in rubricas:
            yaml_key = r.get("yaml_key")
            dr_col = r.get("dr_col")
            label = r.get("label")
            if not yaml_key or not dr_col:
                continue
            map_y2col[str(yaml_key)] = str(dr_col)
            if label:
                labels[str(yaml_key)] = str(label)

        if not map_y2col:
            raise ValueError("Contrato FSE sem rubricas válidas")

        return map_y2col, labels
    except Exception:
        # Fallback compatibility - keeps old columns without special chars.
        return (
            {
                "Subcontratos": "fse_subcontratos",
                "Eletricidade": "fse_eletricidade",
                "Gas_Natural": "fse_gas_natural",
                "Agua": "fse_agua",
                "Manutencao": "fse_manutencao",
                "Transportes_Fretes": "fse_transportes_fretes",
                "Seguros": "fse_seguros",
                "Comunicacoes": "fse_comunicacoes",
                "Honorarios": "fse_honorarios",
                "Rendas": "fse_rendas_alugueres",
                "Limpeza": "fse_limpeza",
                "Vigilancia": "fse_vigilancia",
                "Outros_FSE": "fse_outros_fse",
            },
            {
                "Subcontratos": "Subcontratos",
                "Eletricidade": "Eletricidade",
                "Gas_Natural": "Gas Natural",
                "Agua": "Agua",
                "Manutencao": "Manutencao e Reparacao",
                "Transportes_Fretes": "Transportes e Fretes",
                "Seguros": "Seguros",
                "Comunicacoes": "Comunicacoes",
                "Honorarios": "Honorarios",
                "Rendas": "Rendas e Alugueres",
                "Limpeza": "Limpeza",
                "Vigilancia": "Seguranca e Vigilancia",
                "Outros_FSE": "Outros FSE",
            },
        )


FSE_DETALHE_KEYS, FSE_DETALHE_LABELS = _load_fse_contrato()


def fse_rubricas_ordered() -> list[tuple[str, str, str]]:
    """Devolve lista ordenada: (yaml_key, dr_col, label)."""
    try:
        if not _CONTRATO_FSE_YAML.exists():
            raise FileNotFoundError
        with open(_CONTRATO_FSE_YAML, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        rubricas = raw.get("rubricas") or []
        out: list[tuple[str, str, str]] = []
        for r in rubricas:
            yaml_key = r.get("yaml_key")
            dr_col = r.get("dr_col")
            label = r.get("label")
            if not yaml_key or not dr_col:
                continue
            out.append((str(yaml_key), str(dr_col), str(label or yaml_key)))
        return out
    except Exception:
        return [
            (k, v, FSE_DETALHE_LABELS.get(k, k))
            for k, v in FSE_DETALHE_KEYS.items()
        ]


def fse_rubricas_shares_2024(base: Base2024) -> dict[str, float]:
    """Shares (0..1) das rubricas de FSE calculadas a partir de 2024.

    Exclui `fse_total` e normaliza pelo somatório das rubricas.
    """
    raw = getattr(base, "fse_detalhe", {}) or {}
    vals: dict[str, float] = {}
    for rub_key in FSE_DETALHE_KEYS.keys():
        try:
            vals[rub_key] = float(raw.get(rub_key, 0.0))
        except Exception:
            vals[rub_key] = 0.0

    total = float(sum(vals.values()))
    if total <= 0:
        # fallback determinístico (evita divisões por zero)
        n = max(1, len(vals))
        return {k: 1.0 / n for k in vals.keys()}

    return {k: v / total for k, v in vals.items()}



def _cresc_fse_2025_efetivo(a: Assumptions) -> float:
    """Taxa anual efectiva de FSE para 2025, com suporte a acréscimos mensais.

    Se `acrescimos_mensais` não estiver definido, devolve directamente `base_2025`
    (comportamento idêntico ao anterior).  Quando está presente, calcula a taxa
    anual composta a partir dos 12 factores mensais:
        taxa_ef = ∏(1 + r_m  para m em MESES) - 1
    """
    block = a._driver_block("fse")
    acrescimos = block.get("acrescimos_mensais") or block.get("overrides_mensais") or {}

    if not acrescimos:
        return a.cresc_2025_anual("fse")

    from ..operacoes.vendas import _monthly_rates

    rates = _monthly_rates(block)
    factor = 1.0
    for m in MESES:
        factor *= 1.0 + rates[m]
    return factor - 1.0


def _get_fse_2024_dr(base: Base2024) -> float:
    """Obtém o FSE real de 2024 a partir do YAML/base2024.

    Prioridade:
      1. base.raw["dr_2024_real"]["fse"]
      2. soma de base.fse_detalhe.values()

    Isto evita usar valores hardcoded no modelo.
    """
    try:
        return float(base.raw["dr_2024_real"]["fse"])
    except (AttributeError, KeyError, TypeError, ValueError):
        return float(sum(base.fse_detalhe.values()))


def fse_anual(
    a: Assumptions,
    base: Base2024,
    vendas_factor_2025: float,
) -> pd.DataFrame:
    """FSE anual 2024-2029.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        vendas_factor_2025: Fator de crescimento das vendas em 2025.
            Mantido por compatibilidade com chamadas existentes.

    Returns:
        DataFrame com colunas:
        ano, fse.
    """
    fse_2024_dr = _get_fse_2024_dr(base)

    # Detalhe Nota 27 / FSE detalhado no YAML.
    # Para 2025 em diante, usamos o detalhe como base operacional.
    # Exclui "fse_total" que é a soma das rubricas (evita dupla contagem).
    fse_2024_n27 = float(sum(
        v for k, v in base.fse_detalhe.items()
        if k != "fse_total"
    ))

    g_fse_2025 = _cresc_fse_2025_efetivo(a)
    fse_2025 = fse_2024_n27 * (1 + g_fse_2025)

    g_fse_yr = a.cresc_2026_2029("fse")

    fse = {
        2024: fse_2024_dr,
        2025: fse_2025,
    }

    for y in YEARS[1:]:
        fse[y] = fse[y - 1] * (1 + g_fse_yr[y])

    return pd.DataFrame(
        [
            {
                "ano": y,
                "fse": fse[y],
            }
            for y in ALL_YEARS
        ]
    )


def fse_detalhe_anual(
    a: Assumptions,
    base: Base2024,
    vendas_factor_2025: float,
) -> pd.DataFrame:
    """Detalhe anual de FSE por rubrica.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        vendas_factor_2025: Fator de crescimento das vendas em 2025.

    Returns:
        DataFrame com colunas:
        ano, rubrica, valor.
    """
    g_fse_2025 = _cresc_fse_2025_efetivo(a)

    pct_prod = a.fse_params.get("pct_producao", 0.4)
    pct_n = a.fse_params.get("pct_nao_producao", 0.6)

    factor_2025 = (1 + g_fse_2025) * (
        pct_prod * vendas_factor_2025
        + pct_n
    )

    g_yr = a.cresc_2026_2029("fse")

    rows = []

    # Garantir que o detalhe inclui TODAS as rubricas do contrato,
    # mesmo quando o YAML base2024 não contém o valor (assume 0).
    base_vals = getattr(base, "fse_detalhe", {}) or {}

    # Normalizar chaves: mapear versões com e sem acento
    _NORMALIZE = {
        "Água": "Água",
        "Manutenção": "Manutenção",
        "Comunicações": "Comunicações",
        "Honorários": "Honorários",
        "Rendas": "Rendas",
        "Limpeza": "Limpeza",
        "Vigilância": "Vigilância",
    }

    for rubica in FSE_DETALHE_KEYS.keys():
        if rubica == "fse_total":
            continue

        # Try direct key match first
        val_2024 = float(base_vals.get(rubica, 0.0) or 0.0)
        
        v = {
            2024: val_2024,
            2025: val_2024 * factor_2025,
        }

        for y in YEARS[1:]:
            v[y] = v[y - 1] * (1 + g_yr[y])

        for y in ALL_YEARS:
            rows.append({"ano": y, "rubrica": rubica, "valor": v[y]})

    df = pd.DataFrame(rows)

    # Reconciliação: garantir que a soma das rubricas fecha com o total do FSE anual.
    # Obter o total FSE por ano de fse_anual()
    from .fse import fse_anual as _fse_anual_func

    fse_totals = _fse_anual_func(a, base, vendas_factor_2025)
    fse_total_by_year = dict(zip(fse_totals["ano"], fse_totals["fse"]))

    # Ajuste: se a soma das rubricas não fecha, ajustar proporcionalmente
    for y in ALL_YEARS:
        target = fse_total_by_year.get(y, 0.0)
        actual = df[df.ano == y]["valor"].sum()
        if actual and target and abs(actual - target) > 1.0:
            scale = target / actual
            df.loc[df.ano == y, "valor"] = df[df.ano == y]["valor"] * scale

    return df
