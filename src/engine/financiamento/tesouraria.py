"""Orçamento de Tesouraria Mensal — ano 2025 (M3).

Exigência do manual da UC PEF 2025-26: o Momento 3 deve ter base mensal
para o curto prazo (primeiro ano de projeção), com suporte a rolling forecast.

Metodologia:
  • Recebimentos de clientes: VN mensal × (1 + IVA) com desfasagem PMR
    (encaixe no mês M + floor(PMR/30))
  • Pagamentos a fornecedores: (CMVMC + FSE) mensais × (1 + IVA) com desfasagem PMP
  • Pagamentos de pessoal: gastos mensais × (1 + TSU_empresa) no próprio mês
  • IVA: liquidado - dedutível, pago no mês M+2 (regime mensal CIVA art.27)
  • SS: TSU empresa, pago no mês M+1
  • IRC — Pagamentos Por Conta: 76,5% × IRC_2024 ÷ 3 em Jul, Set, Dez

Rolling forecast: o parâmetro `meses_realizados` permite substituir estimativas
mensais por valores reais para os meses já decorridos, recalculando os restantes.

Funções exportadas:
  build_tesouraria_mensal(a, base, sched) → pd.DataFrame  (12 meses × ~20 colunas)
  rolling_update(df_original, realizados)  → pd.DataFrame  (substitui meses realizados)
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, MESES
from ..operacional import vendas as vendas_mod
from ..operacional.clientes import iva_efetivo_vendas
from ..operacional import cmvmc as cmvmc_mod
from ..operacional import fse as fse_mod
from ..operacional import pessoal as pessoal_mod
from ..modelo import eoep as eoep_mod
from ..demonstracoes import dr as stmt_mod


def _get_irc_2024(base: Base2024) -> float:
    """Obtém o IRC real de 2024 a partir do YAML/base2024, com fallback seguro.

    O diagnóstico identificava o IRC 2024 como valor hardcoded neste módulo.
    Esta função tenta primeiro ler de base.raw["dr_2024_real"]["irc"].
    """
    try:
        return float(base.raw["dr_2024_real"]["irc"])
    except (AttributeError, KeyError, TypeError, ValueError):
        return 127272.29


def _dist_sazonal_vn_weighted(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> dict[str, float]:
    """Distribuição sazonal das vendas de 2025 ponderada pelo VN real por mercado.

    Aceita sazonalidade em formato dict ou list.
    """
    from ..operacional.vendas import _saz_to_dict

    df_prod = vendas_mod.vendas_anuais(a, base, sched)
    df_merc = vendas_mod.vendas_mercadorias_anuais(a, base)
    df_total = vendas_mod.resumo_anual(df_prod, df_merc)

    vn_total_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])

    if vn_total_2025 == 0:
        return {m: 1.0 / 12 for m in MESES}

    saz_raw = a.sazonalidade

    saz = {
        "PT": _saz_to_dict(saz_raw.get("PT", [])),
        "UE": _saz_to_dict(saz_raw.get("UE", [])),
        "USA": _saz_to_dict(saz_raw.get("USA", [])),
        "ROW": _saz_to_dict(saz_raw.get("ROW", [])),
    }

    df_2025 = df_prod[df_prod.ano == 2025].copy()

    vn_by_mkt: dict[str, float] = {}

    for mkt in ("PT", "UE", "USA", "ROW"):
        vn_by_mkt[mkt] = float(df_2025[df_2025["mercado"] == mkt]["vn"].sum())

    vn_ext = float(df_2025[df_2025["mercado"].isin(["EXT", "EXTERNO"])]["vn"].sum())

    if vn_ext:
        mercados = a.mercados or {}
        usa_w = float(mercados.get("USA", {}).get("peso_global", 0.0))
        row_w = float(mercados.get("ROW", {}).get("peso_global", 0.0))
        total_ext_w = usa_w + row_w

        if total_ext_w > 0:
            vn_by_mkt["USA"] += vn_ext * usa_w / total_ext_w
            vn_by_mkt["ROW"] += vn_ext * row_w / total_ext_w
        else:
            vn_by_mkt["USA"] += vn_ext * 0.5
            vn_by_mkt["ROW"] += vn_ext * 0.5

    df_merc_2025 = df_merc[df_merc.ano == 2025]
    vn_by_mkt["PT"] += float(df_merc_2025["vn"].sum())

    total_mkt = sum(vn_by_mkt.values()) or 1.0

    dist: dict[str, float] = {}

    for m in MESES:
        dist[m] = (
            vn_by_mkt["PT"] * saz["PT"][m]
            + vn_by_mkt["UE"] * saz["UE"][m]
            + vn_by_mkt["USA"] * saz["USA"][m]
            + vn_by_mkt["ROW"] * saz["ROW"][m]
        ) / total_mkt

    total = sum(dist.values())

    if total > 0:
        return {
            m: v / total
            for m, v in dist.items()
        }

    return {m: 1.0 / 12 for m in MESES}

def _dist_sazonal_total(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> dict[str, float]:
    """Delegação para a função ponderada, mantida por compatibilidade."""
    return _dist_sazonal_vn_weighted(a, base, sched)


def _mes_recebimento(mes_venda: str, pmr_dias: float) -> str | None:
    """Devolve o mês de encaixe dado PMR em dias, com desfasagem em meses inteiros."""
    desfasagem = max(0, round(pmr_dias / 30))
    idx_venda = MESES.index(mes_venda)
    idx_enc = idx_venda + desfasagem

    if idx_enc < len(MESES):
        return MESES[idx_enc]

    return None  # encaixe no ano seguinte — fora do horizonte 2025


def _mes_pagamento(mes_custo: str, pmp_dias: float) -> str | None:
    """Devolve o mês de pagamento dado PMP em dias."""
    desfasagem = max(0, round(pmp_dias / 30))
    idx_custo = MESES.index(mes_custo)
    idx_pag = idx_custo + desfasagem

    if idx_pag < len(MESES):
        return MESES[idx_pag]

    return None


def _build_mensais_2025(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> tuple[dict, dict, dict, dict, float]:
    """Calcula os vectores mensais 2025 partilhados por várias funções.

    Returns:
        (vn_m, fse_m, cmvmc_m, pessoal_m, irc_2024)
    """
    irc_2024 = _get_irc_2024(base)

    df_prod = vendas_mod.vendas_anuais(a, base, sched)
    df_merc = vendas_mod.vendas_mercadorias_anuais(a, base)
    df_total = vendas_mod.resumo_anual(df_prod, df_merc)

    vn_2024 = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])
    factor_vn = vn_2025 / vn_2024 if vn_2024 > 0 else 1.0

    df_fse = fse_mod.fse_anual(a, base, factor_vn)
    df_pessoal = pessoal_mod.pessoal_anual(a, base, df_total)
    df_cmvmc = cmvmc_mod.cmvmc_anual(a, base, df_prod, df_merc)

    fse_2025 = float(df_fse[df_fse.ano == 2025]["fse"].iloc[0])
    pessoal_2025 = float(df_pessoal[df_pessoal.ano == 2025]["gastos_pessoal"].iloc[0])
    cmvmc_2025 = float(df_cmvmc[df_cmvmc.ano == 2025]["cmvmc"].iloc[0])

    dist_saz = _dist_sazonal_total(a, base, sched)

    vn_m = {m: vn_2025 * dist_saz[m] for m in MESES}
    fse_m = {m: fse_2025 * dist_saz[m] for m in MESES}
    cmvmc_m = {m: cmvmc_2025 * dist_saz[m] for m in MESES}

    pessoal_m = {m: pessoal_2025 / 14.0 for m in MESES}
    pessoal_m["Jun"] = pessoal_2025 / 14.0 * 2
    pessoal_m["Nov"] = pessoal_2025 / 14.0 * 2

    return vn_m, fse_m, cmvmc_m, pessoal_m, irc_2024


def build_eoep_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Calendário fiscal mensal de 2025 (IVA, SS, IRC PPC).

    Returns:
        DataFrame com 12 linhas × colunas de eoep_calendario_mensal.
    """
    vn_m, fse_m, cmvmc_m, pessoal_m, irc_2024 = _build_mensais_2025(a, base, sched)
    return eoep_mod.eoep_calendario_mensal(
        a, base,
        vn_mensal=vn_m,
        fse_mensal=fse_m,
        pessoal_mensal=pessoal_m,
        irc_2024_pago=irc_2024,
        cmvmc_mensal=cmvmc_m,
    )


