"""
Módulo: engine/operacoes/vendas.py — Modelação de Vendas (Volume de Negócios)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Este módulo calcula a receita de vendas (Volume de Negócios) por:
  1. Produto: cada produto com preço unitário (PVU) e quantidade (QTY)
  2. Mercado: desagregação por geografias (PT, UE, Externo)
  3. Período: mensal em 2025, anual em 2026-2029
  4. Cenário: aplicação de crescimentos de volume e preço

LÓGICA DE CÁLCULO:

┌─────────────────────────────────────────────────────────────────┐
│ RECEITA = QUANTIDADE × PREÇO UNITÁRIO × (1 + crescimentos)      │
│                                                                 │
│ Crescimentos aplicados:                                        │
│   1. Crescimento de Volume (Quantidade)                        │
│      - Aumento de market share, penetração, consumo             │
│      - Aplicado ao período anterior: QTY_2025 = QTY_2024 × (1+g_volume)
│                                                                 │
│   2. Crescimento de Preço (Inflação/Pricing Power)             │
│      - Reajustamento de preços face à inflação                 │
│      - Pricing power: capacidade de aumentar preços acima inflação
│      - PVU_2025 = PVU_2024 × (1 + g_preço)                    │
│                                                                 │
│   3. Resultado: VN_2025 = (QTY_2024 × (1+g_vol)) × (PVU_2024 × (1+g_prec))
│                          = VN_2024 × (1+g_vol) × (1+g_prec)    │
│                          ≈ VN_2024 × (1 + g_vol + g_prec)      │
│                            [aproximação linear para pequenos g] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

ESTRUTURA POR PRODUTO:
  - Cada produto tem:
    * PVU (Preço de Venda Unitário): €/unidade
    * Mix de Vendas: % da receita total dedicado a este produto
    * Distribuição Geográfica:
      - PT (Portugal): mercado doméstico (maior segurança)
      - UE (União Europeia): mercado regulado, logistics complexo
      - EXT (Resto do Mundo): maior risco mas potencial de crescimento
    * Sazonalidade: pesos de venda por mês (ex: maior venda em verão)

PERÍODO 2025 (Parcial - Janeiro a Setembro):
  - Contém dados mensais (por mês de janeiro a setembro)
  - Permite análise de seasonalidade e cash flow management
  - Período: 9 meses (não 12), facto crítico para scaling de custos

PERÍODOS 2026-2029 (Completos - Janeiro a Dezembro):
  - Dados agregados por ano (sem desagregação mensal)
  - Crescimentos acumulativos aplicados cada ano

MERCADORIAS (vs Produtos):
  - Vendidas a margens fixas (% markup sobre custo)
  - Menos detalhadas que produtos (simples artigos de comércio)
  - Agregadas numa única categoria "Mercadorias"

SAÍDA:
  - DataFrame com colunas: ano, mês, produto, mercado, pvu, qty, vn
  - Permite relatórios granulares (por produto, por mercado) ou agregados
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, YEARS, ALL_YEARS, MESES, PRODUTOS


def _saz_to_dict(values) -> dict[str, float]:
    """Converte sazonalidade em lista ou dict para dict {mês: peso}."""
    if isinstance(values, dict):
        return values

    if isinstance(values, list):
        return {
            m: float(values[i])
            for i, m in enumerate(MESES)
            if i < len(values)
        }

    return {m: 1 / 12 for m in MESES}


def _qty_2024_from_data(a: Assumptions, base: Base2024) -> pd.DataFrame:
    """Quantidades base 2024 por (produto, mercado) - dos dados carregados."""
    pvu_map = a.raw.get("pvu_base", base.pvu_base)

    if a.produtos_raw:
        pf = a.product_families

        for nome, info in pf.items():
            info["pvu_base_2024"] = pvu_map.get(nome, info.get("pvu_base_2024", 0.0))

    rows = []

    for nome, info in (a.product_families or {}).items():
        pvu = pvu_map.get(nome, info.get("pvu_base_2024", 0.0))
        vn_total_2024 = base.totais.get("VN_Produtos_2024", base.raw.get("dr_2024_real", {}).get("vn", 0.0))

        vn_by_mercado = base.vendas_mercado or {}
        vn_pt = vn_by_mercado.get("Mercado_Interno_PT", 0.0)
        vn_ext = vn_by_mercado.get("Mercado_Externo", 0.0)

        mix = a.mix_produtos_2024 or {}
        peso = mix.get(nome)

        if peso is None:
            peso = info.get("sales_mix_2024") if isinstance(info, dict) else None

        if peso is None:
            raise ValueError(f"Missing sales_mix_2024 para produto: {nome}")

        vn_prod = vn_total_2024 * peso if vn_total_2024 else peso

        qty_total = vn_prod / pvu if pvu else 0.0

        mercado_mix = a.raw.get("mix_mercado_override")

        if mercado_mix:
            pt_w = float(mercado_mix.get("PT", 0.33))
            ue_w = float(mercado_mix.get("UE", 0.30))
            ext_w = float(mercado_mix.get("EXT", 0.37))
        else:
            pt_w = vn_pt / (vn_pt + vn_ext) if (vn_pt + vn_ext) else 0.33
            ue_w = 0.30
            ext_w = 1.0 - pt_w - ue_w

        total_w = pt_w + ue_w + ext_w or 1.0

        dist = {
            "PT": pt_w / total_w,
            "UE": ue_w / total_w,
            "EXT": ext_w / total_w,
        }

        for mkt, w in dist.items():
            rows.append(
                {
                    "produto": nome,
                    "mercado": mkt,
                    "qtd_2024": qty_total * w,
                }
            )

    return pd.DataFrame(rows)


def _qty_2024_mixed(a: Assumptions, base: Base2024) -> pd.DataFrame:
    """Devolve quantidades 2024, com overrides de mix quando existirem."""
    df = _qty_2024_from_data(a, base)

    mix_prod = a.raw.get("mix_produto_override")
    mix_mkt = a.raw.get("mix_mercado_override")

    if mix_prod is None and mix_mkt is None:
        return df

    total_qty = df["qtd_2024"].sum()
    rows = []

    for prod in PRODUTOS:
        df_p = df[df["produto"] == prod]

        qty_prod = (
            total_qty * mix_prod[prod]
            if mix_prod is not None
            else df_p["qtd_2024"].sum()
        )

        if mix_mkt is not None:
            pt_w = mix_mkt.get("PT", 0.0)
            ue_w = mix_mkt.get("UE", 0.0)
            ext_w = mix_mkt.get("USA", 0.0) + mix_mkt.get("ROW", 0.0)

            total_w = pt_w + ue_w + ext_w or 1.0

            dist = {
                "PT": pt_w / total_w,
                "UE": ue_w / total_w,
                "EXT": ext_w / total_w,
            }
        else:
            total_p = df_p["qtd_2024"].sum() or 1.0

            dist = {
                r["mercado"]: r["qtd_2024"] / total_p
                for _, r in df_p.iterrows()
            }

        for mkt, w in dist.items():
            rows.append(
                {
                    "produto": prod,
                    "mercado": mkt,
                    "qtd_2024": qty_prod * w,
                }
            )

    return pd.DataFrame(rows)


def _monthly_rates(
    block: dict,
    inflation_monthly: list[float] | None = None,
) -> dict[str, float]:
    """Converte taxa anual base 2025 em taxas mensais e aplica acréscimos.

    Filosofia B: se `inflation_monthly` for fornecido, o bloco contém um
    spread REAL e a taxa efectiva mensal é composta com a inflação:
        r_nominal_m = (1 + inf_m) × (1 + r_real_m) − 1

    Sem `inflation_monthly` (grandezas físicas como volume), o bloco já
    contém a taxa directa e não se aplica nenhuma composição.

    Estrutura do bloco:
      base_2025 / annual_2025  → spread real anual base
      acrescimos_mensais       → delta (pp) adicionado a cada mês
    """
    block = block or {}

    g_annual = block.get("base_2025", block.get("annual_2025", 0.0))
    g_base_real = (1.0 + g_annual) ** (1.0 / 12.0) - 1.0

    acrescimos = (
        block.get("acrescimos_mensais")
        or block.get("overrides_mensais")
        or {}
    )

    _MES_NOME_IDX = {
        "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5,
        "Jun": 6, "Jul": 7, "Ago": 8, "Set": 9, "Out": 10,
        "Nov": 11, "Dez": 12,
    }

    out = {}

    for i, mes in enumerate(MESES):
        idx = _MES_NOME_IDX[mes]
        delta = acrescimos.get(mes, acrescimos.get(idx, acrescimos.get(str(idx), 0.0)))
        real_rate = g_base_real + float(delta)

        if inflation_monthly is not None and i < len(inflation_monthly):
            inf = inflation_monthly[i]
            out[mes] = (1.0 + inf) * (1.0 + real_rate) - 1.0
        else:
            out[mes] = real_rate

    return out


def _monthly_cum_index(rates_by_month: dict) -> dict[str, float]:
    """Índice cumulativo mensal."""
    idx = {}
    cum = 1.0

    for m in MESES:
        cum *= 1 + rates_by_month[m]
        idx[m] = cum

    return idx


def _eur_usd_factor(a: Assumptions, ano: int) -> float:
    """Factor de correção cambial para vendas EXT denominadas em USD.

    Aplica a fórmula M3:
        factor = 1 - pct_usd_in_ext × (1 − eur_usd_base / eur_usd_proj)

    Se EUR/USD sobe (USD deprecia), factor < 1 → VN EXT cai.
    Só é aplicado ao mercado EXT (USA + ROW); PT e UE não têm exposição USD.
    """
    if ano == 2024:
        return 1.0

    cambio = a.raw.get("cambio_usd", {})
    pct_vn_usd = float(cambio.get("pct_vn_usd", 0.21))
    eur_usd_base = float(cambio.get("eur_usd_base", 1.08))

    mercados = a.mercados or {}
    usa_peso = float(mercados.get("USA", {}).get("peso_global", 0.35))
    row_peso = float(mercados.get("ROW", {}).get("peso_global", 0.18))
    ext_peso = usa_peso + row_peso

    pct_usd_in_ext = pct_vn_usd / ext_peso if ext_peso > 0 else pct_vn_usd

    eur_usd_proj = a.eur_usd_anual(ano)
    if eur_usd_proj <= 0:
        return 1.0

    return 1.0 - pct_usd_in_ext * (1.0 - eur_usd_base / eur_usd_proj)


def _market_weights_for_ext(a: Assumptions, produto: str) -> tuple[float, float]:
    """Pesos USA/ROW para o mercado EXT."""
    mix_mp = a.mix_mercado_produto or {}

    if produto in mix_mp:
        mix = mix_mp[produto]
        return float(mix.get("USA", 0.0)), float(mix.get("ROW", 0.0))

    mercados = a.mercados or {}

    return (
        float(mercados.get("USA", {}).get("peso_global", 0.0)),
        float(mercados.get("ROW", {}).get("peso_global", 0.0)),
    )


def _ext_seasonality(a: Assumptions, produto: str) -> dict[str, float]:
    """Sazonalidade ponderada para EXT = USA + ROW."""
    saz = a.sazonalidade

    s_usa = _saz_to_dict(saz.get("USA", []))
    s_row = _saz_to_dict(saz.get("ROW", []))

    mix_usa, mix_row = _market_weights_for_ext(a, produto)
    total = mix_usa + mix_row

    if total == 0:
        return {m: 1 / 12 for m in MESES}

    return {
        m: (mix_usa * s_usa[m] + mix_row * s_row[m]) / total
        for m in MESES
    }


def _factor_2025(
    a: Assumptions,
    base: Base2024,
    mercado: str,
    produto: str,
) -> tuple[float, float]:
    """Retorna (factor_volume, factor_preço) para 2025 vs 2024."""
    _ = base

    block = a.cenario_block()

    # Volume: grandeza física, não ligada à inflação
    vol_block = (block.get("volume_produto_crescimento", {}) or {}).get(produto)

    if vol_block is None:
        vol_block = block.get("volume_vendas") or a.raw.get("crescimento_volume_vendas", {})

    cum_vol = _monthly_cum_index(_monthly_rates(vol_block))

    # Preço: Filosofia B — spread real composto com inflação mensal
    pvu_block = (block.get("pvu_produto_crescimento", {}) or {}).get(produto)

    if pvu_block is None:
        pvu_block = a.raw.get("pvu_produto_crescimento", {}).get(produto)

    if pvu_block is None:
        pvu_block = block.get("preco_vendas", {})

    cum_price = _monthly_cum_index(
        _monthly_rates(pvu_block, inflation_monthly=a.inflacao_mensal_2025())
    )

    if mercado in ("EXTERNO", "EXT"):
        s = _ext_seasonality(a, produto)
    else:
        s = _saz_to_dict(a.sazonalidade.get(mercado, []))

    vol_f = sum(s[m] * cum_vol[m] for m in MESES)
    price_f = sum(s[m] * cum_price[m] for m in MESES)

    return vol_f, price_f


def _market_uplift(a: Assumptions, mercado: str, produto: str) -> float:
    """Uplift de volume por mercado/canal."""
    mu = a.triggers.get("market_uplift") or {}

    def _single(mkt: str) -> float:
        mkt_data = mu.get(mkt, {})

        if not mkt_data:
            return 0.0

        market_uplift = 0.0
        market_entry = mkt_data.get(a.cenario, {})

        if isinstance(market_entry, dict) and market_entry.get("enabled", False):
            market_uplift = market_entry.get("value", 0.0)
        elif mkt_data.get("enabled", False):
            market_uplift = mkt_data.get("value", 0.0)

        channels_data = mkt_data.get("channels", {})
        enabled_channels = []

        for ch, ch_data in channels_data.items():
            if ch == "global":
                continue

            entry = ch_data.get(a.cenario, ch_data)

            if isinstance(entry, dict) and entry.get("enabled", False):
                enabled_channels.append(ch)

        if not enabled_channels:
            return market_uplift

        mix_canal = a.mix_canal_produto or {}

        if produto in mix_canal and mkt in mix_canal[produto]:
            mix = mix_canal[produto][mkt]
        else:
            mix = (
                (a.mix_mercado_canal or {}).get(
                    mkt,
                    (a.mercados or {}).get(mkt, {}).get("canais", {}),
                )
            )

        total_weight = 0.0
        weighted_uplift = 0.0

        for ch in enabled_channels:
            ch_entry = channels_data[ch].get(a.cenario, channels_data[ch])
            weight = mix.get(ch, 0.0)
            uplift = ch_entry.get("value", 0.0)

            weighted_uplift += weight * uplift
            total_weight += weight

        channel_uplift = (
            weighted_uplift / total_weight
            if total_weight > 0
            else 0.0
        )

        return market_uplift + channel_uplift

    if mercado in ("UE", "USA", "ROW"):
        ext_entry = mu.get("EXT", {})
        ext_data = ext_entry.get(a.cenario, ext_entry)

        if isinstance(ext_data, dict) and ext_data.get("enabled", False):
            return ext_data.get("value", 0.0)

    if mercado in ("EXTERNO", "EXT"):
        usa_w, row_w = _market_weights_for_ext(a, produto)
        total = usa_w + row_w

        if total == 0:
            return 0.0

        return (usa_w * _single("USA") + row_w * _single("ROW")) / total

    return _single(mercado)


def vendas_anuais(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """VN anual por (produto, mercado, ano) para 2024-2029."""
    _ = sched

    df = _qty_2024_mixed(a, base)
    pvu_map = a.raw.get("pvu_base", base.pvu_base)

    factors_2025_vol = {}
    factors_2025_price = {}

    for _, r in df.iterrows():
        v, p = _factor_2025(a, base, r["mercado"], r["produto"])

        factors_2025_vol[(r["produto"], r["mercado"])] = v
        factors_2025_price[(r["produto"], r["mercado"])] = p

    g_vol_yr = a.cresc_2026_2029("volume_vendas")

    rows = []

    for _, r in df.iterrows():
        prod = r["produto"]
        merc = r["mercado"]
        qty_24 = r["qtd_2024"]

        g_price_yr = a.cresc_2026_2029_pvu(prod)

        qty24 = qty_24
        pvu24 = pvu_map.get(prod, 0.0)

        rows.append(
            {
                "ano": 2024,
                "produto": prod,
                "mercado": merc,
                "qtd": qty24,
                "pvu": pvu24,
                "vn": qty24 * pvu24,
            }
        )

        vf = factors_2025_vol[(prod, merc)] * (1 + _market_uplift(a, merc, prod))
        pf = factors_2025_price[(prod, merc)]

        qty_2025 = qty24 * vf
        pvu_2025 = pvu24 * pf

        fx_2025 = _eur_usd_factor(a, 2025) if merc in ("EXT", "EXTERNO") else 1.0

        rows.append(
            {
                "ano": 2025,
                "produto": prod,
                "mercado": merc,
                "qtd": qty_2025,
                "pvu": pvu_2025,
                "vn": qty_2025 * pvu_2025 * fx_2025,
            }
        )

        prev_qty = qty_2025
        prev_pvu = pvu_2025

        for y in YEARS[1:]:
            prev_qty *= 1 + g_vol_yr[y]
            prev_pvu *= 1 + g_price_yr[y]

            fx = _eur_usd_factor(a, y) if merc in ("EXT", "EXTERNO") else 1.0

            rows.append(
                {
                    "ano": y,
                    "produto": prod,
                    "mercado": merc,
                    "qtd": prev_qty,
                    "pvu": prev_pvu,
                    "vn": prev_qty * prev_pvu * fx,
                }
            )

    return pd.DataFrame(rows)


def vendas_mercadorias_anuais(
    a: Assumptions,
    base: Base2024,
) -> pd.DataFrame:
    """VN anual de mercadorias."""
    block = a.cenario_block()

    vol_block = block.get("volume_vendas") or a.raw.get("crescimento_volume_vendas", {})
    cum_vol = _monthly_cum_index(_monthly_rates(vol_block))

    saz = _saz_to_dict(a.sazonalidade.get("PT", []))
    vol_f_2025 = sum(saz[m] * cum_vol[m] for m in MESES)

    g_vol_yr = a.cresc_2026_2029("volume_vendas")

    mix_override = a.raw.get("mix_mercadoria_override")
    pvu_map = a.raw.get("pvu_base", base.pvu_base)
    pvu_2025_ovs = a.raw.get("pvu_2025_mercadorias", {})

    vn_total = base.totais["VN_Mercadorias_2024"]
    mercadorias = base.mercadorias

    base_qtys = {}

    for nome, info in mercadorias.items():
        peso = info.get("peso_vn", info.get("sales_mix_2024", 0.0))
        pvu = info.get("pvu", info.get("pvu_base_2024", pvu_map.get(nome, 0.0)))

        base_qtys[nome] = (peso * vn_total) / pvu if pvu else 0.0

    total_qty = sum(base_qtys.values())

    rows = []

    for nome, info in mercadorias.items():
        qty_2024 = (
            total_qty * mix_override[nome]
            if mix_override
            else base_qtys[nome]
        )

        pvu_2024 = pvu_map.get(
            nome,
            info.get("pvu", info.get("pvu_base_2024", 0.0)),
        )

        rows.append(
            {
                "ano": 2024,
                "mercadoria": nome,
                "qtd": qty_2024,
                "pvu": pvu_2024,
                "vn": qty_2024 * pvu_2024,
            }
        )

        qty_2025 = qty_2024 * vol_f_2025

        rate_2025 = (
            a.cresc_2025_pvu_mercadoria(nome)
            if hasattr(a, "cresc_2025_pvu_mercadoria")
            else 0.0
        )

        pvu_2025 = pvu_2025_ovs.get(
            nome,
            pvu_2024 * (1 + rate_2025),
        )

        rows.append(
            {
                "ano": 2025,
                "mercadoria": nome,
                "qtd": qty_2025,
                "pvu": pvu_2025,
                "vn": qty_2025 * pvu_2025,
            }
        )

        prev_qty = qty_2025
        prev_pvu = pvu_2025

        g_price_yr = (
            a.cresc_2026_2029_pvu_mercadoria(nome)
            if hasattr(a, "cresc_2026_2029_pvu_mercadoria")
            else {y: 0.0 for y in YEARS[1:]}
        )

        for y in YEARS[1:]:
            prev_qty *= 1 + g_vol_yr[y]
            prev_pvu *= 1 + g_price_yr[y]

            rows.append(
                {
                    "ano": y,
                    "mercadoria": nome,
                    "qtd": prev_qty,
                    "pvu": prev_pvu,
                    "vn": prev_qty * prev_pvu,
                }
            )

    return pd.DataFrame(rows)


def resumo_anual(
    df_prod: pd.DataFrame,
    df_merc: pd.DataFrame,
) -> pd.DataFrame:
    """Resumo anual de VN."""
    prod_yr = df_prod.groupby("ano")["vn"].sum().rename("vn_produtos")
    merc_yr = df_merc.groupby("ano")["vn"].sum().rename("vn_mercadorias")

    out = pd.concat([prod_yr, merc_yr], axis=1)
    out["vn_total"] = out["vn_produtos"] + out["vn_mercadorias"]

    return out.reset_index()


def vendas_mensais_2025(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """VN mensal de 2025 por mês, produto/mercadoria e mercado."""
    df_anual = vendas_anuais(a, base, sched)
    df_merc = vendas_mercadorias_anuais(a, base)

    df_2025_prod = df_anual[df_anual.ano == 2025].copy()

    rows = []

    for _, r in df_2025_prod.iterrows():
        prod = r["produto"]
        merc = r["mercado"]
        vn_anual = r["vn"]

        if merc in ("EXT", "EXTERNO"):
            s = _ext_seasonality(a, prod)
        else:
            s = _saz_to_dict(a.sazonalidade.get(merc, []))

        for m in MESES:
            rows.append(
                {
                    "mes": m,
                    "produto": prod,
                    "mercado": merc,
                    "vn": vn_anual * s[m],
                }
            )

    saz_pt = _saz_to_dict(a.sazonalidade.get("PT", []))
    df_2025_merc = df_merc[df_merc.ano == 2025]

    for _, r in df_2025_merc.iterrows():
        for m in MESES:
            rows.append(
                {
                    "mes": m,
                    "produto": r["mercadoria"],
                    "mercado": "PT",
                    "vn": r["vn"] * saz_pt[m],
                }
            )

    return pd.DataFrame(rows)
