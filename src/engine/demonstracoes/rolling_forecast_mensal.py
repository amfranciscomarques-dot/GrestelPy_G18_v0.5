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
from ..modelo.eoep import _get_eoep_credor_2024
from ..operacional.clientes import iva_efetivo_vendas


# ──────────────────────────────────────────────────────────────────────────────
# Auxiliares internos
# ──────────────────────────────────────────────────────────────────────────────

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
# Hub Logístico: impacto mensal no Balanço e DFC
# ──────────────────────────────────────────────────────────────────────────────

def _hub_monthly_impact(a: Assumptions) -> dict | None:
    """Impacto mensal do Hub Logístico no Balanço e DFC de 2025.

    Retorna dict com:
      meses: {mes: {capex, juros_cap, juros_pagos, desembolso}}
      nc:    saldo NC hub constante (carência 2025-2027 → sem amortização)
      c:     saldo C hub constante em 2025
    None se hub desativado ou dados ausentes.

    Metodologia:
      • CAPEX mensal: perfil do cronograma_mensal do YAML → fluxo_investimento
      • Juros 2025 capitalizados (NCRF 10): aumentam custo do AFT, NÃO DR;
        são SEMPRE saída de caixa real (NCRF 2 §33b) → fluxo_financiamento
      • Desembolso bancário: Janeiro 2025 (única entrada) → fluxo_financiamento
      • NC/C constantes em 2025 (sem amortização durante a carência)
    """
    raw_hub = a.raw.get("hub_logistico", {})
    if not raw_hub.get("incluir_hub", False):
        return None

    try:
        from ..projetos import hub_logistico as hub_mod

        df_fin = hub_mod.hub_financing(raw_hub)
        jc_map = hub_mod._juros_capitalizados_map(raw_hub)

        fin_2025 = df_fin[df_fin.ano == 2025].iloc[0]
        hub_nc         = float(fin_2025["emprestimos_nc"])
        hub_c          = float(fin_2025["emprestimos_c"])
        hub_desembolso = float(fin_2025["desembolso"])
        hub_juros_anual = float(fin_2025["juros"])  # total cash outflow

        juros_m = hub_juros_anual / 12.0
        jc_m    = jc_map.get(2025, 0.0) / 12.0  # capitalizado → aumenta AFT

        # CAPEX mensal do cronograma (lowercase → MESES capitalizados)
        cron_proj = raw_hub.get("projeto_hub", {}).get("cronograma_mensal", {})
        cron_2025 = cron_proj.get("2025", cron_proj.get(2025, {}))
        _lower = {m.lower(): m for m in MESES}
        capex_por_mes: dict[str, float] = {m: 0.0 for m in MESES}
        for k, v in cron_2025.items():
            mes = _lower.get(str(k).lower())
            if mes:
                capex_por_mes[mes] = float(v)

        # Normalizar para que o total mensal coincida com o CAPEX anual.
        # cronograma_mensal define o perfil de obra mas o total deve fechar
        # com o cronograma anual usado no Balanco/DFC anual (articulacao M3-M6).
        df_cap_hub = hub_mod.hub_capex(raw_hub)
        _cap_2025_row = df_cap_hub[df_cap_hub.ano == 2025]
        capex_anual_2025 = float(_cap_2025_row["capex"].iloc[0]) if not _cap_2025_row.empty else 0.0
        _total_mes = sum(capex_por_mes.values())
        if _total_mes > 0 and abs(_total_mes - capex_anual_2025) > 1.0:
            _fct = capex_anual_2025 / _total_mes
            capex_por_mes = {m: v * _fct for m, v in capex_por_mes.items()}

        meses_data = {
            m: {
                "capex":       capex_por_mes[m],
                "juros_cap":   jc_m,
                "juros_pagos": juros_m,
                "desembolso":  hub_desembolso if i == 0 else 0.0,
            }
            for i, m in enumerate(MESES)
        }
        return {"meses": meses_data, "nc": hub_nc, "c": hub_c}

    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Loop Integrado: DFC determina Caixa; Balanço fecha por construção
# ──────────────────────────────────────────────────────────────────────────────