def build_tesouraria_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Orçamento de Tesouraria mensal de 2025.

    Returns:
        DataFrame com 12 linhas, uma por mês, incluindo:
        recebimentos_clientes, pagamentos_fornecedores, pagamentos_pessoal,
        iva_pagamento_estado, ss_pagamento, irc_ppc, total_saidas_fiscais,
        fluxo_operacional_bruto, fluxo_liquido e saldo_caixa_acumulado.
    """
    pmr = a.prazos["PMR_dias"]
    pmp = a.prazos["PMP_Inventarios_dias"]
    iva_venda = iva_efetivo_vendas(a)
    iva_fse = a.impostos.get("IVA_FSE", 0.15)
    tsu_emp = a.impostos["TSU_Empresa"]

    vn_m, fse_m, cmvmc_m, pessoal_m, irc_2024 = _build_mensais_2025(a, base, sched)

    df_eoep_cal = eoep_mod.eoep_calendario_mensal(
        a, base,
        vn_mensal=vn_m,
        fse_mensal=fse_m,
        pessoal_mensal=pessoal_m,
        irc_2024_pago=irc_2024,
        cmvmc_mensal=cmvmc_m,
    )
    eoep_map = df_eoep_cal.set_index("mes").to_dict("index")

    # ----------------------------------------------------------------
    # Recebimentos de clientes: VN + IVA, desfasado por PMR
    # ----------------------------------------------------------------
    rec_clientes: dict[str, float] = {m: 0.0 for m in MESES}

    # Saldo inicial de clientes em Jan/2025 = saldo final de 2024
    saldo_cli_abertura = base.balanco["ativo_corrente"]["Clientes"]

    # Simplificação: encaixar o saldo inicial em Jan e Fev
    rec_clientes["Jan"] += saldo_cli_abertura * 0.55
    rec_clientes["Fev"] += saldo_cli_abertura * 0.45

    for m in MESES:
        mes_enc = _mes_recebimento(m, pmr)
        if mes_enc:
            rec_clientes[mes_enc] += vn_m[m] * (1 + iva_venda)

    # ----------------------------------------------------------------
    # Pagamentos a fornecedores: CMVMC + FSE + IVA, desfasado por PMP
    # ----------------------------------------------------------------
    pag_forn: dict[str, float] = {m: 0.0 for m in MESES}

    # Saldo inicial de fornecedores em Jan/2025
    saldo_forn_abertura = base.balanco["passivo"]["Fornecedores"]
    pag_forn["Jan"] += saldo_forn_abertura * 0.60
    pag_forn["Fev"] += saldo_forn_abertura * 0.40

    for m in MESES:
        mes_pag = _mes_pagamento(m, pmp)
        if mes_pag:
            pag_forn[mes_pag] += (cmvmc_m[m] + fse_m[m]) * (1 + iva_fse)

    # ----------------------------------------------------------------
    # Pagamentos de pessoal, incluindo TSU da entidade patronal
    # ----------------------------------------------------------------
    pag_pessoal: dict[str, float] = {m: 0.0 for m in MESES}
    for m in MESES:
        pag_pessoal[m] = pessoal_m[m] * (1 + tsu_emp)

    # ----------------------------------------------------------------
    # Saldo inicial de caixa: 31/Dez/2024
    # ----------------------------------------------------------------
    caixa_inicial = base.balanco["ativo_corrente"]["Caixa"]

    # ----------------------------------------------------------------
    # Consolidação mensal
    #
    # saldo_caixa_acumulado[M] = saldo_caixa_acumulado[M-1] + fluxo_liquido[M]
    #
    # fluxo_liquido  = fluxo_operacional_bruto + fluxo_fiscal
    #   fluxo_op     = recebimentos_clientes
    #                  − pagamentos_fornecedores   (CMVMC+FSE+IVA, desfasado PMP)
    #                  − pagamentos_pessoal        (salários+TSU, mês corrente)
    #   fluxo_fiscal = −(IVA_pago_estado + SS_pago + IRC_PPC)
    #                   IVA: saldo do período M-2, regime mensal CIVA art.27
    #                   SS:  TSU patronal do período M-1
    #                   IRC_PPC: parcelas Jul/Set/Dez = 76,5% × IRC_2024 ÷ 3
    #
    # Nota: o IVA já está embutido nos recebimentos (VN × (1+IVA)) e nos
    # pagamentos (CMVMC+FSE × (1+IVA)); o fluxo_fiscal representa apenas
    # o acerto/liquidação líquida com o Estado no mês de pagamento.
    # ----------------------------------------------------------------
    rows = []
    saldo_acum = caixa_inicial

    for m in MESES:
        e = eoep_map[m]

        ss_p = e["ss_pagamento_mes"]
        irc_p = e["irc_ppc_mes"]

        rec = rec_clientes[m]
        pag_f = pag_forn[m]
        pag_p = pag_pessoal[m]

        iva_saldo_periodo = e["iva_saldo_periodo"]
        iva_pago_estado = e["iva_pagamento_mes"]  # saldo do período M-2, pago em M

        total_fiscal = iva_pago_estado + ss_p + irc_p

        fluxo_op = rec - pag_f - pag_p
        fluxo_fiscal = -total_fiscal
        fluxo_liquido = fluxo_op + fluxo_fiscal
        saldo_acum += fluxo_liquido

        rows.append(
            {
                "mes": m,
                "recebimentos_clientes": round(rec),
                "pagamentos_fornecedores": round(pag_f),
                "pagamentos_pessoal": round(pag_p),
                "fluxo_operacional_bruto": round(fluxo_op),
                "iva_liquidado_periodo": round(e["iva_liquidado"]),
                "iva_dedutivel_periodo": round(e["iva_dedutivel"]),
                "iva_saldo_periodo": round(iva_saldo_periodo),
                "iva_pagamento_estado": round(iva_pago_estado),
                "ss_pagamento": round(ss_p),
                "irc_ppc": round(irc_p),
                "total_saidas_fiscais": round(total_fiscal),
                "fluxo_fiscal": round(fluxo_fiscal),
                "fluxo_liquido": round(fluxo_liquido),
                "saldo_caixa_acumulado": round(saldo_acum),
            }
        )

    return pd.DataFrame(rows)


def build_dr_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Demonstração de Resultados mensal de 2025.

    Distribui os valores anuais de 2025 pela sazonalidade ponderada.
    Depreciações e juros são distribuídos uniformemente, 1/12 cada.

    Columns:
        mes, vn, cmvmc, margem_bruta, fse, gastos_pessoal,
        ebitda, depreciacoes, ebit, juros, rai, irc, rl.
    """
    from ..demonstracoes import statements
    from ..operacional import fse

    # Rubricas detalhadas de FSE (derivadas do base2024.yaml via fse_detalhe_2024)
    # e disponibilizadas como colunas adicionais no DR mensal.
    rubricas_fse = list(fse_mod.FSE_DETALHE_KEYS.keys())
    rub_col = fse_mod.FSE_DETALHE_KEYS  # YAML rubrica -> coluna

    # Anuais 2025 — reutiliza módulos individuais
    df_prod = vendas_mod.vendas_anuais(a, base, sched)
    df_merc = vendas_mod.vendas_mercadorias_anuais(a, base)
    df_total = vendas_mod.resumo_anual(df_prod, df_merc)

    vn_2024 = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])
    factor_vn = vn_2025 / vn_2024 if vn_2024 > 0 else 1.0

    df_fse = fse_mod.fse_anual(a, base, factor_vn)
    df_pessoal = pessoal_mod.pessoal_anual(a, base, df_total)
    df_cmvmc = cmvmc_mod.cmvmc_anual(a, base, df_prod, df_merc)

    fse_2025 = float(df_fse[df_fse.ano == 2025]["fse"].iloc[0])

    # Detalhe anual de FSE por rubrica para alocar o total 2025 mensalmente.
    df_fse_det = fse_mod.fse_detalhe_anual(a, base, factor_vn)
    fse_det_2025_by_rub: dict[str, float] = {
        rub: float(
            df_fse_det[(df_fse_det.ano == 2025) & (df_fse_det.rubrica == rub)]["valor"].iloc[0]
        )
        if not df_fse_det.empty and ((df_fse_det.ano == 2025) & (df_fse_det.rubrica == rub)).any()
        else 0.0
        for rub in rubricas_fse
    }

    # Reconciliação: garante que a soma das rubricas é exatamente o total do FSE 2025.
    det_total_2025 = float(sum(fse_det_2025_by_rub.values()))
    if det_total_2025 and abs(det_total_2025 - fse_2025) > 1e-6:
        # Ajusta a última rubrica para fechar por construção.
        rub_last = rubricas_fse[-1]
        fse_det_2025_by_rub[rub_last] = fse_det_2025_by_rub[rub_last] + (fse_2025 - det_total_2025)
    pessoal_2025 = float(df_pessoal[df_pessoal.ano == 2025]["gastos_pessoal"].iloc[0])
    cmvmc_2025 = float(df_cmvmc[df_cmvmc.ano == 2025]["cmvmc"].iloc[0])

    # Totais anuais 2025 do modelo completo (usado como âncora de articulação)
    dr_anual = stmt_mod.build_dr(a, base, sched)
    row_2025 = dr_anual[dr_anual.ano == 2025].iloc[0]

    # Custos armazenados como negativos no DR anual; negar para obter custo positivo
    dep_2025 = -float(row_2025["depreciacoes"])
    jur_2025 = -float(row_2025["juros"])
    irc_2025 = -float(row_2025["irc"])  # custo fiscal anual, positivo

    # Articulação mensal-anual: diferença entre EBITDA completo (hub + eco + outros
    # rendimentos + var. inventários + imparidades + outros gastos) e os itens
    # operacionais base (VN - CMVMC - FSE - pessoal). Distribuída uniformemente ÷12.
    ebitda_2025_completo = float(row_2025["ebitda"])
    ebitda_2025_ops = vn_2025 - cmvmc_2025 - fse_2025 - pessoal_2025
    outros_ebitda_m = (ebitda_2025_completo - ebitda_2025_ops) / 12.0

    # Rendimentos financeiros distribuídos uniformemente ÷12
    rend_fin_m = float(row_2025.get("rend_financeiros", 0.0)) / 12.0

    dist_saz = _dist_sazonal_total(a, base, sched)

    pessoal_m: dict[str, float] = {m: pessoal_2025 / 14.0 for m in MESES}
    pessoal_m["Jun"] = pessoal_2025 / 14.0 * 2
    pessoal_m["Nov"] = pessoal_2025 / 14.0 * 2

    rows = []

    for m in MESES:
        vn = vn_2025 * dist_saz[m]
        cmvmc = cmvmc_2025 * dist_saz[m]
        fse = fse_2025 * dist_saz[m]
        pessoal = pessoal_m[m]

        # Detalhe mensal de FSE 2025 por rubrica (aloca pela mesma sazonalidade do FSE total).
        fse_det_m = {
            rub_col[rub]: fse_det_2025_by_rub[rub] * dist_saz[m]
            for rub in rubricas_fse
        }

        # EBITDA inclui ajuste de articulação com o modelo anual completo
        ebitda = vn - cmvmc - fse - pessoal + outros_ebitda_m
        dep = dep_2025 / 12.0
        ebit = ebitda - dep
        juros = jur_2025 / 12.0
        # RAI inclui rendimentos financeiros (não desagregados sazonalmente)
        rai = ebit - juros + rend_fin_m
        # IRC distribuído uniformemente do total anual — garante que a soma
        # mensal = IRC anual, evitando divergência por meses com RAI negativo.
        irc = irc_2025 / 12.0
        rl = rai - irc

        rows.append(
            {
                "mes": m,
                "vn": round(vn),
                "cmvmc": round(cmvmc),
                "margem_bruta": round(vn - cmvmc),
                "fse": round(fse),
                "gastos_pessoal": round(pessoal),
                # colunas adicionais: FSE detalhado (custos positivos em €/período)
                **{k: round(v) for k, v in fse_det_m.items()},
                "outros_rendimentos_liq": round(outros_ebitda_m + rend_fin_m),
                "ebitda": round(ebitda),
                "depreciacoes": round(dep),
                "ebit": round(ebit),
                "juros": round(juros),
                "rend_financeiros": round(rend_fin_m),
                "rai": round(rai),
                "irc": round(irc),
                "rl": round(rl),
            }
        )

    return pd.DataFrame(rows)


