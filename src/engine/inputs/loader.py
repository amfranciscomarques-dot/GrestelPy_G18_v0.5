"""
Módulo: inputs/loader.py — Carregamento Agregado dos Dados do Modelo Financeiro Grestel
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Este módulo implementa o padrão de carregamento em camadas de dados financeiros.
Realiza:
  1. Leitura sequencial dos ficheiros YAML (bases de dados estruturadas);
  2. Agregação e normalização dos dados financeiros por ano civil;
  3. Aplicação de cenários (Base, Upside, Downside) através de overrides estruturados;
  4. Retorno de três estruturas consolidadas: Assumptions, Base2024, Schedules.

LÓGICA FINANCEIRA:
- Base Financeira: dados de referência (2024 real e projetos 2025-2029);
- Cenários: variações nas hipóteses de crescimento (volume, preço, custos);
  - Upside: cenário otimista (5% crescimento vendas em volume e preço);
  - Base: cenário central (sem variações);
  - Downside: cenário pessimista (crescimento moderado 1-2% em vendas).
- Subsidiárias: dados específicos da Ecogres e Hub Logístico (opcionais).

FLUXO:
  load() → carrega YAMLs → normaliza por ano → aplica cenário override → retorna estruturas
"""

from __future__ import annotations

from .custom_scenarios import load_custom_scenarios
from .models import Assumptions, Base2024, Schedules
from .paths import (
    ASSUMPTIONS_FILE,
    BASE2024_FILE,
    CUSTOS_2025_FILE,
    CUSTOS_2026_2029_FILE,
    ECOGRES_ASSUMPTIONS_FILE,
    HUB_ASSUMPTIONS_FILE,
    MACRO_2025_FILE,
    MACRO_2026_2029_FILE,
    MERCADORIAS_FILE,
    MERCADORIAS_2024_FILE,
    MIX_2024_FILE,
    MIX_2025_FILE,
    PRODUTOS_FILE,
    PRODUTOS_2024_FILE,
    SCHEDULES_FILE,
    VENDAS_2025_FILE,
    VENDAS_2026_2029_FILE,
)
from .yaml_io import (
    _deep_update,
    _load_yaml_layers,
    _normalizar_chaves_ano,
    _normalizar_mercadorias,
    _yaml_load,
)


