"""Costa Nova Logistics Hub 4.0 — Projeto M6.

Hub logístico automatizado (ZI Vagos, Lotes 77-85) com AMR, VLM, Cobots Vision AI,
WMS integrado e Digital Twin.

Funções exportadas:
  load()               — carrega m6_hub_assumptions.yaml
  hub_capex(hub)       — CAPEX schedule e AFT rolling (2025-2029)
  hub_financing(hub)   — empréstimo bancário CGD/BPI + amortizações + juros
  hub_dr_impact(hub)   — impacto per-line no DR da Grestel (anual, 2025-2029)
  hub_dfc_impact(hub)  — impacto nos fluxos de caixa da Grestel
  hub_fcf(hub)         — FCF livre unlevered para análise de viabilidade
  viabilidade_hub(hub) — NPV, TIR, Payback simples e ajustado
  tornado_hub(hub)     — análise de sensibilidade tornado do VPL
"""

from __future__ import annotations

import copy
from typing import Sequence

import pandas as pd
import yaml
from pathlib import Path

from ..inputs import DATA_DIR


def _hub_assumptions_path() -> Path:
    return DATA_DIR / "subsidiarias" / "hub_logistico" / "m6_hub_assumptions.yaml"


YEARS = [2025, 2026, 2027, 2028, 2029]