def rolling_update(
    df_original: pd.DataFrame,
    realizados: dict[str, dict],
) -> pd.DataFrame:
    """Substitui meses estimados por valores reais, para rolling forecast.

    Args:
        df_original: output de build_tesouraria_mensal().
        realizados: dict {mes: {coluna: valor_real, ...}} para os meses decorridos.
            Exemplo:
            {"Jan": {"recebimentos_clientes": 3250000, ...}}

    Returns:
        Novo DataFrame com meses realizados substituídos e saldo recalculado.
    """
    df = df_original.copy()

    for mes, valores in realizados.items():
        mask = df["mes"] == mes

        for col, val in valores.items():
            if col in df.columns:
                df.loc[mask, col] = val

        # Recalcular fluxo_liquido para os meses alterados
        if mask.any():
            idx = df[mask].index[0]
            row = df.loc[idx]

            fl = (
                row["recebimentos_clientes"]
                - row["pagamentos_fornecedores"]
                - row["pagamentos_pessoal"]
                + row["fluxo_fiscal"]
            )

            df.loc[idx, "fluxo_liquido"] = round(fl)

    # Recalcular saldo acumulado em cadeia
    saldo = df["saldo_caixa_acumulado"].iloc[0] - df["fluxo_liquido"].iloc[0]

    for i, row in df.iterrows():
        saldo += row["fluxo_liquido"]
        df.loc[i, "saldo_caixa_acumulado"] = round(saldo)

    return df


def build_pessoal_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Gastos com pessoal mensais de 2025 como output independente.

    Distribuição: 1/14 por mês, duplicado em Jun (sub. férias) e Nov (sub. natal).

    Returns:
        DataFrame com colunas: mes, gastos_pessoal.
    """
    _, _, _, pessoal_m, _ = _build_mensais_2025(a, base, sched)
    return pd.DataFrame([
        {"mes": m, "gastos_pessoal": round(pessoal_m[m])}
        for m in MESES
    ])


def build_cmvmc_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """CMVMC mensal de 2025 como output independente.

    Distribuição sazonal ponderada por mercado (igual à usada no DR mensal).

    Returns:
        DataFrame com colunas: mes, cmvmc.
    """
    _, _, cmvmc_m, _, _ = _build_mensais_2025(a, base, sched)
    return pd.DataFrame([
        {"mes": m, "cmvmc": round(cmvmc_m[m])}
        for m in MESES
    ])


# Alias de compatibilidade (usado em rolling_forecast_mensal.py)
build_tesouraria = build_tesouraria_mensal