# OVERRIDES POR CENÁRIO: Variações aplicadas sobre o cenário Base
# Conceito: cada cenário modifica as hipóteses de crescimento (drivers) de forma coerente.
# Os overrides são mesclados com os dados base usando _deep_update (merge recursivo).
#
# NOTAÇÃO:
#   - "base_2025": refere-se ao período janeiro-setembro 2025 (9 meses)
#   - Anos 2026-2029: períodos completos (12 meses por ano)
#
# CENÁRIO UPSIDE (Otimista):
#   - Crescimento em volume de vendas: 5% a.a. em 2025-2028, reduzindo a 4% em 2029
#   - Crescimento em preço de vendas: 5% a.a. em 2025-2026, moderando para 3% em 2029
#   - Crescimento FSE (Fornecimentos e Serviços Externos): 4% em 2028-2029
#
# CENÁRIO BASE (Central):
#   - Sem variações: mantém os dados como definidos nos YAML
#
# CENÁRIO DOWNSIDE (Pessimista):
#   - Crescimento em volume de vendas: 2% a.a. em 2025-2027, desacelerando a 1% em 2028-2029
#   - Crescimento em preço de vendas: apenas 1% a.a. (pressure de concorrência / inflação contida)
#   - Crescimento FSE: 4% em 2025-2027, acelerando a 6% em 2028-2029 (custos operacionais ascendentes)
#
# ---------------------------------------------------------------------------
# Overrides de cenário — SPREADS REAIS (Filosofia B)
#
# Os valores abaixo são spreads reais acima da inflação.
# O engine compõe a inflação em runtime: nominal = (1+inf)×(1+real)−1
#
# Volume é grandeza física — valores directos (não compostos com inflação).
#
# Conversão de referência (nominal → real):
#   real = (1+nominal)/(1+inflação) − 1
#   com inflações: 2025≈2.2%, 2026=2.0%, 2027=1.8%, 2028=1.7%, 2029=1.6%
# ---------------------------------------------------------------------------
_SCENARIO_OVERRIDES: dict[str, dict] = {
    "Base": {},
    "Upside": {
        # Volume: directo (grandeza física)
        "crescimento_volume_vendas": {
            "base_2025": 0.05,
            2026: 0.05,
            2027: 0.05,
            2028: 0.05,
            2029: 0.04,
        },
        # PVU: spreads reais — (5%−2.2%)/1.022≈2.7%, (5%−2.0%)/1.02≈2.9%, etc.
        "crescimento_pvu_vendas": {
            "base_2025": 0.027,
            2026: 0.029,
            2027: 0.022,
            2028: 0.023,
            2029: 0.014,
        },
        # FSE: spread real apenas nos anos com pressão extra
        "crescimento_fse": {
            2028: 0.023,
            2029: 0.024,
        },
    },
    "Downside": {
        # Volume: directo
        "crescimento_volume_vendas": {
            "base_2025": 0.02,
            2026: 0.02,
            2027: 0.02,
            2028: 0.01,
            2029: 0.01,
        },
        # PVU: spread real negativo — preço não acompanha inflação
        "crescimento_pvu_vendas": {
            "base_2025": -0.012,
            2026: -0.010,
            2027: -0.008,
            2028: -0.007,
            2029: -0.006,
        },
        # FSE: spread real positivo — custos sobem acima da inflação
        "crescimento_fse": {
            "base_2025": 0.018,
            2026: 0.020,
            2027: 0.022,
            2028: 0.042,
            2029: 0.043,
        },
    },
    "Hub_Ativo": {
        # DR consolidada com todos os impactos do hub (poupança pessoal/FSE/CMVMC + PT2030)
        "hub_logistico": {
            "incluir_hub": True,
        },
    },
    "Stress": {
        # Volume: directo (contracção real)
        "crescimento_volume_vendas": {
            "base_2025": -0.02,
            2026: 0.00,
            2027: 0.01,
            2028: 0.02,
            2029: 0.02,
        },
        # PVU: spread real muito negativo — incapacidade de repercutir inflação
        "crescimento_pvu_vendas": {
            "base_2025": -0.022,
            2026: -0.010,
            2027: -0.008,
            2028: -0.007,
            2029:  0.004,
        },
        # FSE: spread real elevado — choque energético acima da inflação geral
        "crescimento_fse": {
            "base_2025": 0.037,
            2026: 0.029,
            2027: 0.031,
            2028: 0.042,
            2029: 0.043,
        },
        # Pessoal: pressão salarial acima da inflação
        "crescimento_pessoal": {
            "base_2025": 0.027,
            2026: 0.029,
            2027: 0.022,
            2028: 0.023,
            2029: 0.033,
        },
    },
}

CENARIOS = list(_SCENARIO_OVERRIDES.keys())


