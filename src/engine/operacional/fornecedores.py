"""Módulo: engine/fornecedores.py — Fornecedores."""

from __future__ import annotations

import pandas as pd

from ..inputs import Base2024, Assumptions, ALL_YEARS


def fornecedores_anual(
    base: Base2024,
    df_cmvmc: pd.DataFrame,
    df_fse: pd.DataFrame,
    a: Assumptions | None = None,
) -> pd.DataFrame:
    """Calcula saldo de fornecedores e mapa de compras por ano.

    Metodologia:
        Compras_MP = CMVMC_prod + EF_MP - EI_MP
        Compras_Merc = CMVMC_merc + EF_Merc - EI_Merc
        Compras_FSE = FSE_total
        Saldo_Fornecedores = Compras_total × (1 + IVA_compras) / 365 × PMP

    2024 usa o valor auditado do balanço.
    """
    cmvmc_idx = df_cmvmc.set_index("ano")
    fse_idx = df_fse.set_index("ano")["fse"].to_dict()

    has_breakdown = (
        "cmvmc_prod" in cmvmc_idx.columns
        and "cmvmc_merc" in cmvmc_idx.columns
    )

    cmvmc_merc_2024 = float(base.totais["CMVMC_Mercadorias_2024"])
    cmvmc_total_2024 = float(base.raw["dr_2024_real"]["cmvmc"])

    merc_share = (
        cmvmc_merc_2024 / cmvmc_total_2024
        if cmvmc_total_2024 > 0
        else 0.08
    )

    if a is not None:
        pmp = float(a.prazos["PMP_Inventarios_dias"])
        iva = float(a.impostos.get("IVA_FSE", 0.15))
        dmi_mp = float(a.prazos["DMI_MP_dias"])
        dmi_merc = float(a.prazos["DMI_Mercadorias_dias"])
    else:
        pmp = 63.0
        iva = 0.15
        dmi_mp = 62.0
        dmi_merc = 164.0

    def _mp_stock(cmvmc_prod: float) -> float:
        """Stock estimado de matérias-primas."""
        return (cmvmc_prod / 365.0) * dmi_mp

    def _merc_stock(cmvmc_merc: float) -> float:
        """Stock estimado de mercadorias."""
        return (cmvmc_merc / 365.0) * dmi_merc

    forn_2024 = float(base.balanco["passivo"]["Fornecedores"])

    cmvmc_prod_24 = (
        float(cmvmc_idx.loc[2024, "cmvmc_prod"])
        if has_breakdown
        else cmvmc_total_2024 * (1 - merc_share)
    )

    cmvmc_merc_24 = (
        float(cmvmc_idx.loc[2024, "cmvmc_merc"])
        if has_breakdown
        else cmvmc_merc_2024
    )

    mp_stock_prev = _mp_stock(cmvmc_prod_24)
    merc_stock_prev = _merc_stock(cmvmc_merc_24)

    rows = []

    for y in ALL_YEARS:
        if y == 2024:
            rows.append(
                {
                    "ano": 2024,
                    "compras_mp": 0.0,
                    "compras_merc": 0.0,
                    "compras_fse": 0.0,
                    "compras_total": 0.0,
                    "fornecedores": forn_2024,
                }
            )
            continue

        cmvmc_total = float(cmvmc_idx.loc[y, "cmvmc"])

        if has_breakdown:
            cmvmc_prod = float(cmvmc_idx.loc[y, "cmvmc_prod"])
            cmvmc_merc = float(cmvmc_idx.loc[y, "cmvmc_merc"])
        else:
            cmvmc_merc = cmvmc_total * merc_share
            cmvmc_prod = cmvmc_total - cmvmc_merc

        mp_stock_ef = _mp_stock(cmvmc_prod)
        merc_stock_ef = _merc_stock(cmvmc_merc)

        compras_mp = cmvmc_prod + mp_stock_ef - mp_stock_prev
        compras_merc = cmvmc_merc + merc_stock_ef - merc_stock_prev
        compras_fse = float(fse_idx.get(y, 0.0))

        compras_total = compras_mp + compras_merc + compras_fse

        saldo = (compras_total * (1.0 + iva) / 365.0) * pmp

        mp_stock_prev = mp_stock_ef
        merc_stock_prev = merc_stock_ef

        rows.append(
            {
                "ano": y,
                "compras_mp": compras_mp,
                "compras_merc": compras_merc,
                "compras_fse": compras_fse,
                "compras_total": compras_total,
                "fornecedores": saldo,
            }
        )

    return pd.DataFrame(rows)