def load() -> dict:
    """Carrega m6_hub_assumptions.yaml."""
    with open(_hub_assumptions_path(), "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# CAPEX e Depreciação
# ---------------------------------------------------------------------------

def hub_capex(hub: dict) -> pd.DataFrame:
    """CAPEX schedule do Hub e evolução do AFT líquido.

    CAPEX base: 5.500.000€ todo em 2025. #atençao ao novo capex
    Vida útil: 10 anos → depreciação: 550.000€/ano a partir de 2026.
    """
    proj = hub["projeto_hub"]

    capex_base = float(proj["capex"]["base"])
    cron = proj["capex"]["cronograma"]
    taxa_dep = float(proj["capex"]["taxa_depreciacao"])
    ano_inicio_op = int(proj["ano_inicio_beneficios"])

    dep_anual = capex_base * taxa_dep

    aft = 0.0
    rows = []

    for y in YEARS:
        capex_y = float(cron.get(y, 0.0))
        dep_y = dep_anual if y >= ano_inicio_op else 0.0

        aft = aft + capex_y - dep_y

        rows.append(
            {
                "ano": y,
                "capex": capex_y,
                "depreciacao": dep_y,
                "aft_liquido_fim": max(aft, 0.0),
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Financiamento Bancário
# ---------------------------------------------------------------------------

def hub_financing(hub: dict) -> pd.DataFrame:
    """Empréstimo bancário Hub.

    - Desembolso no ano indicado no YAML
    - Amortizações a partir de `inicio_amortizacao`
    """
    proj = hub["projeto_hub"]
    banco = proj["financiamento"]["Banco_Hub"]

    capital = float(banco["montante"])
    taxa = float(banco["taxa_juro"])
    amort_anual = float(banco["amortizacao_anual"])
    inicio_amort = int(banco["inicio_amortizacao"])
    desembolso_ano = int(banco["desembolso"])

    saldo = 0.0
    rows = []

    for y in YEARS:
        if y == desembolso_ano:
            saldo = capital

        juros = saldo * taxa

        amort = amort_anual if y >= inicio_amort and saldo > 0 else 0.0
        amort = min(amort, saldo)

        saldo = max(saldo - amort, 0.0)

        prox_amort = amort_anual if saldo > 0 else 0.0
        emp_c = min(prox_amort, saldo)
        emp_nc = max(saldo - emp_c, 0.0)

        rows.append(
            {
                "ano": y,
                "saldo_fim": saldo,
                "emprestimos_nc": emp_nc,
                "emprestimos_c": emp_c,
                "juros": juros,
                "amortizacao": amort,
                "desembolso": capital if y == desembolso_ano else 0.0,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# PT2030 — Subsídio ao Investimento
# ---------------------------------------------------------------------------

def pt2030_reconhecimento(hub: dict) -> dict[int, float]:
    """Subsídio PT2030 reconhecido no DR como outros rendimentos.

    SNC: subsídio ao investimento amortizado pelo período de vida do ativo.
    """
    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]

    montante = float(pt["montante"])
    vida_util = float(proj["capex"]["vida_util_anos"])
    inicio = int(proj["ano_inicio_beneficios"])

    anual = montante / vida_util

    return {
        y: anual if y >= inicio else 0.0
        for y in YEARS
    }


# ---------------------------------------------------------------------------
# Impacto no DR da Grestel
# ---------------------------------------------------------------------------

def hub_dr_impact(
    hub: dict,
    crescimento_anual: float | None = None,
) -> dict[int, dict]:
    """Impacto anual do Hub no DR standalone da Grestel."""
    proj = hub["projeto_hub"]

    if crescimento_anual is None:
        crescimento_anual = float(proj["beneficios_anuais"]["crescimento_anual"])

    ben = proj["beneficios_anuais"]
    ben_pontual = proj["beneficios_pontuais"]
    inicio = int(proj["ano_inicio_beneficios"])

    poupanca_op = float(ben["poupanca_operacional"])
    reducao_quebras = float(ben["reducao_quebras"])

    # Mantido por compatibilidade com o modelo atual.
    _ = abs(float(ben["opex_incremental"]))

    pessoal_pct = 0.68
    fse_pct = 0.32

    poupanca_pessoal_base = poupanca_op * pessoal_pct
    poupanca_fse_base = poupanca_op * fse_pct

    fse_opex_base = float(
        ben.get("opex_incremental")
        or proj.get("opex_detalhe", {}).get("total", 0)
    )

    subsidio = pt2030_reconhecimento(hub)

    inventario_one_time = float(ben_pontual["libertacao_inventario"])
    ano_inventario = int(ben_pontual["ano"])

    df_cap = hub_capex(hub)
    capex_map = df_cap.set_index("ano")

    result: dict[int, dict] = {}

    for y in YEARS:
        if y < inicio:
            result[y] = {
                "pessoal_reducao": 0.0,
                "fse_reducao": 0.0,
                "cmvmc_reducao": 0.0,
                "fse_opex_hub": 0.0,
                "outros_rend_subsidio": 0.0,
                "depreciacao_hub": 0.0,
                "inventario_libertado": 0.0,
                "beneficio_liquido": 0.0,
                "ebitda_impact": 0.0,
                "ebit_impact": 0.0,
            }
            continue

        n = y - inicio
        fator = (1 + crescimento_anual) ** n

        pessoal_red = poupanca_pessoal_base * fator
        fse_red = poupanca_fse_base * fator
        cmvmc_red = reducao_quebras * fator
        fse_opex = fse_opex_base * fator
        subsidio_y = subsidio.get(y, 0.0)

        dep_hub = (
            float(capex_map.loc[y, "depreciacao"])
            if y in capex_map.index
            else 0.0
        )

        inventario = inventario_one_time if y == ano_inventario else 0.0

        beneficio_liq = pessoal_red + fse_red + cmvmc_red - fse_opex
        ebitda_impact = beneficio_liq + subsidio_y
        ebit_impact = ebitda_impact - dep_hub

        result[y] = {
            "pessoal_reducao": pessoal_red,
            "fse_reducao": fse_red,
            "cmvmc_reducao": cmvmc_red,
            "fse_opex_hub": fse_opex,
            "outros_rend_subsidio": subsidio_y,
            "depreciacao_hub": dep_hub,
            "inventario_libertado": inventario,
            "beneficio_liquido": beneficio_liq,
            "ebitda_impact": ebitda_impact,
            "ebit_impact": ebit_impact,
        }

    return result


# ---------------------------------------------------------------------------
# Impacto no DFC da Grestel
# ---------------------------------------------------------------------------

def hub_dfc_impact(hub: dict) -> dict[int, dict]:
    """Impacto nos fluxos de caixa da Grestel."""
    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]

    pt_montante = float(pt["montante"])
    pt_ano = int(pt["ano_recebimento"])

    df_cap = hub_capex(hub)
    df_fin = hub_financing(hub)

    capex_map = df_cap.set_index("ano")
    fin_map = df_fin.set_index("ano")

    result: dict[int, dict] = {}

    for y in YEARS:
        capex_y = (
            float(capex_map.loc[y, "capex"])
            if y in capex_map.index
            else 0.0
        )

        juros_y = (
            float(fin_map.loc[y, "juros"])
            if y in fin_map.index
            else 0.0
        )

        amort_y = (
            float(fin_map.loc[y, "amortizacao"])
            if y in fin_map.index
            else 0.0
        )

        desembolso_y = (
            float(fin_map.loc[y, "desembolso"])
            if y in fin_map.index
            else 0.0
        )

        pt2030_y = pt_montante if y == pt_ano else 0.0

        result[y] = {
            "capex_hub": -capex_y,
            "pt2030_recebimento": pt2030_y,
            "desembolso_banco": desembolso_y,
            "amortizacao_banco": -amort_y,
            "juros_banco": -juros_y,
            "fluxo_investimento_hub": -capex_y + pt2030_y,
            "fluxo_financiamento_hub": desembolso_y - amort_y - juros_y,
        }

    return result


# ---------------------------------------------------------------------------
# FCF Livre — Análise de Viabilidade
# ---------------------------------------------------------------------------

def hub_fcf(
    hub: dict,
    irc_taxa: float = 0.225,
    incluir_inventario: bool = True,
) -> pd.DataFrame:
    """FCF unlevered do Hub para análise de viabilidade.

    FCF = NOPAT + Dep - CAPEX - ΔNFM
    NOPAT = EBIT × (1 - t)
    """
    dr_imp = hub_dr_impact(hub)
    df_cap = hub_capex(hub)

    capex_map = df_cap.set_index("ano")

    rows = []

    for y in YEARS:
        capex_y = (
            float(capex_map.loc[y, "capex"])
            if y in capex_map.index
            else 0.0
        )

        dep_y = (
            float(capex_map.loc[y, "depreciacao"])
            if y in capex_map.index
            else 0.0
        )

        imp = dr_imp[y]
        ebit_y = float(imp["ebit_impact"])

        inventario_y = (
            float(imp["inventario_libertado"])
            if incluir_inventario
            else 0.0
        )

        nopat = ebit_y * (1 - irc_taxa) if ebit_y > 0 else ebit_y
        fcf = nopat + dep_y - capex_y + inventario_y

        rows.append(
            {
                "ano": y,
                "ebitda_impact": imp["ebitda_impact"],
                "ebit_impact": ebit_y,
                "nopat": nopat,
                "depreciacao": dep_y,
                "capex": -capex_y,
                "inventario_libertado": inventario_y,
                "fcf_livre": fcf,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Funções financeiras: VPL, TIR, Payback
# ---------------------------------------------------------------------------

def _npv(cashflows: Sequence[float], rate: float) -> float:
    """Valor Presente Líquido."""
    return sum(
        cf / (1 + rate) ** t
        for t, cf in enumerate(cashflows)
    )


def _irr(
    cashflows: Sequence[float],
    low: float = -0.99,
    high: float = 10.0,
    tol: float = 1e-7,
    max_iter: int = 300,
) -> float | None:
    """Taxa Interna de Rentabilidade por bissecção."""
    try:
        v_low = _npv(cashflows, low)
        v_high = _npv(cashflows, high)

        if v_low * v_high > 0:
            return None

        for _ in range(max_iter):
            mid = (low + high) / 2.0
            v_mid = _npv(cashflows, mid)

            if abs(v_mid) < tol:
                return mid

            if _npv(cashflows, low) * v_mid < 0:
                high = mid
            else:
                low = mid

        return (low + high) / 2.0

    except Exception:
        return None


def _payback(cashflows: Sequence[float]) -> float | None:
    """Payback simples."""
    acum = 0.0

    for t, cf in enumerate(cashflows):
        prev_acum = acum
        acum += cf

        if prev_acum < 0 and acum >= 0 and t > 0:
            frac = (-prev_acum) / cf if cf else 0.0
            return (t - 1) + frac

    return None


def _discounted_payback(
    cashflows: Sequence[float],
    rate: float,
) -> float | None:
    """Payback atualizado."""
    disc = [
        cf / (1 + rate) ** t
        for t, cf in enumerate(cashflows)
    ]

    return _payback(disc)


def viabilidade_hub(
    hub: dict | None = None,
    irc_taxa: float | None = None,
    wacc: float | None = None,
    incluir_inventario: bool = True,
) -> dict:
    """Análise de viabilidade completa do Hub Logístico 4.0."""
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.225))

    if wacc is None:
        wacc = float(via["wacc"])

    g_terminal = float(via["taxa_crescimento_terminal"])
    horizonte = int(via["horizonte_anos"])

    df_fcf = hub_fcf(
        hub,
        irc_taxa=irc_taxa,
        incluir_inventario=incluir_inventario,
    )

    anos_modelo = list(df_fcf["ano"])
    ultimo_ano = anos_modelo[-1]

    fcf_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["fcf_livre"].iloc[0])
    ebitda_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["ebitda_impact"].iloc[0])
    dep_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["depreciacao"].iloc[0])

    ext_rows = []
    g = float(proj["beneficios_anuais"]["crescimento_anual"])

    fcf_prev = fcf_ultimo
    ebitda_prev = ebitda_ultimo

    for k in range(1, horizonte - len(anos_modelo) + 1):
        y_ext = ultimo_ano + k

        fcf_ext = fcf_prev * (1 + g)
        ebitda_ext = ebitda_prev * (1 + g)

        ebit_ext = ebitda_ext - dep_ultimo

        ext_rows.append(
            {
                "ano": y_ext,
                "ebitda_impact": ebitda_ext,
                "ebit_impact": ebit_ext,
                "nopat": max(ebit_ext, 0.0) * (1 - irc_taxa),
                "depreciacao": dep_ultimo,
                "capex": 0.0,
                "inventario_libertado": 0.0,
                "fcf_livre": fcf_ext,
            }
        )

        fcf_prev = fcf_ext
        ebitda_prev = ebitda_ext

    if ext_rows:
        df_fcf = pd.concat(
            [df_fcf, pd.DataFrame(ext_rows)],
            ignore_index=True,
        )

    fcf_t = float(df_fcf["fcf_livre"].iloc[-1])

    vt = (
        fcf_t * (1 + g_terminal) / (wacc - g_terminal)
        if wacc > g_terminal
        else 0.0
    )

    cfs = list(df_fcf["fcf_livre"])
    cfs[-1] += vt

    vpl = _npv(cfs, wacc)
    tir = _irr(cfs)
    pb = _payback(cfs)
    pb_disc = _discounted_payback(cfs, wacc)

    capex_base = float(proj["capex"]["base"])
    indice_rendibilidade = (1 + vpl / capex_base) if capex_base else None

    return {
        "fcf_df": df_fcf,
        "valor_terminal": vt,
        "cashflows_vpl": cfs,
        "vpl": vpl,
        "tir": tir,
        "payback_simples": pb,
        "payback_atualizado": pb_disc,
        "indice_rendibilidade": indice_rendibilidade,
        "parametros": {
            "wacc": wacc,
            "irc_taxa": irc_taxa,
            "crescimento_terminal": g_terminal,
            "horizonte_anos": horizonte,
            "incluir_inventario": incluir_inventario,
            "capex_base": capex_base,
            "capex_2025": float(proj["capex"]["cronograma"].get(2025, 0)),
            "capex_2026": float(proj["capex"]["cronograma"].get(2026, 0)),
            "vida_util": int(proj["capex"]["vida_util_anos"]),
            "taxa_depreciacao": float(proj["capex"]["taxa_depreciacao"]),
            "poupanca_operacional": float(proj["beneficios_anuais"]["poupanca_operacional"]),
            "reducao_quebras": float(proj["beneficios_anuais"]["reducao_quebras"]),
            "opex_incremental": float(
                proj["beneficios_anuais"].get("opex_incremental")
                or proj.get("opex_detalhe", {}).get("total", 0)
            ),
            "beneficio_liquido_anual": float(proj["beneficios_anuais"]["beneficio_liquido_anual"]),
            "crescimento_anual": float(proj["beneficios_anuais"]["crescimento_anual"]),
            "libertacao_inventario": float(proj["beneficios_pontuais"]["libertacao_inventario"]),
            "ano_inventario": int(proj["beneficios_pontuais"]["ano"]),
            "banco_montante": float(proj["financiamento"]["Banco_Hub"]["montante"]),
            "banco_taxa_juro": float(proj["financiamento"]["Banco_Hub"]["taxa_juro"]),
            "pt2030_montante": float(proj["financiamento"]["PT2030"]["montante"]),
            "pt2030_ano": int(proj["financiamento"]["PT2030"]["ano_recebimento"]),
            "ano_inicio_beneficios": int(proj["ano_inicio_beneficios"]),
        },
    }


