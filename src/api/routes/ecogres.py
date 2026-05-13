"""Rotas da Ecogres."""

from fastapi import APIRouter, Query

from src.engine.projetos.ecogres import ecogres_dr, load as eco_load

router = APIRouter(prefix="/api")


@router.get("/ecogres")
def get_ecogres(
    hub_on: bool = Query(False),
    cresc_subc: float | None = Query(None),
    cresc_ced: float | None = Query(None),
    cresc_custos: float | None = Query(None),
    cresc_dep: float | None = Query(None),
    alpha_sem_hub: float | None = Query(None),
    alpha_com_hub: float | None = Query(None),
    transfer_price: float | None = Query(None),
    transfer_inicio: int | None = Query(None),
    irc_taxa: float | None = Query(None),
):
    eco = eco_load()
    ops = eco.get("operacoes_correntes", {}) or {}
    trans = eco.get("transacoes_grestel", {}) or {}
    viab = eco.get("viabilidade", {}) or {}
    transfer = eco.get("transferencia_hub", {}) or {}
    elasticidade = (ops.get("elasticidade_pessoal", {}) or {})

    assumptions_used = {
        "hub_on": hub_on,
        "cresc_subc": float(cresc_subc) / 100 if cresc_subc is not None else float(trans.get("crescimento_subcontratacao", 0.03)),
        "cresc_ced": float(cresc_ced) / 100 if cresc_ced is not None else float(trans.get("crescimento_cedencia", 0.02)),
        "cresc_custos": float(cresc_custos) if cresc_custos is not None else float(ops.get("crescimento_custos_anual", 0.02)),
        "cresc_dep": float(cresc_dep) if cresc_dep is not None else float(ops.get("crescimento_depreciacao", 0.01)),
        "alpha_sem_hub": float(alpha_sem_hub) if alpha_sem_hub is not None else float(elasticidade.get("alpha_sem_hub", 0.40)),
        "alpha_com_hub": float(alpha_com_hub) if alpha_com_hub is not None else float(elasticidade.get("alpha_com_hub", 0.15)),
        "transfer_price": float(transfer_price) if transfer_price is not None else float(transfer.get("preco_transferencia_base", 180000)),
        "transfer_inicio": int(transfer_inicio) if transfer_inicio is not None else int(transfer.get("inicio", 2026)),
        "irc_taxa": float(irc_taxa) if irc_taxa is not None else float(viab.get("irc_taxa_ecogres", 0.21)),
    }
    df = ecogres_dr(
        eco,
        hub_ativo=hub_on,
        cresc_subc=cresc_subc,
        cresc_ced=cresc_ced,
        cresc_custos=cresc_custos,
        cresc_dep=cresc_dep,
        alpha_sem_hub=alpha_sem_hub,
        alpha_com_hub=alpha_com_hub,
        transfer_price=transfer_price,
        transfer_inicio=transfer_inicio,
        irc_taxa=irc_taxa,
    )
    return {"rows": df.to_dict(orient="records"), "assumptions_used": assumptions_used}