def _build_integrated_monthly(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_dr_m: pd.DataFrame,
    df_t_m: pd.DataFrame,
    anual_ref: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Loop mensal integrado: DFC determina Caixa; Balanço fecha naturalmente.

    Args:
        anual_ref: valores do modelo anual 2025 (live) para ancoragem.
            Chaves usadas: inventarios, outros_pc, clientes, fornecedores,
            subs_2025, rend_equiv_2025, dividendos_2025.
            Se None, usa reference_balanco do schedules.yaml e sem ajustes.

    Retorna:
        tuple[pd.DataFrame, pd.DataFrame]: df_balanco, df_dfc.
    """
    caixa_min = a.caixa["minima"]
    caixa_max = a.caixa["maxima"]
    iva_venda = iva_efetivo_vendas(a)
    iva_fse = a.impostos.get("IVA_FSE", 0.15)

    fin_m = _financiamento_mensal(sched)
    cap_m = _capex_mensal(sched)
    dr_map = df_dr_m.set_index("mes").to_dict("index")
    t_map = df_t_m.set_index("mes").to_dict("index")

    b = base.balanco
    ref = sched.reference_balanco

    # ── Constantes ─────────────────────────────────────────────────────────────
    # Subsidiárias: interpoladas linearmente 2024→2025 usando schedules.yaml.
    # Não requer modelo anual externo — valores pré-calculados no schedule.
    subs_ini = float(b["ativo_nao_corrente"]["Subsidiarias"])
    _inv_s        = sched.investimento
    _rend_eq_2025 = float(_inv_s.get("rend_equiv_patrimonial", {}).get(2025, 0.0))
    _div_2025     = float(_inv_s.get("dividendos_recebidos",   {}).get(2025, 0.0))
    subs_fin      = subs_ini + _rend_eq_2025 - _div_2025

    # DFC — ajustes pelo método indireto para rendimentos não-monetários:
    #   rend_equiv_m : incluído no RL mas não é caixa → subtrai de fluxo_op
    #   dividendos_m : caixa real recebido das subsidiárias → fluxo_inv
    rend_equiv_m = _rend_eq_2025 / 12.0
    dividendos_m = _div_2025 / 12.0

    anc_outros_nosubs = (
        b["ativo_nao_corrente"]["Goodwill"]
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
    outros_pc_fin = (
        float(anual_ref["outros_pc"])
        if anual_ref and "outros_pc" in anual_ref
        else outros_pc_ini
    )

    inv_ini = b["ativo_corrente"]["Inventarios"]
    inv_fin = (
        float(anual_ref["inventarios"])
        if anual_ref and "inventarios" in anual_ref
        else ref["inventarios"][2025]
    )

    nc_ini   = sched.financiamento["emprestimos_NC"][2024]
    nc_fin_r = sched.financiamento["emprestimos_NC"][2025]  # core live, sem hub

    c_ini   = sched.financiamento["emprestimos_C"][2024]
    c_fin_r = sched.financiamento["emprestimos_C"][2025]    # core live, sem hub

    # ── Hub: impacto mensal (None se desativado) ───────────────────────────────
    hub_impact = _hub_monthly_impact(a)
    hub_nc = float(hub_impact["nc"]) if hub_impact else 0.0
    hub_c  = float(hub_impact["c"])  if hub_impact else 0.0

    # ── Estado inicial: abertura 31 Dez 2024 ───────────────────────────────────
    aft_core_prev = b["ativo_nao_corrente"]["AFT_liquido"]
    aft_hub_cum   = 0.0  # acumula CAPEX hub + juros capitalizados (NCRF 10)
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

        dep_m   = cap["dep_total"]
        juros_m = fin["juros"]
        amort_m = fin["amortizacao"]

        # ── Hub: fluxos do mês ────────────────────────────────────────────────
        hub_m            = hub_impact["meses"][m] if hub_impact else {}
        hub_capex_m      = float(hub_m.get("capex",       0.0))
        hub_jc_m         = float(hub_m.get("juros_cap",   0.0))
        hub_juros_pag_m  = float(hub_m.get("juros_pagos", 0.0))
        hub_desembolso_m = float(hub_m.get("desembolso",  0.0))

        # CAPEX total do mês (core Grestel + hub) — para DFC fluxo_investimento
        capex_m = cap["capex_aft"] + cap["capex_int"] + hub_capex_m

        # ── 1. Itens determinísticos do Balanço ───────────────────────────────
        # AFT core (Grestel) — evolução autónoma independente do hub
        aft_core_m = aft_core_prev + cap["capex_aft"] - cap["dep_aft"]
        aft_core_m = max(aft_core_m, 0.0)
        # AFT hub: acumula CAPEX (saída caixa) + juros capitalizados (NCRF 10)
        # Sem depreciação em 2025 — hub entra em exploração em 2026
        aft_hub_cum += hub_capex_m + hub_jc_m
        aft_m = aft_core_m + aft_hub_cum

        intang_m = intang_prev + cap["capex_int"] - cap["dep_int"]
        intang_m = max(intang_m, 0.0)

        subs_m = _interp(subs_ini, subs_fin, i)

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

        # Ancoragem de Dezembro: clientes e fornecedores forçados ao valor anual.
        # A diferença metodológica (DFC-first PMR cash vs. PMR/365 ratio) flui
        # integralmente por var_nfm → var_caixa → caixa_m (DFC-first preservado).
        if anual_ref is not None and m == "Dez":
            cli_m  = float(anual_ref.get("clientes",     cli_m))
            forn_m = float(anual_ref.get("fornecedores", forn_m))

        eoep_cred_m = _interp(eoep_cred_ini, eoep_cred_fin, i)
        outros_pc_m = _interp(outros_pc_ini, outros_pc_fin, i)

        # NC/C: core Grestel (interpolação) + hub (constante, carência 2025-2027)
        nc_m = _interp(nc_ini, nc_fin_r, i) + hub_nc
        c_m  = _interp(c_ini,  c_fin_r,  i) + hub_c

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
        # rend_equiv_patrimonial é não-monetário: incluso no RL (via outros_ebitda_m)
        # mas não gera caixa — subtrai do fluxo_op (NCRF 2 método indireto).
        # Dividendos recebidos são caixa real das subsidiárias → fluxo_investimento.
        fluxo_op = dr["rl"] + dep_m + juros_m - rend_equiv_m + var_nfm
        fluxo_inv_base = -capex_m + dividendos_m
        # Hub: desembolso bancário (entrada Jan) − juros totais pagos (saída mensal)
        # Os juros hub são sempre saída de caixa real (NCRF 2 §33b), mesmo
        # os capitalizados no AFT (NCRF 10) — distinção contabilística, não financeira.
        fluxo_fin_base = -amort_m - juros_m + hub_desembolso_m - hub_juros_pag_m
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
        anc_outros_m = anc_outros_nosubs + subs_m + intang_m
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
                "dividendos_recebidos": round(dividendos_m),
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
        aft_core_prev = aft_core_m  # hub acumula em aft_hub_cum (fora deste campo)
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
    """DFC mensal 2025 pelo método indireto, reconciliada com o Balanço."""
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
# Reconciliação Mensal-Anual
# ──────────────────────────────────────────────────────────────────────────────

def build_reconciliacao_mensal_anual(
    a: "Assumptions",
    base: "Base2024",
    df_bs: pd.DataFrame,
    df_dr_m: pd.DataFrame,
    df_dfc_m: pd.DataFrame,
    sched: Schedules,
    stmt: dict | None = None,
) -> dict:
    """Compara o fecho de Dezembro do loop mensal com o modelo anual 2025 (live).

    A referência anual é o modelo anual calculado on-the-fly (via build_statements
    se stmt não for passado), garantindo que compara sempre contra o modelo atual.

    Desvio = mensal − anual. Zero significa articulação perfeita.

    Args:
        stmt: resultado de build_statements() pré-calculado (evita double call).
              Se None, calcula internamente.

    Returns:
        dict com três secções:
          balanco_dezembro  — itens do Balanço em Dez vs Balanço anual 2025
          dr_soma_vs_anual  — soma dos 12 meses do DR vs DR anual 2025
          dfc_consolidado   — fluxos acumulados e reconciliação de Caixa
    """
    if stmt is None:
        from .statements import build_statements
        stmt = build_statements(a, base, sched)

    df_bs_anual = stmt["balanco"]
    df_dr_anual = stmt["dr"]

    anual_b = df_bs_anual[df_bs_anual["ano"] == 2025].iloc[0]
    anual_dr = df_dr_anual[df_dr_anual["ano"] == 2025].iloc[0]

    dez = df_bs[df_bs["mes"] == "Dez"].iloc[0]

    def _it(mensal_val: float, ref_val: float) -> dict:
        return {
            "mensal": round(mensal_val),
            "ref_anual": round(ref_val),
            "desvio": round(mensal_val - ref_val),
        }

    # ── Balanço: fecho de Dezembro vs Balanço anual 2025 ─────────────────────
    balanco = {
        "aft_liquido":      _it(dez["aft_liquido"],      float(anual_b["aft_liquido"])),
        "inventarios":      _it(dez["inventarios"],      float(anual_b["inventarios"])),
        "clientes":         _it(dez["clientes"],         float(anual_b["clientes"])),
        "eoep_devedor":     _it(dez["eoep_devedor"],     float(anual_b["eoep_devedor"])),
        "caixa":            _it(dez["caixa"],            float(anual_b["caixa"])),
        "total_ac":         _it(dez["total_ac"],         float(anual_b["total_ac"])),
        "total_anc":        _it(dez["total_anc"],        float(anual_b["total_anc"])),
        "total_ativo":      _it(dez["total_ativo"],      float(anual_b["total_ativo"])),
        "total_cp":         _it(dez["total_cp"],         float(anual_b["total_cp"])),
        "emprestimos_nc":   _it(dez["emprestimos_nc"],   float(anual_b["emprestimos_nc"])),
        "emprestimos_c":    _it(dez["emprestimos_c"],    float(anual_b["emprestimos_c"])),
        "fornecedores":     _it(dez["fornecedores"],     float(anual_b["fornecedores"])),
        "eoep_credor":      _it(dez["eoep_credor"],      float(anual_b["eoep_credor"])),
        "outros_pc":        _it(dez["outros_pc"],        float(anual_b["outros_pc"])),
        "linha_credito_cp": _it(dez["linha_credito_cp"], float(anual_b["linha_credito_cp"])),
        "total_passivo":    _it(dez["total_passivo"],    float(anual_b["total_passivo"])),
    }

    # ── DR: soma 12 meses vs DR anual 2025 ────────────────────────────────────
    # No DR anual, custos são negativos; no DR mensal, custos são positivos.
    # Negamos os custos do DR anual para comparar na mesma escala.
    dr_soma = df_dr_m[["vn", "cmvmc", "fse", "gastos_pessoal", "ebitda",
                        "depreciacoes", "ebit", "juros", "rl"]].sum()
    dr = {
        "vn":             _it(dr_soma["vn"],             float(anual_dr["vn"])),
        "cmvmc":          _it(dr_soma["cmvmc"],          -float(anual_dr["cmvmc"])),
        "fse":            _it(dr_soma["fse"],            -float(anual_dr["fse"])),
        "gastos_pessoal": _it(dr_soma["gastos_pessoal"], -float(anual_dr["gastos_pessoal"])),
        "ebitda":         _it(dr_soma["ebitda"],         float(anual_dr["ebitda"])),
        "depreciacoes":   _it(dr_soma["depreciacoes"],   -float(anual_dr["depreciacoes"])),
        "ebit":           _it(dr_soma["ebit"],           float(anual_dr["ebit"])),
        "juros":          _it(dr_soma["juros"],          -float(anual_dr["juros"])),
        "rl":             _it(dr_soma["rl"],             float(anual_dr["rl"])),
    }

    # ── DFC: fluxos acumulados e reconciliação de Caixa ───────────────────────
    dfc_soma = df_dfc_m[
        ["fluxo_operacional", "fluxo_investimento", "fluxo_financiamento", "variacao_caixa"]
    ].sum()

    caixa_ini = int(df_dfc_m["caixa_abertura"].iloc[0])
    caixa_fim = int(df_dfc_m["caixa_fecho"].iloc[-1])

    dfc = {
        "fluxo_operacional":    round(dfc_soma["fluxo_operacional"]),
        "fluxo_investimento":   round(dfc_soma["fluxo_investimento"]),
        "fluxo_financiamento":  round(dfc_soma["fluxo_financiamento"]),
        "variacao_caixa_total": round(dfc_soma["variacao_caixa"]),
        "caixa_abertura_jan":   caixa_ini,
        "caixa_fecho_dez":      caixa_fim,
        "ref_caixa_dez_anual":  round(float(anual_b["caixa"])),
        "desvio_caixa":         caixa_fim - round(float(anual_b["caixa"])),
    }

    return {
        "balanco_dezembro": balanco,
        "dr_soma_vs_anual": dr,
        "dfc_consolidado": dfc,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Opção B — overlay mensal Dezembro → Balanço anual 2025
# ──────────────────────────────────────────────────────────────────────────────

def _overlay_dez_mensal_no_anual(
    df_bs_mensal: pd.DataFrame,
    df_balanco_anual: pd.DataFrame,
) -> pd.DataFrame:
    """Substitui a linha 2025 do Balanço anual pelos valores de Dezembro do mensal.

    Implementa Option B: M3 DFC-first é a fonte de verdade para 2025.
    As linhas 2026-2029 ficam inalteradas mas o DFC anual passará a usar os
    valores mensais como fecho de 2025 (abertura de 2026), propagando M3→M6→OE4.

    Colunas com breakdown detalhado de CP e ANC (goodwill, reservas, etc.)
    mantêm-se do modelo anual — só os totais e os itens NFM/caixa são
    substituídos pelo mensal.
    """
    dez = df_bs_mensal[df_bs_mensal["mes"] == "Dez"].iloc[0]

    # Colunas NFM + caixa + financiamento + totais — computadas pelo DFC-first
    _OVERLAY = [
        "aft_liquido", "total_anc",
        "aplicacoes_fin_cp", "inventarios", "clientes",
        "eoep_devedor", "outros_ac", "caixa",
        "total_ac", "total_ativo",
        "total_cp",
        "emprestimos_nc", "emprestimos_c",
        "fornecedores", "eoep_credor", "outros_pc",
        "linha_credito_cp", "total_passivo", "total_cp_passivo",
    ]

    df = df_balanco_anual.copy()
    mask = df["ano"] == 2025
    for col in _OVERLAY:
        if col in dez.index and col in df.columns:
            df.loc[mask, col] = float(dez[col])

    df.loc[mask, "controlo"] = (
        df.loc[mask, "total_cp_passivo"] - df.loc[mask, "total_ativo"]
    )
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Ponto de Entrada
# ──────────────────────────────────────────────────────────────────────────────

def build_rolling_forecast(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    ov: Optional[Dict[str, Any]] = None,
) -> dict:
    """Constrói todas as demonstrações mensais articuladas (M3) e propaga para M6/OE4.

    Fluxo Option B — M3 → M6 → OE4:
      1. Modelo mensal DFC-first — fonte de verdade para 2025
      2. Modelo anual DR + Balanço + DFC construídos independentemente
      3. Linha 2025 do Balanço anual substituída pelo fecho de Dezembro mensal
      4. DFC anual reconstruída com o Balanço híbrido — 2026-2029 usam o
         fecho mensal de 2025 como abertura, propagando M3 → M6 → OE4
    """
    from .dr import build_dr as _build_dr_anual
    from .balanco import build_balanco as _build_balanco_anual
    from .dfc import build_dfc as _build_dfc_anual

    # ── 1. Modelo mensal DFC-first ────────────────────────────────────────────
    df_dr = teso_mod.build_dr_mensal(a, base, sched)
    df_t  = teso_mod.build_tesouraria(a, base, sched)
    df_bs, df_dfc = _build_integrated_monthly(a, base, sched, df_dr, df_t)

    df_nfm = build_nfm_mensal(df_bs, df_dr)
    df_tc  = build_tesouraria_completa(a, base, sched, df_bs=df_bs)

    # ── 2. Modelo anual independente (DR → Balanço → DFC) ────────────────────
    df_dr_anual     = _build_dr_anual(a, base, sched)
    df_bs_anual_raw = _build_balanco_anual(a, base, sched, df_dr_anual)

    # ── 3. Opção B: fecho Dez mensal ancora Balanço anual 2025 ───────────────
    df_bs_hibrido = _overlay_dez_mensal_no_anual(df_bs, df_bs_anual_raw)

    # ── 4. DFC anual reconstruída — 2026-2029 partem do fecho mensal 2025 ────
    df_dfc_anual = _build_dfc_anual(a, df_dr_anual, df_bs_hibrido, sched, base)

    stmt_m6 = {
        "dr":      df_dr_anual,
        "balanco": df_bs_hibrido,
        "dfc":     df_dfc_anual,
    }

    # ── 5. Reconciliação DR/DFC (Balanço Dez = anual 2025 por construção) ────
    reconciliacao = build_reconciliacao_mensal_anual(
        a, base, df_bs, df_dr, df_dfc, sched, stmt=stmt_m6
    )

    return {
        "dr_mensal":           df_dr,
        "balanco_mensal":      df_bs,
        "dfc_mensal":          df_dfc,
        "nfm_mensal":          df_nfm,
        "tesouraria_completa": df_tc,
        "reconciliacao_anual": reconciliacao,
        "stmt_m6":             stmt_m6,
    }