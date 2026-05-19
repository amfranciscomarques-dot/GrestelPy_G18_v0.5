"""Serializa??o de dados do engine para respostas da API."""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from src.api.constants import PRODUCT_FAMILY_TO_SG_KEY
from src.engine.inputs import load

logger = logging.getLogger(__name__)


def _build_assumptions_response(cenario: str, hub_on: bool, ecogres_on: bool) -> dict:
    """Devolve pressupostos efetivos no formato esperado pelo frontend."""
    a, base, _ = load(cenario=cenario)

    a.raw.setdefault("hub_logistico", {})
    a.raw["hub_logistico"]["incluir_hub"] = hub_on

    a.raw.setdefault("ecogres", {})
    a.raw["ecogres"]["incluir_ecogres"] = ecogres_on

    eff = _flatten_assumptions(a)

    base_data = {}
    try:
        bv = base.vendas_mercado or {}
        base_data["vendas_PT"] = float(bv.get("Mercado_Interno_PT", 0))
        base_data["vendas_Externo"] = float(bv.get("Mercado_Externo", 0))
        base_data["vendas_total"] = base_data["vendas_PT"] + base_data["vendas_Externo"]
    except (TypeError, ValueError, AttributeError) as e:
        logger.warning("Erro a construir base_data: %s", e)

    return {
        "effective": eff,
        "base": base_data,
        "overrides": {},
        "summary": [],
    }