def load(cenario: str = "Base"):
    """
    Função Principal: Carrega e consolida os dados financeiros do modelo.

    PARÂMETRO:
      cenario (str): Um de {'Base', 'Upside', 'Downside'}. Define qual conjunto de
                     variações de crescimento aplicar sobre os dados base.

    RETORNA:
      tuple[Assumptions, Base2024, Schedules]: Três estruturas principais:
        1. Assumptions: hipóteses operacionais e financeiras (2025-2029, + cenário);
        2. Base2024: dados reais de 2024 (ponto de partida para projeções);
        3. Schedules: calendários plurianuais de valores (juros, depreciação, etc.).

    FLUXO INTERNO:

    PASSO 1: Carregamento e mesclagem de pressupostos (9 YAML em camadas)
      - MACRO_2025_FILE: inflação e câmbio EUR/USD — granularidade mensal 2025
      - MACRO_2026_2029_FILE: inflação e câmbio EUR/USD — granularidade anual 2026-2029
      - VENDAS_2025_FILE: pressupostos de vendas 2025
      - VENDAS_2026_2029_FILE: pressupostos de vendas 2026-2029
      - CUSTOS_2025_FILE: pressupostos de custos 2025
      - CUSTOS_2026_2029_FILE: pressupostos de custos 2026-2029
      - MIX_2024_FILE: mix real 2024 (base histórica de mercado/canal)
      - MIX_2025_FILE: mix planeamento 2025 (actualizado mensalmente)
      - ASSUMPTIONS_FILE: globais — fiscal, prazos, pessoal, ESG, sazonalidade
      → Resultado: dicionário consolidado de hipóteses

    PASSO 2: Carregamento de catálogos (opcionais)
      - PRODUTOS_FILE: lista e características de produtos (margem, cost, etc.)
      - MERCADORIAS_FILE: arquivo de mercadorias com estrutura de margem progressiva
      → Resultado: dois dicionários para lookup durante cálculos

    PASSO 3: Carregamento de dados base 2024
      - BASE2024_FILE: saldos iniciais de contas (caixa, crédito clientes, fornecedores)
      - SCHEDULES_FILE: tabelas plurianuais pré-calculadas (plano de financiamento,
                       calendário de depreciação, calendário de juros, etc.)
      → Resultado: dados "às linhas" de base para consolidação

    PASSO 4: Carregamento de subsidiárias (opcionais)
      - Ecogres: pressupostos específicos de Ecogres (se ativa)
      - Hub Logístico: pressupostos específicos do Hub M6 (se ativo)
      → Resultado: dados mesclados em assumptions["ecogres"] e assumptions["hub_logistico"]

    PASSO 5: Aplicação do cenário
      - Busca os overrides de crescimento em _SCENARIO_OVERRIDES[cenario]
      - Mescla recursivamente (crescimento volume/preço vendas, FSE)
      → Resultado: assumptions finalizadas com cenário aplicado

    PASSO 6: Retorno das três estruturas
      - Assumptions com flag cenario (p/ rastreabilidade)
      - Base2024 com referência aos produtos/mercadorias
      - Schedules para acesso a valores plurianuais pré-calculados
    """
    _custom = load_custom_scenarios().get("scenarios", {})
    if cenario not in _SCENARIO_OVERRIDES and cenario not in _custom:
        all_opts = list(_SCENARIO_OVERRIDES) + list(_custom)
        raise ValueError(f"Cenário '{cenario}' inválido. Opções: {all_opts}")

    # PASSO 1: Mesclagem em camadas de ficheiros de pressupostos
    # _load_yaml_layers aplica merge sucessivo (primeira sobrescreve, última ganha)
    assumptions = _normalizar_chaves_ano(
        _load_yaml_layers([
            MACRO_2025_FILE,                  # Macro 2025 — inflação/câmbio mensal
            MACRO_2026_2029_FILE,             # Macro 2026-2029 — inflação/câmbio anual
            VENDAS_2025_FILE,                 # Pressupostos vendas 2025
            VENDAS_2026_2029_FILE,            # Pressupostos vendas 2026-2029
            CUSTOS_2025_FILE,                 # Pressupostos custos 2025
            CUSTOS_2026_2029_FILE,            # Pressupostos custos 2026-2029
            MIX_2024_FILE,                    # Mix real 2024 (base histórica)
            MIX_2025_FILE,                    # Mix planeamento 2025
            ASSUMPTIONS_FILE,                 # Globais — fiscal, prazos, pessoal, ESG
        ])
    )

    # PASSO 2: Carregamento de catálogos (merge master + histórico 2024)
    produtos_master = _yaml_load(PRODUTOS_FILE, required=False) or {}
    produtos_2024   = _yaml_load(PRODUTOS_2024_FILE, required=False) or {}
    produtos = _normalizar_chaves_ano(_deep_update(produtos_master, produtos_2024))

    mercadorias_master = _yaml_load(MERCADORIAS_FILE, required=False) or {}
    mercadorias_2024   = _yaml_load(MERCADORIAS_2024_FILE, required=False) or {}
    mercadorias = _normalizar_mercadorias(
        _normalizar_chaves_ano(_deep_update(mercadorias_master, mercadorias_2024))
    )

    # PASSO 3: Base 2024 e Schedules
    base2024 = _normalizar_chaves_ano(_yaml_load(BASE2024_FILE))
    schedules = _normalizar_chaves_ano(_yaml_load(SCHEDULES_FILE))

    # PASSO 4: Carregamento de subsidiárias (opcionais, merge se presentes)
    ecogres_data = _normalizar_chaves_ano(
        _yaml_load(ECOGRES_ASSUMPTIONS_FILE, required=False)
    )
    hub_data = _normalizar_chaves_ano(
        _yaml_load(HUB_ASSUMPTIONS_FILE, required=False)
    )

    if ecogres_data:
        assumptions.setdefault("ecogres", ecogres_data)
    if hub_data:
        assumptions.setdefault("hub_logistico", hub_data)

    # PASSO 5: Aplicação do cenário (override de crescimentos ou parâmetros custom)
    if cenario in _SCENARIO_OVERRIDES:
        overrides = _SCENARIO_OVERRIDES[cenario]
    else:
        overrides = _custom.get(cenario, {}).get("overrides", {})
    if overrides:
        assumptions = _deep_update(assumptions, overrides)

    # PASSO 6: Retorno das três estruturas consolidadas
    return (
        Assumptions(
            assumptions,
            cenario=cenario,
            produtos_raw=produtos,
            mercadorias_raw=mercadorias,
        ),
        Base2024(
            base2024,
            produtos_raw=produtos,
            mercadorias_raw=mercadorias,
        ),
        Schedules(schedules),
    )
