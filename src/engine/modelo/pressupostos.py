"""Agregação estruturada de pressupostos para display e API.

Função central: build_pressupostos_summary(cenario, hub_on, ecogres_on)
Retorna um dict estável com secções e itens prontos para qualquer frontend.
"""

from __future__ import annotations

from typing import Any

from src.engine.inputs import load
from src.engine.inputs.constants import YEARS


def _pct(v: Any, decimais: int = 2) -> float:
    """Converte decimal para percentagem arredondada."""
    return round(float(v or 0) * 100, decimais)


def _item(label: str, value: Any, unit: str = "", note: str = "") -> dict:
    return {"label": label, "value": value, "unit": unit, "note": note}


def _cresc_section(id_: str, label: str, raw_key: str, raw: dict) -> dict:
    """Gera secção de crescimento a partir de um bloco de driver anual."""
    bloco = raw.get(raw_key, {}) or {}
    val_25 = float(bloco.get("base_2025", bloco.get("annual_2025", 0.0)))
    items = [_item("2025 (base 9 meses)", _pct(val_25), "%")]
    for y in YEARS[1:]:
        items.append(_item(str(y), _pct(bloco.get(y, 0.0)), "%"))
    return {"id": id_, "label": label, "items": items}


def build_pressupostos_summary(
    cenario: str = "Base",
    hub_on: bool = False,
    ecogres_on: bool = False,
) -> dict[str, Any]:
    """Retorna resumo estruturado de todos os pressupostos do cenário activo.

    Formato de retorno:
        cenario: str
        hub_ativo: bool
        ecogres_ativo: bool
        sections: list[dict]  — cada secção: {id, label, items}
            items: list[dict] — cada item: {label, value, unit, note}
    """
    a, _base, _sched = load(cenario=cenario)

    raw: dict = a.raw or {}
    raw.setdefault("hub_logistico", {})["incluir_hub"] = hub_on
    raw.setdefault("ecogres", {})["incluir_ecogres"] = ecogres_on

    sections: list[dict] = []

    # ── 1. Cenário & Período ─────────────────────────────────────────────────
    sections.append({
        "id": "cenario",
        "label": "Cenário & Período",
        "items": [
            _item("Cenário activo", cenario),
            _item("Hub Logístico incluído", hub_on),
            _item("Ecogres incluído", ecogres_on),
            _item("Horizonte de análise", "2024 – 2029"),
            _item("2025 (período parcial)", "Jan – Set (9 meses)"),
        ],
    })

    # ── 2. Macro & Contexto ──────────────────────────────────────────────────
    macro = raw.get("macro", {}) or {}
    inflacao = macro.get("inflacao", {}) or {}
    eurusd = macro.get("eur_usd", {}) or {}

    macro_items = [_item("Inflação média 2025", _pct(a.inflacao_anual(2025)), "%")]
    for y in YEARS[1:]:
        macro_items.append(_item(f"Inflação {y}", _pct(inflacao.get("anual", {}).get(y, 0.023)), "%"))

    macro_items.append(_item("EUR/USD médio 2025", round(a.eur_usd_anual(2025), 4)))
    for y in YEARS[1:]:
        macro_items.append(_item(f"EUR/USD {y}", round(float(eurusd.get("anual", {}).get(y, 1.08)), 4)))

    sections.append({"id": "macro", "label": "Macro & Contexto", "items": macro_items})

    # ── 3–5. Drivers de crescimento ──────────────────────────────────────────
    sections.append(_cresc_section(
        "cresc_volume", "Crescimento Vendas — Volume",
        "crescimento_volume_vendas", raw,
    ))
    sections.append(_cresc_section(
        "cresc_preco", "Crescimento Vendas — Preço",
        "crescimento_pvu_vendas", raw,
    ))
    sections.append(_cresc_section(
        "cresc_fse", "Crescimento FSE",
        "crescimento_fse", raw,
    ))
    sections.append(_cresc_section(
        "cresc_pessoal", "Crescimento Gastos Pessoal",
        "crescimento_pessoal", raw,
    ))

    cresc_mpsc = raw.get("crescimento_pcu_mpsc", {}) or {}
    if cresc_mpsc:
        sections.append(_cresc_section(
            "cresc_mpsc", "Crescimento MPSC",
            "crescimento_pcu_mpsc", raw,
        ))

    cresc_merc = raw.get("crescimento_custo_mercadorias", {}) or {}
    if cresc_merc:
        sections.append(_cresc_section(
            "cresc_mercadorias", "Crescimento Custo Mercadorias",
            "crescimento_custo_mercadorias", raw,
        ))

    # ── 6. Pessoal ───────────────────────────────────────────────────────────
    pessoal = raw.get("pessoal", {}) or {}
    sections.append({
        "id": "pessoal",
        "label": "Pessoal",
        "items": [
            _item("Headcount 2024", int(pessoal.get("headcount_2024", 140)), "pessoas"),
            _item("Headcount 2025", int(pessoal.get("headcount_2025", 142)), "pessoas"),
            _item("Custo total 2024 (auditado)", round(float(pessoal.get("custo_total_2024_auditado", 0)), 2), "€"),
            _item("Taxa crescimento custo 2025", _pct(pessoal.get("taxa_cresc_custo_2025", 0)), "%"),
        ],
    })

    # ── 7. Impostos & Prazos ─────────────────────────────────────────────────
    impostos = raw.get("impostos", {}) or {}
    prazos = raw.get("prazos", {}) or {}
    sections.append({
        "id": "impostos_prazos",
        "label": "Impostos & Prazos",
        "items": [
            _item("Taxa IRC geral", _pct(impostos.get("IRC_taxa_geral", 0.20), 1), "%"),
            _item("PMR (prazo médio de recebimento)", int(prazos.get("pmr_dias", 60)), "dias"),
            _item("PMP (prazo médio de pagamento)", int(prazos.get("pmp_dias", 45)), "dias"),
            _item("DMI (dias de inventário)", int(prazos.get("dmi_dias", 45)), "dias"),
        ],
    })

    # ── 8. Distribuição de Resultados ────────────────────────────────────────
    distrib = raw.get("distribuicao_resultados", {}) or {}
    if distrib:
        dist_items = []
        for k, v in distrib.items():
            try:
                dist_items.append(_item(k.replace("_", " ").title(), _pct(v), "%"))
            except (TypeError, ValueError):
                dist_items.append(_item(k.replace("_", " ").title(), str(v)))
        sections.append({"id": "distribuicao", "label": "Distribuição de Resultados", "items": dist_items})

    # ── 9. Hub Logístico (condicional) ───────────────────────────────────────
    if hub_on:
        hub_raw = (raw.get("hub_logistico", {}) or {}).get("projeto_hub", {}) or {}
        capex_b = hub_raw.get("capex", {}) or {}
        viab_h = hub_raw.get("viabilidade", {}) or {}
        benef_h = hub_raw.get("beneficios_anuais", {}) or {}
        fin_h = hub_raw.get("financiamento", {}) or {}
        loan = fin_h.get("emprestimo_bancario", {}) or {}

        hub_items = [
            _item("CAPEX base", round(float(capex_b.get("base", 5_500_000)), 0), "€"),
            _item("WACC", _pct(viab_h.get("wacc", 0.08), 1), "%"),
            _item("Taxa IRC Hub", _pct(viab_h.get("irc_taxa", 0.21), 1), "%"),
            _item("Crescimento benefícios anuais", _pct(benef_h.get("crescimento_anual", 0.02), 1), "%"),
            _item("Vida útil", int(hub_raw.get("vida_util_anos", 10)), "anos"),
        ]
        if loan:
            hub_items += [
                _item("Empréstimo bancário", round(float(loan.get("montante", 0)), 0), "€"),
                _item("Taxa de juro empréstimo", _pct(loan.get("taxa_juro", 0.04), 2), "%"),
            ]
        sections.append({"id": "hub", "label": "Hub Logístico M6", "items": hub_items})

    # ── 10. Ecogres (condicional) ────────────────────────────────────────────
    if ecogres_on:
        eco_raw = raw.get("ecogres", {}) or {}
        trans = eco_raw.get("transacoes_grestel", {}) or {}
        ops = eco_raw.get("operacoes_correntes", {}) or {}
        viab_eco = eco_raw.get("viabilidade", {}) or {}
        cap = eco_raw.get("capacidade", {}) or {}

        eco_items = [
            _item("Subcontratação base 2024", round(float(trans.get("subcontratacao_2024", 0)), 0), "€"),
            _item("Crescimento subcontratação", _pct(trans.get("crescimento_subcontratacao", 0.03), 1), "%"),
            _item("Cedência pessoal 2024", round(float(trans.get("cedencia_pessoal_2024", 0)), 0), "€"),
            _item("Crescimento cedência pessoal", _pct(trans.get("crescimento_cedencia", 0.02), 1), "%"),
            _item("Custos operacionais 2024", round(float((ops.get("custos_operacionais_2024") or {}).get("total", 0)), 0), "€"),
            _item("Crescimento custos anuais", _pct(ops.get("crescimento_custos_anual", 0.02), 1), "%"),
            _item("Taxa IRC Ecogres", _pct(viab_eco.get("irc_taxa_ecogres", 0.21), 1), "%"),
            _item("Redução MPSC activa", cap.get("ativar_reducao_mpsc", False)),
            _item("Redução MPSC por capacidade", _pct(cap.get("reducao_mpsc_por_capacidade", 0.15), 1), "%"),
        ]
        sections.append({"id": "ecogres", "label": "Ecogres", "items": eco_items})

    return {
        "cenario": cenario,
        "hub_ativo": hub_on,
        "ecogres_ativo": ecogres_on,
        "sections": sections,
    }
