"""Modelos de dados carregados dos YAML."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .constants import MERCADORIAS, PRODUTOS, YEARS
from .yaml_io import _alias_mercadoria


Cenario = str


@dataclass
class Assumptions:
    raw: dict[str, Any]
    cenario: Cenario = "Base"
    produtos_raw: dict[str, Any] | None = None
    mercadorias_raw: dict[str, Any] | None = None

    def get(self, *path, default=None):
        """Obtém valor aninhado de raw."""
        d: Any = self.raw

        for p in path:
            if d is None or not isinstance(d, dict):
                return default
            d = d.get(p)

        return d if d is not None else default

    @property
    def impostos(self):
        return self.raw["impostos"]

    @property
    def prazos(self):
        return self.raw["prazos"]

    @property
    def caixa(self):
        return self.raw["caixa"]

    @property
    def distribuicao(self):
        return self.raw["distribuicao_resultados"]

    @property
    def macro(self):
        return self.raw["macro"]

    @property
    def mercados(self):
        return self.raw.get("mercados", {})

    @property
    def fse_params(self):
        return self.raw.get("fse", {})

    @property
    def pessoal_params(self):
        return self.raw.get("pessoal", {})

    @property
    def triggers(self):
        return self.raw.get("triggers", {})

    @property
    def plurianual(self):
        return self.raw.get("plurianual_factors", {})

    @property
    def ecogres(self):
        return self.raw.get("ecogres", {})

    @property
    def hub_logistico(self):
        return self.raw.get("hub_logistico", {})

    @property
    def esg(self):
        return self.raw.get("esg", {})

    @property
    def product_families(self) -> dict[str, Any]:
        return (self.produtos_raw or {}).get("product_families", {})

    @property
    def raw_materials(self) -> dict[str, Any]:
        return (self.produtos_raw or {}).get("raw_materials", {})

    @property
    def merchandise_families(self) -> dict[str, Any]:
        return (self.mercadorias_raw or {}).get("merchandise_families", {})

    @property
    def produtos(self) -> list[str]:
        return list(self.product_families.keys()) or PRODUTOS

    @property
    def mercadorias(self) -> list[str]:
        return list(self.merchandise_families.keys()) or MERCADORIAS

    @property
    def pvu_base_produtos(self) -> dict[str, float]:
        return {
            p: float(v.get("pvu_base_2024", 0.0))
            for p, v in self.product_families.items()
        }

    @property
    def pvu_base_mercadorias(self) -> dict[str, float]:
        return {
            m: float(v.get("pvu_base_2024", 0.0))
            for m, v in self.merchandise_families.items()
        }

    @property
    def mix_produtos_2024(self) -> dict[str, float]:
        return {
            p: float(v.get("sales_mix_2024", 0.0))
            for p, v in self.product_families.items()
        }

    @property
    def mix_mercadorias_2024(self) -> dict[str, float]:
        return {
            m: float(v.get("sales_mix_2024", 0.0))
            for m, v in self.merchandise_families.items()
        }

    @property
    def cresc_producao(self):
        return self.raw.get(
            "crescimento_producao",
            self.raw.get("crescimento_volume_vendas", {}),
        )

    @property
    def mix_mercado_produto(self) -> dict:
        """Mix por mercado por produto, com suporte a _default."""
        raw = self.raw.get("mix_mercado_produto") or {}
        default = raw.get("_default", {})
        return {p: raw.get(p, default) for p in self.produtos}

    @property
    def mix_canal_produto(self) -> dict:
        """Mix por canal por produto × mercado, com suporte a _default."""
        raw = self.raw.get("mix_canal_produto") or {}
        default = raw.get("_default", {})
        return {p: raw.get(p, default) for p in self.produtos}

    @property
    def sazonalidade(self):
        if "sazonalidade" in self.raw:
            return self.raw["sazonalidade"]

        return {
            m: bloco.get("sazonalidade", [])
            for m, bloco in self.mercados.items()
        }

    @property
    def mix_mercado_canal(self):
        if "mix_mercado_canal" in self.raw:
            return self.raw["mix_mercado_canal"]

        mix_2024 = self.raw.get("mix_canais_2024")
        if isinstance(mix_2024, dict):
            return {
                m: mix_2024
                for m in self.mercados.keys()
            }

        return {
            m: bloco.get("canais", {})
            for m, bloco in self.mercados.items()
        }

    @property
    def cenarios_mensais(self):
        """Cenários mensais.

        Se o YAML não tiver cenarios_mensais, constrói uma estrutura compatível
        com os nomes usados pela API e pelos módulos mensais.
        Mapeia as novas chaves (crescimento_*) para os nomes legados.
        """
        return {
            "Base": {
                "volume_vendas": self.raw.get("crescimento_volume_vendas", {}),
                "preco_vendas": self.raw.get("crescimento_preco_vendas", {}),
                "pvu_produto_crescimento": self.raw.get("pvu_produto_crescimento", {}),
                "pvu_mercadorias_crescimento": self.raw.get(
                    "pvu_mercadorias_crescimento",
                    {},
                ),
                "fse": self.raw.get("crescimento_fse", {}),
                "pessoal": self.raw.get("crescimento_pessoal", {}),
                "custo_mercadorias": self.raw.get("crescimento_custo_mercadorias", {}),
                "mpsc": self.raw.get("crescimento_pcu_mpsc", {}),
            }
        }

    def cenario_block(self) -> dict:
        """Obtém bloco do cenário activo."""
        return self.cenarios_mensais.get(
            self.cenario,
            self.cenarios_mensais.get("Base", {}),
        )

    def _driver_block(self, key: str) -> dict:
        """Obtém bloco de driver, considerando aliases."""
        aliases = {
            "volume_vendas": "crescimento_volume_vendas",
            "preco_vendas": "crescimento_preco_vendas",
            "fse": "crescimento_fse",
            "pessoal": "crescimento_pessoal",
            "custo_mercadorias": "crescimento_custo_mercadorias",
            "mpsc": "crescimento_pcu_mpsc",
        }

        block = self.cenario_block().get(key)

        if isinstance(block, dict) and ("base_2025" in block or "annual_2025" in block):
            return block

        raw_key = aliases.get(key, key)

        return self.raw.get(raw_key, block if isinstance(block, dict) else {}) or {}

    def cresc_2026_2029(self, key: str) -> Dict[int, float]:
        block = self._driver_block(key)

        return {
            y: float((block or {}).get(y, 0.0))
            for y in YEARS[1:]
        }

    def cresc_2025_anual(self, key: str) -> float:
        block = self._driver_block(key)

        return float((block or {}).get("base_2025", (block or {}).get("annual_2025", 0.0)))

    def cresc_2026_2029_pvu(self, produto: str) -> Dict[int, float]:
        produto = produto.strip()

        bloco = self.raw.get("pvu_produto_crescimento", {}).get(produto, {})

        if not bloco:
            bloco = (
                self.cenario_block()
                .get("pvu_produto_crescimento_2026_2029", {})
                .get(produto, {})
            )

        return {
            y: float((bloco or {}).get(y, 0.0))
            for y in YEARS[1:]
        }

    def cresc_2025_pvu_produto(self, produto: str) -> float:
        bloco = self.raw.get("pvu_produto_crescimento", {}).get(produto, {})

        return float(
            (bloco or {}).get("base_2025", (bloco or {}).get("annual_2025", 0.0))
        )

    def cresc_2026_2029_pvu_mercadoria(self, mercadoria: str) -> Dict[int, float]:
        mercadoria = _alias_mercadoria(mercadoria.strip())

        bloco = self.raw.get("pvu_mercadorias_crescimento", {}).get(mercadoria, {})

        if not bloco:
            for k, v in self.raw.get("pvu_mercadorias_crescimento", {}).items():
                if _alias_mercadoria(k) == mercadoria:
                    bloco = v or {}
                    break

        return {
            y: float((bloco or {}).get(y, 0.0))
            for y in YEARS[1:]
        }

    def cresc_2025_pvu_mercadoria(self, mercadoria: str) -> float:
        mercadoria = _alias_mercadoria(mercadoria.strip())

        bloco = self.raw.get("pvu_mercadorias_crescimento", {}).get(mercadoria, {})

        if not bloco:
            for k, v in self.raw.get("pvu_mercadorias_crescimento", {}).items():
                if _alias_mercadoria(k) == mercadoria:
                    bloco = v or {}
                    break

        return float(
            (bloco or {}).get("base_2025", (bloco or {}).get("annual_2025", 0.0))
        )

    def taxa_pessoal_2025(self) -> float:
        return float(self.pessoal_params.get("taxa_cresc_custo_2025", 0.0))

    def inflacao_mensal_2025(self) -> list[float]:
        return self.macro.get("inflacao", {}).get("mensal_2025", [0.023] * 12)

    def inflacao_anual(self, ano: int) -> float:
        if ano == 2025:
            vals = self.inflacao_mensal_2025()
            return float(sum(vals) / len(vals)) if vals else 0.023

        return float(
            self.macro.get("inflacao", {}).get("anual", {}).get(ano, 0.023)
        )

    def eur_usd_mensal_2025(self) -> list[float]:
        return self.macro.get("eur_usd", {}).get("mensal_2025", [1.08] * 12)

    def eur_usd_anual(self, ano: int) -> float:
        if ano == 2025:
            vals = self.eur_usd_mensal_2025()
            return float(sum(vals) / len(vals)) if vals else 1.08

        return float(
            self.macro.get("eur_usd", {}).get("anual", {}).get(ano, 1.08)
        )


@dataclass
class Base2024:
    raw: dict[str, Any]
    produtos_raw: dict[str, Any] | None = None
    mercadorias_raw: dict[str, Any] | None = None

    @property
    def balanco(self):
        return self.raw["balanco_abertura"]

    @property
    def vendas_mercado(self):
        return self.raw["vendas_2024_por_mercado"]

    @property
    def fse_detalhe(self):
        return self.raw["fse_detalhe_2024"]

    @property
    def saldos(self):
        return self.raw["saldos_historicos"]

    @property
    def invest_fin(self):
        return self.raw["investimento_financiamento_2024"]

    @property
    def financiamento(self):
        return self.raw["financiamento_2024"]

    @property
    def totais(self):
        return self.raw["totais_2024"]

    @property
    def outros_rendimentos(self):
        return self.raw["outros_rendimentos_2024"]

    @property
    def materias_primas(self):
        return self.raw.get(
            "materias_primas_2024",
            (self.produtos_raw or {}).get("raw_materials", {}),
        )

    @property
    def mercadorias(self):
        return self.raw.get(
            "mercadorias_2024",
            (self.mercadorias_raw or {}).get("merchandise_families", {}),
        )

    @property
    def pvu_base(self):
        if "pvu_base_2024" in self.raw:
            return self.raw["pvu_base_2024"]

        pvu = {}

        for p, bloco in (self.produtos_raw or {}).get("product_families", {}).items():
            pvu[p] = bloco.get("pvu_base_2024", 0.0)

        for m, bloco in (self.mercadorias_raw or {}).get("merchandise_families", {}).items():
            pvu[m] = bloco.get("pvu_base_2024", 0.0)

        return pvu


@dataclass
class Schedules:
    raw: dict[str, Any]

    @property
    def investimento(self):
        return self.raw["investimento"]

    @property
    def financiamento(self):
        return self.raw["financiamento"]

    @property
    def eoep(self):
        return self.raw["eoep_saldos"]

    @property
    def reference_dr(self):
        return self.raw["reference_dr"]

    @property
    def reference_balanco(self):
        return self.raw["reference_balanco"]

    @property
    def plurianual_AB(self):
        return self.raw["plurianual_factors_AB"]
