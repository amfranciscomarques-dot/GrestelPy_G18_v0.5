"""Rolling Forecast Mensal — Balanço, DFC e NFM mensais para 2025.

Fase 1 do planeamento M3: demonstrações financeiras mensais articuladas,
integrando Investimento, Financiamento, EOEP e Necessidades de Fundo de Maneio.

Metodologia: DFC-first (fluxos de caixa determinam a posição de Caixa).
  1. Mapa de Investimento → variações ANC (AFT)
  2. Demonstração de Resultados → RL acumulado no CP
  3. Todos os itens do Balanço calculados de forma determinística (exceto Caixa)
  4. ΔNFM apurado a partir desses itens
  5. DFC: fluxo_op + fluxo_inv + fluxo_fin → var_caixa
  6. caixa_fecho = caixa_abertura + var_caixa  (nunca negativa; défice → Linha CP)
  7. Balanço fecha naturalmente sem ajuste manual (controlo = 0 por construção)

Caixa NUNCA é plug algébrico do Balanço. O saldo de Caixa resulta sempre do
apuramento dos fluxos de tesouraria. Se insuficiente, activa-se a Linha de
Crédito CP (decisão de gestão sobre défice); se excessivo, aplica-se em
Depósitos/Aplicações CP.

Funções exportadas:
  build_balanco_mensal()      → Balanço sequencial (abertura → Dez)
  build_dfc_mensal()          → DFC indireta (reconciliada com o Balanço)
  build_nfm_mensal()          → NFM e CCC mensais (derivado do Balanço)
  build_tesouraria_completa() → Tesouraria operacional + serviço dívida + CAPEX
  build_rolling_forecast()    → Ponto de entrada: devolve dict com tudo

Simplificações (itens de baixa frequência mensal):
  • Inventários            — interpolação linear abertura→ano-fim 2025
  • EOEP devedor/credor    — interpolação linear entre refs anuais
  • Outros Passivos CP     — interpolação linear
  • Amortizações e CAPEX   — distribuição uniforme (÷12)
  • Empréstimos NC/C       — interpolação linear (amortização uniforme implícita)
"""

from __future__ import annotations

from typing import Optional, Dict, Any

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, MESES
from ..financiamento import tesouraria as teso_mod


# ──────────────────────────────────────────────────────────────────────────────
# Auxiliares internos
# ──────────────────────────────────────────────────────────────────────────────

def _get_eoep_credor_2024(base: Base2024) -> float:
    """Obtém EOEP credor 2024 a partir dos dados base, com fallback seguro."""
    candidates = [
        ("saldos", "EOEP_credor"),
        ("saldos", "eoep_credor"),
        ("saldos", "EOEP_Credor"),
    ]

    for attr, key in candidates:
        try:
            value = getattr(base, attr)[key]
            return float(value)
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

    # Fallback antigo, mantido para não quebrar caso o YAML não tenha a chave.
    return 460_472.58


def _financiamento_mensal(sched: Schedules) -> dict[str, dict]:
    """Distribui serviço da dívida bancária 2025 por mês, uniforme ÷12.

    Amortização = variação anual em Empréstimos NC+C.
    As responsabilidades de locação financeira estão em Outros PC e a sua
    amortização é capturada via ΔOutros_PC no ajuste de NFM da DFC, evitando
    dupla contagem e mantendo a reconciliação DFC-Balanço ≈ 0.
    """
    nc_ini = sched.financiamento["emprestimos_NC"][2024]
    nc_fin = sched.financiamento["emprestimos_NC"][2025]
    c_ini = sched.financiamento["emprestimos_C"][2024]
    c_fin = sched.financiamento["emprestimos_C"][2025]

    amort_banco = (nc_ini + c_ini - nc_fin - c_fin) / 12.0
    juros_a = sched.financiamento["juros_total"][2025]

    d = {
        "amortizacao": amort_banco,
        "juros": juros_a / 12.0,
    }

    return {m: d for m in MESES}


