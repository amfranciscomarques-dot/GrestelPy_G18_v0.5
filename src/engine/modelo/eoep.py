"""Módulo: engine/eoep.py — Estado e Outros Entes Públicos (IVA, IRC, SS)."""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS, YEARS, MESES


MESES_NUM = {m: i + 1 for i, m in enumerate(MESES)}


def _get_eoep_credor_2024(base: Base2024) -> float:
    """Obtém EOEP credor 2024 a partir dos dados base, com fallback seguro.

    Evita usar o valor hardcoded 460472.58.
    """
    candidates = [
        ("saldos", "EOEP_credor"),
        ("saldos", "eoep_credor"),
        ("saldos", "EOEP_Credor"),
    ]

    for attr, key in candidates:
        try:
            return float(getattr(base, attr)[key])
        except (AttributeError, KeyError, TypeError, ValueError):
            pass

    try:
        return float(base.raw["saldos"]["EOEP_credor"])
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    try:
        return float(base.raw["saldos"]["eoep_credor"])
    except (AttributeError, KeyError, TypeError, ValueError):
        pass

    # Fallback antigo para não quebrar caso a chave ainda não exista no YAML.
    return 460_472.58


def eoep_anual(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    irc_anual: dict,
) -> pd.DataFrame:
    """Calcula saldos anuais de EOEP devedor e credor para o Balanço.

    2024 usa saldos históricos/auditados.
    2025 usa saldos do schedules.yaml.
    2026+ cresce IVA/SS por fatores plurianuais e acrescenta IRC corrente.
    """
    iva_24 = float(base.saldos["EOEP_devedor"])
    eoep_credor_2024 = _get_eoep_credor_2024(base)

    eoep_2025_devedor = abs(float(sched.eoep["IVA_saldo_2024_2025_total"]))

    eoep_2025_credor = (
        float(sched.eoep["IRC_saldo_2025_total"])
        + float(sched.eoep["SS_saldo_2025_total"])
    )

    ab = sched.plurianual_AB
    g_ab73 = ab.get("AB73", 0.025)
    g_ab74 = ab.get("AB74", 0.02)

    eoep_dev = {
        2024: iva_24,
        2025: eoep_2025_devedor,
    }

    eoep_cred = {
        2024: eoep_credor_2024,
        2025: max(0.0, eoep_2025_credor),
    }

    for y in YEARS[1:]:
        eoep_dev[y] = eoep_dev[y - 1] * (
            1 + (g_ab73 if y == 2026 else g_ab74)
        )

        iva_part = max(
            0.0,
            eoep_2025_credor - max(0.0, float(sched.eoep.get("IRC_saldo_2025_total", 0.0))),
        )

        for k in range(2026, y + 1):
            iva_part *= 1 + (g_ab73 if k == 2026 else g_ab74)

        eoep_cred[y] = iva_part + float(irc_anual.get(y, 0.0))

    return pd.DataFrame(
        [
            {
                "ano": y,
                "eoep_devedor": eoep_dev[y],
                "eoep_credor": eoep_cred[y],
            }
            for y in ALL_YEARS
        ]
    )


def eoep_calendario_mensal(
    a: Assumptions,
    base: Base2024,
    vn_mensal: dict[str, float],
    fse_mensal: dict[str, float],
    pessoal_mensal: dict[str, float],
    irc_2024_pago: float,
) -> pd.DataFrame:
    """Calendário mensal de pagamentos fiscais para 2025.

    IVA: pagamento em M+2.
    Segurança Social: pagamento em M+1.
    IRC: pagamentos por conta em Julho, Setembro e Dezembro.
    """
    # Mantido por compatibilidade futura; atualmente não é usado diretamente.
    _ = base

    iva_venda = a.impostos["IVA_Vendas"]
    iva_fse = a.impostos.get("IVA_FSE", 0.15)
    tsu = a.impostos["TSU_Empresa"]

    iva_liq = {
        m: vn_mensal.get(m, 0.0) * iva_venda
        for m in MESES
    }

    iva_ded = {
        m: fse_mensal.get(m, 0.0) * iva_fse
        for m in MESES
    }

    iva_saldo = {
        m: iva_liq[m] - iva_ded[m]
        for m in MESES
    }

    iva_pagamento = {
        m: 0.0
        for m in MESES
    }

    for m in MESES:
        target_idx = MESES_NUM[m] + 2

        if target_idx <= 12:
            iva_pagamento[MESES[target_idx - 1]] += iva_saldo[m]

    ss_pagamento = {
        m: 0.0
        for m in MESES
    }

    for m in MESES:
        target_idx = MESES_NUM[m] + 1

        if target_idx <= 12:
            ss_pagamento[MESES[target_idx - 1]] += (
                pessoal_mensal.get(m, 0.0) * tsu
            )

    ppc_total = float(irc_2024_pago) * 0.765
    ppc_prestacao = ppc_total / 3.0

    irc_ppc = {
        m: 0.0
        for m in MESES
    }

    for mes_ppc in ["Jul", "Set", "Dez"]:
        irc_ppc[mes_ppc] = ppc_prestacao

    rows = []

    for m in MESES:
        total_saidas_fiscais = (
            iva_pagamento[m]
            + ss_pagamento[m]
            + irc_ppc[m]
        )

        rows.append(
            {
                "mes": m,
                "iva_liquidado": iva_liq[m],
                "iva_dedutivel": iva_ded[m],
                "iva_saldo_periodo": iva_saldo[m],
                "iva_pagamento_mes": iva_pagamento[m],
                "ss_pagamento_mes": ss_pagamento[m],
                "irc_ppc_mes": irc_ppc[m],
                "total_saidas_fiscais": total_saidas_fiscais,
            }
        )

    return pd.DataFrame(rows)