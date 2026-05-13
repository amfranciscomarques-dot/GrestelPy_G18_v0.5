# GrestelPy_G18 — Project Tree

```
GrestelPy_G18/
├── server.py                          ← FastAPI entry point (porta 8000)
├── pyproject.toml                     ← Configuração pacote (v0.3.0, Python ≥3.10)
├── requirements.txt                   ← Dependências runtime
├── .gitignore
│
├── docs/
│   ├── PEF_2025-26_Resumo_M3_M6_OE4.md
│   ├── guia_docentes.md
│   └── project_tree.md                ← Este ficheiro
│
├── src/
│   ├── api/                           ← Camada HTTP (FastAPI)
│   │   ├── __init__.py
│   │   ├── constants.py               ← Mapeamento famílias de produto
│   │   ├── schemas.py                 ← Schemas Pydantic (request/response)
│   │   ├── serializers.py             ← Serialização JSON
│   │   ├── summary.py                 ← Geração de relatórios sumário
│   │   └── routes/
│   │       ├── __init__.py            ← Agregador de rotas
│   │       ├── assumptions.py         ← GET/POST pressupostos
│   │       ├── pressupostos.py        ← Gestão orçamentos
│   │       ├── scenarios.py           ← Execução de cenários
│   │       ├── custom_scenarios.py    ← CRUD cenários customizados
│   │       ├── rolling.py             ← Rolling forecast mensal
│   │       ├── hub.py                 ← Projeto Hub Logístico (M6)
│   │       └── ecogres.py             ← Subsidiária Ecogres
│   │
│   └── engine/                        ← Motor de cálculo financeiro (v0.5.0)
│       ├── __init__.py
│       ├── config.py
│       │
│       ├── inputs/                    ← Carregamento de dados e configuração
│       │   ├── __init__.py
│       │   ├── loader.py              ← Orquestrador YAML + cenários
│       │   ├── models.py              ← Dataclasses (Assumptions, Base2024, Schedules)
│       │   ├── paths.py               ← Caminhos de ficheiros
│       │   ├── constants.py
│       │   ├── yaml_io.py             ← I/O e normalização YAML
│       │   └── custom_scenarios.py
│       │
│       ├── data/                      ← Dados de configuração (YAML)
│       │   ├── assumptions/
│       │   │   ├── assumptions.yaml   ← Pressupostos principais
│       │   │   └── base_financeira.yaml
│       │   ├── cenarios/
│       │   │   └── custom_scenarios.yaml
│       │   ├── contrato/
│       │   │   └── fse.yaml           ← FSE contratual
│       │   ├── drivers/
│       │   │   ├── 2025/
│       │   │   │   ├── vendas_mensal.yaml   ← Drivers vendas mensais 2025
│       │   │   │   ├── custos_mensal.yaml   ← Drivers custos mensais 2025
│       │   │   │   └── mix_mensal.yaml      ← Mix produto mensal 2025
│       │   │   └── 2026_2029/
│       │   │       ├── vendas_anual.yaml    ← Drivers vendas anuais (5 anos)
│       │   │       └── custos_anual.yaml    ← Drivers custos anuais (5 anos)
│       │   ├── historico/
│       │   │   └── 2024/
│       │   │       ├── base.yaml      ← Base financeira histórica 2024
│       │   │       └── mix.yaml       ← Mix de produto real 2024
│       │   ├── master/
│       │   │   ├── produtos.yaml      ← Mestre de produtos
│       │   │   ├── mercadorias.yaml   ← Mestre de mercadorias
│       │   │   └── schedules.yaml     ← Prazos de pagamento/recebimento
│       │   ├── mix/
│       │   │   └── mix_comercial.yaml
│       │   └── subsidiarias/
│       │       ├── ecogres/
│       │       │   └── ecogres_assumptions.yaml
│       │       └── hub_logistico/
│       │           └── m6_hub_assumptions.yaml  ← Pressupostos projeto M6
│       │
│       ├── operacional/               ← Actividades operacionais (DFC)
│       │   ├── __init__.py
│       │   ├── vendas.py              ← Cálculo de receitas
│       │   ├── producao.py            ← Planeamento de produção
│       │   ├── inventarios.py         ← Gestão de inventários
│       │   ├── cmvmc.py               ← CMVMC
│       │   ├── pessoal.py             ← Remunerações e encargos sociais
│       │   ├── fornecedores.py        ← Gestão de pagáveis
│       │   ├── clientes.py            ← Gestão de recebíveis
│       │   └── fse.py                 ← Fornecimentos e Serviços Externos
│       │
│       ├── investimento/              ← Actividades de investimento (DFC)
│       │   ├── __init__.py
│       │   ├── investimento.py        ← CAPEX e calendário de investimento
│       │   └── viabilidade.py         ← VAN, TIR, Payback, ROIC
│       │
│       ├── financiamento/             ← Actividades de financiamento (DFC)
│       │   ├── __init__.py
│       │   ├── financiamento.py       ← Empréstimos + mapas de dívida
│       │   └── tesouraria.py          ← Tesouraria mensal (rolling forecast)
│       │
│       ├── demonstracoes/             ← Demonstrações financeiras
│       │   ├── __init__.py
│       │   ├── statements.py          ← Orquestrador (DR + Balanço + DFC)
│       │   ├── dr.py                  ← Demonstração de Resultados
│       │   ├── balanco.py             ← Balanço
│       │   ├── dfc.py                 ← Demonstração de Fluxos de Caixa
│       │   └── nfm.py                 ← Necessidades de Fundo de Maneio
│       │
│       ├── modelo/                    ← Orquestração do modelo completo
│       │   ├── __init__.py
│       │   ├── model.py               ← Execução principal (run_model)
│       │   └── eoep.py                ← Estado e Outros Entes Públicos
│       │
│       ├── projetos/                  ← Subsidiária + Projeto M6
│       │   ├── __init__.py
│       │   ├── ecogres.py             ← Modelo financeiro Ecogres (subsidiária)
│       │   └── hub_logistico.py       ← Modelo financeiro Hub Logístico (Projeto M6)
│       │
│       └── analitica/                 ← Análise e KPIs
│           ├── __init__.py
│           ├── kpis.py                ← KPIs (rácios financeiros, margens, VAN/TIR)
│           ├── pressupostos.py        ← Análise de orçamentos
│           ├── rolling_forecast_mensal.py  ← Rolling forecast
│           └── sensitivity.py         ← Análise de sensibilidade
│
└── tests/                             ← Suite de testes (27 testes)
    ├── __init__.py
    ├── conftest.py                    ← Fixtures pytest (cenário Base)
    ├── test_api_detail.py
    ├── test_api_model.py
    ├── test_api_reconcil.py
    ├── test_api_structure.py
    ├── test_fse_mensal.py
    ├── test_fse_reconciliations.py
    ├── test_keys.py
    └── test_kpis_contract.py
```