def _capex_mensal(sched: Schedules) -> dict[str, dict]:
    """Distribui CAPEX e depreciação 2025 por mês, uniforme ÷12."""
    inv = sched.investimento

    dep_total_a = inv["total_dep_amort_dr"][2025]
    dep_aft_a = inv["depreciacao_aft_anual"][2025]

    d = {
        "capex_aft": inv["novo_investimento_aft"][2025] / 12.0,
        "capex_int": inv["novo_investimento_intang"][2025] / 12.0,
        "dep_aft": dep_aft_a / 12.0,
        "dep_int": (dep_total_a - dep_aft_a) / 12.0,
        "dep_total": dep_total_a / 12.0,
    }

    return {m: d for m in MESES}


def _interp(ini: float, fin: float, m_idx: int) -> float:
    """Valor no fim do mês m_idx, onde 0=Jan e 11=Dez, por interpolação linear."""
    return ini + (m_idx + 1) / 12.0 * (fin - ini)


# ──────────────────────────────────────────────────────────────────────────────
# Loop Integrado: DFC determina Caixa; Balanço fecha por construção
# ──────────────────────────────────────────────────────────────────────────────

def _build_integrated_monthly(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_dr_m: pd.DataFrame,
    df_t_m: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Loop mensal integrado: DFC determina Caixa; Balanço fecha naturalmente.

    Retorna:
        tuple[pd.DataFrame, pd.DataFrame]: df_balanco, df_dfc.
    """
    caixa_min = a.caixa["minima"]
    caixa_max = a.caixa["maxima"]
    iva_venda = a.impostos["IVA_Vendas"]
    iva_fse = a.impostos.get("IVA_FSE", 0.15)

    fin_m = _financiamento_mensal(sched)
    cap_m = _capex_mensal(sched)
    dr_map = df_dr_m.set_index("mes").to_dict("index")
    t_map = df_t_m.set_index("mes").to_dict("index")

    b = base.balanco
    ref = sched.reference_balanco

    # ── Constantes ─────────────────────────────────────────────────────────────
    anc_outros_base = (
    b["ativo_nao_corrente"]["Goodwill"]
    + b["ativo_nao_corrente"]["Subsidiarias"]
    + b["ativo_nao_corrente"]["Ativos_Fin_Justo_Valor"]
    + b["ativo_nao_corrente"]["Outros_Ativos_Fixos"]
)

    impost_dif_a = b["ativo_nao_corrente"]["Impostos_Diferidos_Ativos"]
    impost_dif_p = b["passivo"]["Impostos_Diferidos_Passivos"]

    rt_opening = (
        b["capital_proprio"]["Resultados_Transitados"]
        + b["capital_proprio"]["RL_2024"]
    )

    cp_fixo = (
        b["capital_proprio"]["Capital_Social"]
        + b["capital_proprio"]["Premios_Emissao"]
        + b["capital_proprio"]["Outros_IC_Proprio"]
        + b["capital_proprio"]["Reservas_Legais"]
        + b["capital_proprio"]["Ajust_AF"]
        + b["capital_proprio"]["Outras_Var_CP"]
        + rt_opening
    )

    eoep_dev_ini = base.saldos["EOEP_devedor"]
    eoep_cred_ini = _get_eoep_credor_2024(base)

    outros_ac = b["ativo_corrente"]["Outros_AC"] - eoep_dev_ini

    # ── Refs para interpolação ─────────────────────────────────────────────────
    eoep_dev_fin = ref["eoep_devedor"][2025]
    eoep_cred_fin = ref["eoep_credor"][2025]

    outros_pc_ini = b["passivo"]["Outros_PC"] - eoep_cred_ini
    outros_pc_fin = ref["outros_pc"][2025]

    inv_ini = b["ativo_corrente"]["Inventarios"]
    inv_fin = ref["inventarios"][2025]

    nc_ini = sched.financiamento["emprestimos_NC"][2024]
    nc_fin_r = ref["emprestimos_nc"][2025]

    c_ini = sched.financiamento["emprestimos_C"][2024]
    c_fin_r = ref["emprestimos_c"][2025]

    # ── Estado inicial: abertura 31 Dez 2024 ───────────────────────────────────
    aft_prev = b["ativo_nao_corrente"]["AFT_liquido"]
    intang_prev = b["ativo_nao_corrente"]["Intangiveis"]
    cli_prev = b["ativo_corrente"]["Clientes"]
    forn_prev = b["passivo"]["Fornecedores"]
    inv_prev = inv_ini
    eoep_dev_prev = eoep_dev_ini
    eoep_cred_prev = eoep_cred_ini
    outros_pc_prev = outros_pc_ini
    aplic_prev = 0.0
    linha_prev = 0.0
    caixa_prev = b["ativo_corrente"]["Caixa"]
    rl_acum = 0.0

    bs_rows: list[dict] = []
    dfc_rows: list[dict] = []

    for i, m in enumerate(MESES):
        dr = dr_map[m]
        t = t_map[m]
        fin = fin_m[m]
        cap = cap_m[m]

        dep_m = cap["dep_total"]
        juros_m = fin["juros"]
        capex_m = cap["capex_aft"] + cap["capex_int"]
        amort_m = fin["amortizacao"]

        # ── 1. Itens determinísticos do Balanço ───────────────────────────────
        aft_m = aft_prev + cap["capex_aft"] - cap["dep_aft"]
        intang_m = intang_prev + cap["capex_int"] - cap["dep_int"]

        aft_m = max(aft_m, 0.0)
        intang_m = max(intang_m, 0.0)

        inv_m = _interp(inv_ini, inv_fin, i)

        cli_m = (
            cli_prev
            + dr["vn"] * (1 + iva_venda)
            - t["recebimentos_clientes"]
        )

        eoep_dev_m = _interp(eoep_dev_ini, eoep_dev_fin, i)

        forn_m = (
            forn_prev
            + (dr["cmvmc"] + dr["fse"]) * (1 + iva_fse)
            - t["pagamentos_fornecedores"]
        )

        eoep_cred_m = _interp(eoep_cred_ini, eoep_cred_fin, i)
        outros_pc_m = _interp(outros_pc_ini, outros_pc_fin, i)

        nc_m = _interp(nc_ini, nc_fin_r, i)
        c_m = _interp(c_ini, c_fin_r, i)

        rl_acum += dr["rl"]
        cp_m = cp_fixo + rl_acum

        # ── 2. ΔNFM ───────────────────────────────────────────────────────────
        d_cli = -(cli_m - cli_prev)
        d_inv = -(inv_m - inv_prev)
        d_eoep_dev = -(eoep_dev_m - eoep_dev_prev)
        d_forn = forn_m - forn_prev
        d_eoep_cred = eoep_cred_m - eoep_cred_prev
        d_outros_pc = outros_pc_m - outros_pc_prev

        var_nfm = (
            d_cli
            + d_inv
            + d_eoep_dev
            + d_forn
            + d_eoep_cred
            + d_outros_pc
        )

        # ── 3. Fluxos base ────────────────────────────────────────────────────
        fluxo_op = dr["rl"] + dep_m + juros_m + var_nfm
        fluxo_inv_base = -capex_m
        fluxo_fin_base = -amort_m - juros_m
        var_caixa_base = fluxo_op + fluxo_inv_base + fluxo_fin_base

        # ── 4. Posição líquida disponível no fecho do mês ─────────────────────
        posicao_liq = caixa_prev + aplic_prev - linha_prev + var_caixa_base

        # ── 5. Decisão de gestão de caixa ─────────────────────────────────────
        if posicao_liq >= caixa_max:
            aplic_cp_m = posicao_liq - caixa_max
            linha_cp_m = 0.0
            caixa_m = caixa_max
        elif posicao_liq >= caixa_min:
            aplic_cp_m = 0.0
            linha_cp_m = 0.0
            caixa_m = posicao_liq
        else:
            aplic_cp_m = 0.0
            linha_cp_m = caixa_min - posicao_liq
            caixa_m = caixa_min

        # ── 6. Ajustes DFC: Δ Aplicações e Δ Linha CP ─────────────────────────
        d_aplic = -(aplic_cp_m - aplic_prev)
        d_linha = linha_cp_m - linha_prev

        fluxo_inv = fluxo_inv_base + d_aplic
        fluxo_fin = fluxo_fin_base + d_linha
        var_caixa = fluxo_op + fluxo_inv + fluxo_fin

        # ── 7. Reconciliação ──────────────────────────────────────────────────
        reconciliacao = round((caixa_prev + var_caixa) - caixa_m, 2)

        # ── Totais do Balanço ─────────────────────────────────────────────────
        anc_outros_m = anc_outros_base + intang_m
        total_anc = aft_m + anc_outros_m + impost_dif_a
        total_ac = aplic_cp_m + inv_m + cli_m + eoep_dev_m + outros_ac + caixa_m
        total_ativo = total_anc + total_ac

        total_passivo = (
            nc_m
            + c_m
            + impost_dif_p
            + forn_m
            + eoep_cred_m
            + outros_pc_m
            + linha_cp_m
        )

        total_cp_passivo = cp_m + total_passivo
        controlo = round(total_cp_passivo - total_ativo, 2)

        bs_rows.append(
            {
                "mes": m,
                "aft_liquido": round(aft_m),
                "anc_outros": round(anc_outros_m),
                "impost_dif_ativos": round(impost_dif_a),
                "total_anc": round(total_anc),
                "aplicacoes_fin_cp": round(aplic_cp_m),
                "inventarios": round(inv_m),
                "clientes": round(cli_m),
                "eoep_devedor": round(eoep_dev_m),
                "outros_ac": round(outros_ac),
                "caixa": round(caixa_m),
                "total_ac": round(total_ac),
                "total_ativo": round(total_ativo),
                "cp_fixo": round(cp_fixo),
                "rl_acumulado": round(rl_acum),
                "total_cp": round(cp_m),
                "emprestimos_nc": round(nc_m),
                "impost_dif_passivos": round(impost_dif_p),
                "emprestimos_c": round(c_m),
                "fornecedores": round(forn_m),
                "eoep_credor": round(eoep_cred_m),
                "outros_pc": round(outros_pc_m),
                "linha_credito_cp": round(linha_cp_m),
                "total_passivo": round(total_passivo),
                "total_cp_passivo": round(total_cp_passivo),
                "controlo": controlo,
                "_capex_m": round(capex_m),
                "_dep_m": round(dep_m),
                "_amort_m": round(amort_m),
                "_juros_m": round(juros_m),
                "_aplic_delta": round(aplic_cp_m - aplic_prev),
            }
        )

        dfc_rows.append(
            {
                "mes": m,
                "rl": round(dr["rl"]),
                "dep_amort": round(dep_m),
                "juros_add_back": round(juros_m),
                "var_clientes": round(d_cli),
                "var_inventarios": round(d_inv),
                "var_eoep_dev": round(d_eoep_dev),
                "var_fornecedores": round(d_forn),
                "var_eoep_cred": round(d_eoep_cred),
                "var_outros_pc": round(d_outros_pc),
                "var_nfm_total": round(var_nfm),
                "fluxo_operacional": round(fluxo_op),
                "capex": round(-capex_m),
                "var_aplic_cp": round(d_aplic),
                "fluxo_investimento": round(fluxo_inv),
                "amortizacoes": round(-amort_m),
                "juros_pagos": round(-juros_m),
                "var_linha_cp": round(d_linha),
                "fluxo_financiamento": round(fluxo_fin),
                "variacao_caixa": round(var_caixa),
                "caixa_abertura": round(caixa_prev),
                "caixa_fecho": round(caixa_m),
                "reconciliacao": reconciliacao,
            }
        )

        # ── Actualiza estado ───────────────────────────────────────────────────
        aft_prev = aft_m
        intang_prev = intang_m
        cli_prev = cli_m
        forn_prev = forn_m
        inv_prev = inv_m
        eoep_dev_prev = eoep_dev_m
        eoep_cred_prev = eoep_cred_m
        outros_pc_prev = outros_pc_m
        aplic_prev = aplic_cp_m
        linha_prev = linha_cp_m
        caixa_prev = caixa_m

    return pd.DataFrame(bs_rows), pd.DataFrame(dfc_rows)


# ──────────────────────────────────────────────────────────────────────────────
# Balanço Mensal
# ──────────────────────────────────────────────────────────────────────────────

def build_balanco_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    _df_dr_m: pd.DataFrame | None = None,
    _df_t_m: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Balanço mensal 2025, com Caixa derivada dos fluxos DFC."""
    if _df_dr_m is None:
        _df_dr_m = teso_mod.build_dr_mensal(a, base, sched)

    if _df_t_m is None:
        _df_t_m = teso_mod.build_tesouraria(a, base, sched)

    df_bs, _ = _build_integrated_monthly(a, base, sched, _df_dr_m, _df_t_m)
    return df_bs


# ──────────────────────────────────────────────────────────────────────────────
# DFC Mensal
# ──────────────────────────────────────────────────────────────────────────────

def build_dfc_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_bs: pd.DataFrame | None = None,
    df_dr_m: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """DFC mensal 2025 pelo método indireto, reconciliada com o Balanço.

    O parâmetro df_bs é aceite por compatibilidade, mas o cálculo integrado
    reconstrói internamente o Balanço e a DFC para garantir consistência.
    """
    if df_dr_m is None:
        df_dr_m = teso_mod.build_dr_mensal(a, base, sched)

    df_t_m = teso_mod.build_tesouraria(a, base, sched)

    _, df_dfc = _build_integrated_monthly(a, base, sched, df_dr_m, df_t_m)
    return df_dfc


# ──────────────────────────────────────────────────────────────────────────────
# NFM Mensal
# ──────────────────────────────────────────────────────────────────────────────

def build_nfm_mensal(
    df_bs: pd.DataFrame,
    df_dr_m: pd.DataFrame,
) -> pd.DataFrame:
    """NFM e Ciclo de Conversão de Caixa mensais, derivados do Balanço."""
    bs_map = df_bs.set_index("mes").to_dict("index")
    dr_map = df_dr_m.set_index("mes").to_dict("index")

    rows: list[dict] = []

    for m in MESES:
        bs = bs_map[m]
        dr = dr_map[m]

        vn_m = max(dr["vn"], 1)
        cmvmc_m = max(dr["cmvmc"], 1)
        fse_m = max(dr["fse"], 1)

        ac_cicl = bs["inventarios"] + bs["clientes"]
        pc_cicl = bs["fornecedores"] + bs["eoep_credor"]
        nfm_m = ac_cicl - pc_cicl

        pmr_eff = bs["clientes"] / vn_m * 30
        dmi_eff = bs["inventarios"] / cmvmc_m * 30
        pmp_eff = bs["fornecedores"] / (cmvmc_m + fse_m) * 30
        ccc_eff = pmr_eff + dmi_eff - pmp_eff

        rows.append(
            {
                "mes": m,
                "ativo_ciclico": round(ac_cicl),
                "inventarios": round(bs["inventarios"]),
                "clientes": round(bs["clientes"]),
                "passivo_ciclico": round(pc_cicl),
                "fornecedores": round(bs["fornecedores"]),
                "eoep_credor": round(bs["eoep_credor"]),
                "nfm": round(nfm_m),
                "pmr_eff": round(pmr_eff, 1),
                "dmi_eff": round(dmi_eff, 1),
                "pmp_eff": round(pmp_eff, 1),
                "ccc_eff": round(ccc_eff, 1),
            }
        )

    df = pd.DataFrame(rows)
    df["delta_nfm"] = df["nfm"].diff().fillna(0).round().astype(int)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Tesouraria Completa
# ──────────────────────────────────────────────────────────────────────────────

def build_tesouraria_completa(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_bs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tesouraria mensal completa: operacional + serviço dívida + CAPEX."""
    if df_bs is None:
        df_bs = build_balanco_mensal(a, base, sched)

    df_teso = teso_mod.build_tesouraria(a, base, sched)
    fin_m = _financiamento_mensal(sched)
    cap_m = _capex_mensal(sched)

    t_map = df_teso.set_index("mes").to_dict("index")
    bs_map = df_bs.set_index("mes").to_dict("index")

    caixa_prev = base.balanco["ativo_corrente"]["Caixa"]

    rows: list[dict] = []

    for m in MESES:
        t = t_map[m]
        bs = bs_map[m]
        fin = fin_m[m]
        cap = cap_m[m]

        rec = t["recebimentos_clientes"]
        pag_forn = t["pagamentos_fornecedores"]
        pag_pess = t["pagamentos_pessoal"]
        fluxo_fisc = t["fluxo_fiscal"]
        fluxo_op_b = t["fluxo_operacional_bruto"]
        fluxo_op_l = t["fluxo_liquido"]

        capex_pag = cap["capex_aft"] + cap["capex_int"]
        amort_pag = fin["amortizacao"]
        juros_pag = fin["juros"]

        fluxo_fin = -(amort_pag + juros_pag)

        var_total = fluxo_op_l - capex_pag + fluxo_fin
        caixa_bruta = caixa_prev + var_total

        linha_cp = bs["linha_credito_cp"]

        rows.append(
            {
                "mes": m,
                "recebimentos_clientes": round(rec),
                "pagamentos_fornecedores": round(pag_forn),
                "pagamentos_pessoal": round(pag_pess),
                "fluxo_operacional_bruto": round(fluxo_op_b),
                "iva_pago_estado": round(t["iva_pagamento_estado"]),
                "ss_pagamento": round(t["ss_pagamento"]),
                "irc_ppc": round(t["irc_ppc"]),
                "fluxo_fiscal": round(fluxo_fisc),
                "fluxo_operacional_liquido": round(fluxo_op_l),
                "capex_pagamento": round(-capex_pag),
                "amortizacoes": round(-amort_pag),
                "juros_pagos": round(-juros_pag),
                "fluxo_financiamento": round(fluxo_fin),
                "variacao_caixa_total": round(var_total),
                "caixa_abertura": round(caixa_prev),
                "caixa_antes_credito": round(caixa_bruta),
                "linha_credito_utilizada": round(linha_cp),
                "caixa_fecho": round(bs["caixa"]),
            }
        )

        caixa_prev = bs["caixa"]

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# Ponto de Entrada
# ──────────────────────────────────────────────────────────────────────────────

def build_rolling_forecast(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    ov: Optional[Dict[str, Any]] = None,
) -> dict:
    """Constrói todas as demonstrações mensais articuladas.

    Args:
        a: Assumptions com overrides já aplicados.
        base: Base2024.
        sched: Schedules.
        ov: Overrides do dashboard, aceite por compatibilidade.

    Returns:
        dict com:
        dr_mensal, balanco_mensal, dfc_mensal, nfm_mensal,
        tesouraria_completa.
    """
    df_dr = teso_mod.build_dr_mensal(a, base, sched)
    df_t = teso_mod.build_tesouraria(a, base, sched)

    # Único loop: DFC determina Caixa; Balanço fecha por construção
    df_bs, df_dfc = _build_integrated_monthly(a, base, sched, df_dr, df_t)

    df_nfm = build_nfm_mensal(df_bs, df_dr)
    df_tc = build_tesouraria_completa(a, base, sched, df_bs=df_bs)

    return {
        "dr_mensal": df_dr,
        "balanco_mensal": df_bs,
        "dfc_mensal": df_dfc,
        "nfm_mensal": df_nfm,
        "tesouraria_completa": df_tc,
    }