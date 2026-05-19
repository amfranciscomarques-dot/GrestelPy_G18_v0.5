"""Monte Carlo — Viabilidade do Hub Logístico 4.0.

Complementa a análise determinística (tornado, ponto crítico) com simulação estocástica:
em vez de 2 pontos por driver (pessimista/otimista), amostra distribuições contínuas e
corre N iterações completas do modelo de viabilidade.

Principais saídas:
  • Distribuição do VAL e TIR (percentis P5–P95, média, desvio-padrão)
  • P(VAL > 0)  — probabilidade de o projeto ser viável
  • P(TIR > WACC_base) — probabilidade de excesso de retorno sobre o custo de capital
  • Correlações de Pearson driver → VAL (ranking de importância dos riscos)
  • Dados de histograma prontos para renderização no frontend

Distribuições por driver:
  inventario   Triangular(1 M€, 2 M€, 2,5 M€)       — evento pontual com teto físico
  pt2030_taxa  Triangular(20 %, 45 %, 45 %)           — assimétrica (base = máximo aprovável)
  b2c          Normal truncada N(1,0; σ=0,20) ∈ [0,3; 2,0] — incerteza de mercado
  pessoal      Triangular(200 k€, 380 k€, 500 k€)    — eficácia da automação
  wacc         Triangular(6 %, 8 %, 10 %)             — risco de financiamento
  capex        Triangular(−15 %, base, +15 %)         — derrapagem de obra 4.0

Dependências: apenas numpy + stdlib (sem scipy).
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from .hub_logistico import load, viabilidade_hub


# ---------------------------------------------------------------------------
# Distribuições por defeito (calibradas com os ranges do tornado_hub)
# ---------------------------------------------------------------------------

DEFAULT_DISTRIBUTIONS: dict[str, dict] = {
    "inventario": {
        "type": "triangular",
        "min": 1_000_000.0,
        "mode": 2_000_000.0,
        "max": 2_500_000.0,
    },
    # Triangular degenerada (mode = max): cauda longa para a esquerda —
    # modela o risco de aprovação parcial do PT2030 (base = montante máximo).
    "pt2030_taxa": {
        "type": "triangular",
        "min": 0.20,
        "mode": 0.45,
        "max": 0.45,
    },
    # Normal truncada: incerteza de mercado em torno do cenário base (×1.0).
    "b2c": {
        "type": "truncnorm",
        "mean": 1.0,
        "std": 0.20,
        "low": 0.30,
        "high": 2.00,
    },
    "pessoal": {
        "type": "triangular",
        "min": 200_000.0,
        "mode": 380_000.0,
        "max": 500_000.0,
    },
    "wacc": {
        "type": "triangular",
        "min": 0.06,
        "mode": 0.08,
        "max": 0.10,
    },
    # capex: min/mode/max calculados em runtime (±15 % sobre proj["capex"]["base"])
    "capex": {
        "type": "triangular",
        "min": None,
        "mode": None,
        "max": None,
    },
}

DRIVERS = ["inventario", "pt2030_taxa", "b2c", "pessoal", "wacc", "capex"]


# ---------------------------------------------------------------------------
# Samplers (numpy puro)
# ---------------------------------------------------------------------------

def _sample_triangular(
    rng: np.random.Generator,
    low: float,
    mode: float,
    high: float,
    n: int,
) -> np.ndarray:
    """Amostrador triangular usando numpy.random.Generator.triangular."""
    # Caso degenerado: se low == high (distribuição pontual), retorna constante.
    if math.isclose(low, high, rel_tol=1e-9):
        return np.full(n, low)
    # numpy aceita mode == low ou mode == high (casos degenerados válidos)
    return rng.triangular(low, mode, high, size=n)


def _sample_truncated_normal(
    rng: np.random.Generator,
    mean: float,
    std: float,
    low: float,
    high: float,
    n: int,
) -> np.ndarray:
    """Normal truncada por rejection sampling.

    Para os parâmetros b2c (N(1.0, 0.20) em [0.3, 2.0]) a taxa de rejeição é
    < 0,3 % — o over-sampling de 10× é suficiente para qualquer n prático.
    """
    collected: list[float] = []
    while len(collected) < n:
        batch = rng.normal(mean, std, size=max(n * 10, 500))
        valid = batch[(batch >= low) & (batch <= high)]
        collected.extend(valid.tolist())
    return np.array(collected[:n])


def _draw_samples(
    rng: np.random.Generator,
    dist_cfg: dict,
    n: int,
) -> np.ndarray:
    """Despacha para o sampler correto conforme dist_cfg["type"]."""
    t = dist_cfg["type"]
    if t == "triangular":
        return _sample_triangular(
            rng,
            float(dist_cfg["min"]),
            float(dist_cfg["mode"]),
            float(dist_cfg["max"]),
            n,
        )
    if t == "truncnorm":
        return _sample_truncated_normal(
            rng,
            float(dist_cfg["mean"]),
            float(dist_cfg["std"]),
            float(dist_cfg["low"]),
            float(dist_cfg["high"]),
            n,
        )
    raise ValueError(f"Tipo de distribuição desconhecido: {t!r}")


# ---------------------------------------------------------------------------
# Mutação do hub (espelha sensibilidade_hub() de hub_logistico.py)
# ---------------------------------------------------------------------------

def _apply_sample(hub_base: dict, s: dict[str, float]) -> tuple[dict, float]:
    """Aplica um conjunto de valores amostrados a uma cópia profunda do hub.

    Retorna (hub_mutado, wacc_amostrado).
    O wacc NÃO é mutado no dicionário — é passado como kwarg a viabilidade_hub()
    (mesmo comportamento de sensibilidade_hub() nas linhas 1515-1527 do módulo original).
    """
    h = copy.deepcopy(hub_base)
    proj = h["projeto_hub"]

    # 1. Libertação de inventário (benefício pontual one-time)
    proj["beneficios_pontuais"]["libertacao_inventario"] = s["inventario"]

    # 2. CAPEX — escala base + cronograma anual proporcionalmente.
    #    A mesma proporção é aplicada ao capex_elegivel do RFAI para manter
    #    consistência interna (se mais é investido, mais é elegível a crédito fiscal).
    capex_base_val = float(proj["capex"]["base"])
    factor = s["capex"] / capex_base_val if capex_base_val else 1.0
    proj["capex"]["base"] = s["capex"]
    for y in list(proj["capex"]["cronograma"].keys()):
        proj["capex"]["cronograma"][y] = float(proj["capex"]["cronograma"][y]) * factor
    rfai_cfg = proj.get("rfai", {})
    if rfai_cfg.get("aplicar", False) and "capex_elegivel" in rfai_cfg:
        rfai_cfg["capex_elegivel"] = float(rfai_cfg["capex_elegivel"]) * factor

    # 3. PT2030 — montante em € = taxa amostrada × CAPEX amostrado.
    #    (O subsídio é definido como % do CAPEX, logo ambos variam em conjunto.)
    proj["financiamento"]["PT2030"]["montante"] = s["pt2030_taxa"] * s["capex"]

    # 4. Poupança operacional (pessoal + automação)
    ben = proj["beneficios_anuais"]
    ben["poupanca_operacional"] = s["pessoal"]
    quebras = float(ben.get("reducao_quebras", 0.0))
    opex = abs(float(
        ben.get("opex_incremental")
        or proj.get("opex_detalhe", {}).get("total", 0.0)
        or 0.0
    ))
    ben["beneficio_liquido_anual"] = s["pessoal"] + quebras - opex

    # 5. B2C — factor de escala sobre o VN incremental por ano
    vn_map = proj.get("beneficios_comerciais", {}).get("vn_incremental", {})
    for yr in list(vn_map.keys()):
        vn_map[yr] = float(vn_map[yr]) * s["b2c"]

    # wacc devolvido separadamente (não mutado no dict)
    return h, float(s["wacc"])


# ---------------------------------------------------------------------------
# Estatísticas e histograma
# ---------------------------------------------------------------------------

def _percentiles(values: np.ndarray, pcts: list[int]) -> dict[str, float]:
    """Dicionário de percentis a partir de um array numpy."""
    return {f"p{p}": float(np.percentile(values, p)) for p in pcts}


def _build_histogram(values: np.ndarray, n_bins: int = 40) -> dict[str, Any]:
    """Histograma JSON-serializable com centros de bins, contagens e arestas."""
    counts, edges = np.histogram(values, bins=n_bins)
    centers = [(float(edges[i]) + float(edges[i + 1])) / 2.0 for i in range(n_bins)]
    return {
        "bins": centers,
        "counts": [int(c) for c in counts],
        "edges": [float(e) for e in edges],
    }


def _pearson(x: list[float], y: list[float]) -> float:
    """Correlação de Pearson entre dois vetores (ignora NaN via máscara)."""
    xa = np.array(x, dtype=float)
    ya = np.array(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    if mask.sum() < 2:
        return 0.0
    corr_matrix = np.corrcoef(xa[mask], ya[mask])
    return float(corr_matrix[0, 1])


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def monte_carlo_hub(
    hub: dict | None = None,
    n_simulations: int = 1000,
    irc_taxa: float | None = None,
    distributions: dict | None = None,
    seed: int | None = None,
) -> dict:
    """Simulação Monte Carlo da viabilidade do Hub Logístico 4.0.

    Parâmetros
    ----------
    hub : dict | None
        Dicionário de pressupostos (carregado de m6_hub_assumptions.yaml).
        Se None, carrega automaticamente via load().
    n_simulations : int
        Número de iterações (recomendado: 1 000–5 000).
    irc_taxa : float | None
        Taxa combinada de IRC. Se None, usa o valor do YAML (por defeito 22,5 %).
    distributions : dict | None
        Override de parâmetros por driver. Mesma estrutura de DEFAULT_DISTRIBUTIONS.
        Apenas as chaves fornecidas são substituídas; as restantes mantêm o defeito.
    seed : int | None
        Seed do gerador aleatório (para reprodutibilidade). None = seed aleatório.

    Retorna
    -------
    dict com:
      val          — estatísticas e histograma do VAL (€)
      tir          — estatísticas da TIR (exclui iterações sem convergência)
      correlacoes_val — Pearson r entre cada driver e o VAL (ranking de risco)
      distribuicoes_usadas — parâmetros efetivos usados na simulação
      parametros_base      — caso base determinístico para referência
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.225))
    wacc_base = float(via["wacc"])
    capex_base = float(proj["capex"]["base"])

    # ── Resolver distribuições efetivas ─────────────────────────────────────
    dist_efetivas: dict[str, dict] = {}
    for drv in DRIVERS:
        cfg = dict(DEFAULT_DISTRIBUTIONS[drv])
        if distributions and drv in distributions:
            cfg.update(distributions[drv])
        dist_efetivas[drv] = cfg

    # Calcular limites do CAPEX em runtime (dependem do capex_base do YAML)
    if dist_efetivas["capex"]["min"] is None:
        dist_efetivas["capex"]["min"] = capex_base * 0.85
        dist_efetivas["capex"]["mode"] = capex_base
        dist_efetivas["capex"]["max"] = capex_base * 1.15

    # ── Caso base (determinístico, para referência) ──────────────────────────
    res_base = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc_base)
    val_base = float(res_base["vpl"])   # viabilidade_hub devolve a chave "vpl" internamente
    tir_base = res_base.get("tir")

    # ── Gerar amostras antecipadamente (mais eficiente que amostrar no loop) ─
    rng = np.random.default_rng(seed)
    samples_arr: dict[str, np.ndarray] = {
        drv: _draw_samples(rng, dist_efetivas[drv], n_simulations)
        for drv in DRIVERS
    }

    # ── Loop principal ────────────────────────────────────────────────────────
    val_list: list[float] = []
    tir_list: list[float | None] = []
    driver_samples: dict[str, list[float]] = {d: [] for d in DRIVERS}

    for i in range(n_simulations):
        s = {drv: float(samples_arr[drv][i]) for drv in DRIVERS}
        for drv in DRIVERS:
            driver_samples[drv].append(s[drv])

        h_mut, wacc_i = _apply_sample(hub, s)
        res = viabilidade_hub(h_mut, irc_taxa=irc_taxa, wacc=wacc_i)

        val_list.append(float(res["vpl"]))
        tir_list.append(res.get("tir"))  # None quando IRR não converge

    # ── Estatísticas VAL ─────────────────────────────────────────────────────
    val_arr = np.array(val_list, dtype=float)
    pcts = [5, 10, 25, 50, 75, 90, 95]

    val_stats: dict[str, Any] = {
        "mean": float(np.mean(val_arr)),
        "std": float(np.std(val_arr, ddof=1)),
        **_percentiles(val_arr, pcts),
        "min": float(np.min(val_arr)),
        "max": float(np.max(val_arr)),
        # Probabilidade de viabilidade: P(VAL > 0)
        "prob_positivo": float(np.mean(val_arr > 0)),
        "histogram": _build_histogram(val_arr),
    }

    # ── Estatísticas TIR ─────────────────────────────────────────────────────
    tir_validas = [t for t in tir_list if t is not None]
    n_validas = len(tir_validas)
    n_invalidas = n_simulations - n_validas

    if n_validas >= 2:
        tir_arr = np.array(tir_validas, dtype=float)
        tir_stats: dict[str, Any] = {
            "mean": float(np.mean(tir_arr)),
            "std": float(np.std(tir_arr, ddof=1)),
            **_percentiles(tir_arr, pcts),
            # P(TIR > wacc_base): usa o WACC base como limiar fixo para interpretabilidade
            "prob_supera_wacc_base": float(np.mean(tir_arr > wacc_base)),
        }
    else:
        tir_stats = {k: None for k in ["mean", "std"] + [f"p{p}" for p in pcts] + ["prob_supera_wacc_base"]}

    tir_stats["n_validas"] = n_validas
    tir_stats["n_invalidas"] = n_invalidas

    # ── Correlações de Pearson: driver → VAL ────────────────────────────────
    # r > 0 → driver aumenta VAL; r < 0 → driver reduz VAL.
    # Ordenado por |r| decrescente (maior impacto primeiro).
    correlacoes_raw = {
        drv: _pearson(driver_samples[drv], val_list)
        for drv in DRIVERS
    }
    correlacoes_val = dict(
        sorted(correlacoes_raw.items(), key=lambda kv: abs(kv[1]), reverse=True)
    )

    return {
        "n_simulations": n_simulations,
        "irc_taxa": float(irc_taxa),
        "val": val_stats,
        "tir": tir_stats,
        "correlacoes_val": {k: float(v) for k, v in correlacoes_val.items()},
        # Parâmetros efetivos usados — útil para o frontend mostrar os ranges
        "distribuicoes_usadas": {
            drv: {k: (float(v) if isinstance(v, (int, float)) and v is not None else v)
                  for k, v in cfg.items()}
            for drv, cfg in dist_efetivas.items()
        },
        # Caso base determinístico para comparação
        "parametros_base": {
            "val_base": val_base,
            "tir_base": float(tir_base) if tir_base is not None else None,
            "wacc_base": float(wacc_base),
            "capex_base": float(capex_base),
            "irc_taxa": float(irc_taxa),
        },
    }