def _flatten_assumptions(a) -> dict[str, Any]:
    """Achata pressupostos aninhados para formato de chave ?nica do frontend."""
    out: dict[str, Any] = {}

    raw = a.raw or {}

    pessoal = raw.get("pessoal", {}) or {}
    out["custo_total_2024"] = pessoal.get("custo_total_2024_auditado", 14371357.70)
    out["hc_2024"] = pessoal.get("headcount_2024", 140)
    out["hc_2025"] = pessoal.get("headcount_2025", 142)

    ep = raw.get("elasticidade_pessoal", pessoal) or {}
    out["alpha_sem_hub"] = float(ep.get("alpha_sem_hub", 0.40)) * 100
    out["alpha_com_hub"] = float(ep.get("alpha_com_hub", 0.15)) * 100

    ecogres = raw.get("ecogres", {}) or {}
    trans = ecogres.get("transacoes_grestel", {}) or {}
    out["eco_cresc_subc"] = float(trans.get("crescimento_subcontratacao", 0.03)) * 100
    out["eco_cresc_ced"] = float(trans.get("crescimento_cedencia", 0.02)) * 100
    out["eco_subc_2024"] = float(trans.get("subcontratacao_2024", 2240000))
    out["eco_ced_2024"] = float(trans.get("cedencia_pessoal_2024", 360000))

    ops = ecogres.get("operacoes_correntes", {}) or {}
    out["eco_custos_op_2024"] = float((ops.get("custos_operacionais_2024") or {}).get("total", 5480000))
    out["eco_dep_2024"] = float(ops.get("depreciacao_2024", 275000))
    out["eco_rl_base_2024"] = float(ops.get("rl_base_2024", 85000))
    out["eco_cresc_custos"] = float(ops.get("crescimento_custos_anual", 0.02)) * 100
    out["eco_cresc_dep"] = float(ops.get("crescimento_depreciacao", 0.01)) * 100

    eco_elast = ops.get("elasticidade_pessoal", {}) or {}
    out["eco_alpha_sem_hub"] = float(eco_elast.get("alpha_sem_hub", 0.40)) * 100
    out["eco_alpha_com_hub"] = float(eco_elast.get("alpha_com_hub", 0.15)) * 100

    viab = ecogres.get("viabilidade", {}) or {}
    out["eco_irc_taxa"] = float(viab.get("irc_taxa_ecogres", 0.21)) * 100

    transfer = ecogres.get("transferencia_hub", {}) or {}
    out["eco_transfer_price"] = float(transfer.get("preco_transferencia_base", 180000))
    out["eco_transfer_inicio"] = int(transfer.get("inicio", 2026))

    capacidade = ecogres.get("capacidade", {}) or {}
    out["eco_ativar_reducao_mpsc"] = capacidade.get("ativar_reducao_mpsc", False)
    out["eco_reducao_mpsc_pct"] = float(capacidade.get("reducao_mpsc_por_capacidade", 0.15)) * 100
    out["eco_capacidade_referencia"] = float(capacidade.get("subcontratacao_capacidade_referencia", 2240000))

    h = raw.get("hub_logistico", {}).get("projeto_hub", {}) or {}
    out["hub_capex_base"] = float((h.get("capex") or {}).get("base", 6_000_000))
    out["hub_wacc"] = float((h.get("viabilidade") or {}).get("wacc", 0.08)) * 100
    out["hub_cresc_beneficios"] = float((h.get("beneficios_anuais") or {}).get("crescimento_anual", 0.02)) * 100

    impostos = raw.get("impostos", {}) or {}
    out["irc_taxa_geral"] = float(impostos.get("IRC_taxa_geral", 0.21)) * 100
    out["irc_taxa_reduzida"] = float(impostos.get("IRC_taxa_reduzida", 0.17)) * 100
    out["derrama_municipal"] = float(impostos.get("Derrama_Municipal", 0.015)) * 100
    out["derrama_estadual"] = float(impostos.get("Derrama_Estadual", 0.0135)) * 100
    out["derrama_estadual_limiar"] = float(impostos.get("Derrama_Estadual_limiar", 1500000))
    out["tsu_empresa"] = float(impostos.get("TSU_Empresa", 0.2375)) * 100
    out["sat"] = float(impostos.get("SAT", 0.03)) * 100
    out["sifide_taxa"] = float(impostos.get("SIFIDE_taxa_credito", 0.325)) * 100
    out["tributacao_autonoma"] = float(impostos.get("Tributacao_Autonoma_taxa", 0.10)) * 100
    out["majoracao_energia"] = float(impostos.get("Majoracao_Energia_pct", 0.20)) * 100
    out["iva_vendas"] = float(impostos.get("IVA_Vendas", 0.23)) * 100

    prazos = raw.get("prazos", {}) or {}
    out["pmr_dias"] = int(prazos.get("PMR_dias", 45))
    out["pmp_dias"] = int(prazos.get("PMP_Inventarios_dias", 63))
    out["dmi_pa_dias"] = int(prazos.get("DMI_PA_dias", 160))
    out["dmi_mp_dias"] = int(prazos.get("DMI_MP_dias", 160))
    out["dmi_merc_dias"] = int(prazos.get("DMI_Mercadorias_dias", 60))

    caixa = raw.get("caixa", {}) or {}
    out["caixa_minima"] = float(caixa.get("minima", 500000))
    out["caixa_maxima"] = float(caixa.get("maxima", 1500000))

    distrib = raw.get("distribuicao_resultados", {}) or {}
    out["payout_ratio"] = float(distrib.get("payout_ratio", 0.20)) * 100
    out["reserva_legal_pct"] = float(distrib.get("reserva_legal_pct", 0.05)) * 100
    out["inicio_distribuicao"] = int(distrib.get("ano_inicio_distribuicao", 2026))

    out["taxa_cresc_custo_2025"] = float(pessoal.get("taxa_cresc_custo_2025", 0.035)) * 100
    out["tsu_empregador"] = float(pessoal.get("TSU_empregador", 0.2375)) * 100
    out["subsidio_ferias_mes"] = pessoal.get("subsídio_férias_mes", "Jun")
    out["subsidio_natal_mes"] = pessoal.get("subsídio_natal_mes", "Nov")

    for k, v in (raw.get("crescimento_volume_vendas") or {}).items():
        out[f"cresc_vol_{k}"] = v

    for k, v in (raw.get("crescimento_pvu_vendas") or {}).items():
        out[f"cresc_preco_{k}"] = v

    for k, v in (raw.get("crescimento_fse") or {}).items():
        out[f"cresc_fse_{k}"] = v

    for k, v in (raw.get("crescimento_pessoal") or {}).items():
        out[f"cresc_pessoal_{k}"] = v

    for k, v in (raw.get("crescimento_custo_mercadorias") or {}).items():
        out[f"cresc_custo_merc_{k}"] = v

    for k, v in (raw.get("crescimento_mpsc") or {}).items():
        out[f"cresc_mpsc_{k}"] = v

    mercados = raw.get("mercados") or {}
    for mk, bloco in mercados.items():
        if bloco:
            out[f"mk_{mk}"] = float(bloco.get("peso_global", 0))

    out["mix_mercado_produto"] = deepcopy(raw.get("mix_mercado_produto", {}) or {})
    out["mix_canal_produto"] = deepcopy(raw.get("mix_canal_produto", {}) or {})
    out["sazonalidade"] = deepcopy(raw.get("sazonalidade", {}) or {
        m: bloco.get("sazonalidade", []) for m, bloco in mercados.items()
    })
    out["vendas_2024_por_mercado"] = deepcopy(raw.get("vendas_2024_por_mercado", {}) or {})
    out["mercados"] = deepcopy(mercados)

    mix_produtos = getattr(a, "mix_produtos_2024", {}) or {}
    for family, sg_key in PRODUCT_FAMILY_TO_SG_KEY.items():
        try:
            mix_value = mix_produtos.get(family)
            if mix_value is not None:
                out[sg_key] = round(float(mix_value) * 100.0, 2)
        except (TypeError, ValueError):
            continue

    out["incluir_ecogres"] = raw.get("ecogres", {}).get("incluir_ecogres", False)
    out["incluir_hub"] = raw.get("hub_logistico", {}).get("incluir_hub", False)

    return out


def _wrap_rows(value):
    """Garante o wrapper {rows: [...]} esperado pelo frontend."""
    if isinstance(value, list):
        return {"rows": value}
    if isinstance(value, dict) and "rows" in value:
        return value
    return {"rows": []}


def _fse_mensal_to_rows(fse_mensal):
    """Converte detalhe mensal de FSE em linhas JSON."""
    if not fse_mensal or not isinstance(fse_mensal, dict):
        return []

    rows = []
    for rubrica, valores in fse_mensal.items():
        if not isinstance(valores, dict):
            continue
        for mes, valor in valores.items():
            rows.append({
                "rubrica": rubrica,
                "mes": mes,
                "valor": float(valor) if valor else 0.0,
            })

    return rows