# ---------------------------------------------------------------------------
# Análise de Sensibilidade / Tornado
# ---------------------------------------------------------------------------

def sensibilidade_hub(
    driver: str,
    valores: Sequence[float],
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
) -> pd.DataFrame:
    """One-at-a-time sensibilidade do VPL do Hub."""
    if hub_base is None:
        hub_base = load()

    rows = []

    for v in valores:
        h = copy.deepcopy(hub_base)
        proj = h["projeto_hub"]

        if driver == "beneficio":
            ben = proj["beneficios_anuais"]
            factor = v / float(ben["beneficio_liquido_anual"])

            ben["poupanca_operacional"] = (
                float(ben["poupanca_operacional"]) * factor
            )
            ben["reducao_quebras"] = (
                float(ben["reducao_quebras"]) * factor
            )

        elif driver == "capex":
            old = float(proj["capex"]["base"])
            factor = v / old if old else 1.0

            proj["capex"]["base"] = v

            for y in proj["capex"]["cronograma"]:
                proj["capex"]["cronograma"][y] = (
                    float(proj["capex"]["cronograma"][y]) * factor
                )

        elif driver == "wacc":
            res = viabilidade_hub(h, irc_taxa=irc_taxa, wacc=v)

            rows.append(
                {
                    "driver": driver,
                    "valor": v,
                    "vpl": res["vpl"],
                    "tir": res["tir"],
                }
            )

            continue

        elif driver == "inventario":
            proj["beneficios_pontuais"]["libertacao_inventario"] = v

        elif driver == "crescimento":
            proj["beneficios_anuais"]["crescimento_anual"] = v

        else:
            raise ValueError(f"Driver desconhecido: {driver}")

        res = viabilidade_hub(h, irc_taxa=irc_taxa)

        rows.append(
            {
                "driver": driver,
                "valor": v,
                "vpl": res["vpl"],
                "tir": res["tir"],
            }
        )

    return pd.DataFrame(rows)


def tornado_hub(
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
) -> pd.DataFrame:
    """Tornado do VPL Hub: swing de cada driver principal."""
    if hub_base is None:
        hub_base = load()

    proj = hub_base["projeto_hub"]

    ben_base = float(proj["beneficios_anuais"]["beneficio_liquido_anual"])
    capex_base = float(proj["capex"]["base"])
    wacc_base = float(proj["viabilidade"]["wacc"])
    inv_base = float(proj["beneficios_pontuais"]["libertacao_inventario"])
    g_base = float(proj["beneficios_anuais"]["crescimento_anual"])
    pt2030_montante = float(proj["financiamento"]["PT2030"]["montante"])

    vpl_base = viabilidade_hub(hub_base, irc_taxa=irc_taxa)["vpl"]

    cfg = {
        "beneficio": {
            "vals": [ben_base * 0.85, ben_base * 1.15],
            "label": "Benefício líquido/ano (€)",
        },
        "capex": {
            "vals": [capex_base * 1.15, capex_base * 0.85],
            "label": "CAPEX (€)",
        },
        "wacc": {
            "vals": [wacc_base + 0.02, wacc_base - 0.02],
            "label": "WACC (%)",
        },
        "inventario": {
            "vals": [inv_base * 0.70, inv_base * 1.30],
            "label": "Inventário libertado (€)",
        },
        "crescimento": {
            "vals": [g_base - 0.01, g_base + 0.01],
            "label": "Cresc. benefícios (%/ano)",
        },
    }

    rows = []

    for key, info in cfg.items():
        low_v, high_v = info["vals"]

        df_low = sensibilidade_hub(key, [low_v], hub_base, irc_taxa)
        df_high = sensibilidade_hub(key, [high_v], hub_base, irc_taxa)

        vpl_low = float(df_low["vpl"].iloc[0])
        vpl_high = float(df_high["vpl"].iloc[0])

        rows.append(
            {
                "driver": key,
                "label": info["label"],
                "valor_low": low_v,
                "valor_high": high_v,
                "vpl_low": vpl_low,
                "vpl_base": vpl_base,
                "vpl_high": vpl_high,
                "impacto_total": abs(vpl_high - vpl_low),
            }
        )

    # Cenário sem PT2030: montante = 0 → sem reconhecimento anual nem cash-in
    h_sem_pt2030 = copy.deepcopy(hub_base)
    h_sem_pt2030["projeto_hub"]["financiamento"]["PT2030"]["montante"] = 0.0
    vpl_sem_pt2030 = viabilidade_hub(h_sem_pt2030, irc_taxa=irc_taxa)["vpl"]

    rows.append(
        {
            "driver": "pt2030",
            "label": "PT2030 (sem vs. com subsídio)",
            "valor_low": 0.0,
            "valor_high": pt2030_montante,
            "vpl_low": vpl_sem_pt2030,
            "vpl_base": vpl_base,
            "vpl_high": vpl_base,
            "impacto_total": abs(vpl_base - vpl_sem_pt2030),
        }
    )

    return (
        pd.DataFrame(rows)
        .sort_values("impacto_total", ascending=False)
        .reset_index(drop=True)
    )
