# GrestelPy — Project Tree

> Estado actual: Engine v0.5+ · actualizado 2026-05-14

```
GrestelPy_G18/
├── server.py                              ← FastAPI entry point (porta 8000)
├── pyproject.toml                         ← Configuração pacote (Python ≥ 3.10)
├── requirements.txt                       ← Dependências runtime
├── .gitignore
│
├── docs/
│   ├── PEF_2025-26_Resumo_M3_M6_OE4.md  ← Enquadramento académico completo
│   ├── guia_docentes.md                  ← Documentação endpoints e outputs
│   └── project_tree.md                   ← Este ficheiro
│
├── interface/                             ← Interface web (HTML/JS/CSS)
│
├── src/
│   ├── api/                              ← Camada HTTP (FastAPI)
│   │   ├── __init__.py
│   │   ├── constants.py                  ← Mapeamento famílias de produto
│   │   ├── schemas.py                    ← Schemas Pydantic (request/response)
│   │   ├── serializers.py                ← Serialização JSON + helpers FSE mensal
│   │   ├── summary.py                    ← Geração de relatórios sumário
│   │   └── routes/
│   │       ├── __init__.py               ← Agregador de rotas
│   │       ├── assumptions.py            ← GET/POST pressupostos
│   │       ├── pressupostos.py           ← Gestão orçamentos
│   │       ├── scenarios.py              ← Execução de cenários + /api/run
│   │       ├── custom_scenarios.py       ← CRUD cenários customizados
│   │       ├── rolling.py                ← Rolling forecast mensal
│   │       ├── hub.py                    ← Projecto Hub Logístico (M6)
│   │       └── ecogres.py                ← Subsidiária Ecogres
│   │
│   └── engine/                           ← Motor de cálculo financeiro
│       ├── __init__.py
│       ├── config.py
│       │
│       ├── inputs/                       ← Carregamento de dados e configuração
│       │   ├── __init__.py               ← Exporta: load, Assumptions, Base2024, Schedules, MESES, …
│       │   ├── loader.py                 ← Orquestrador YAML + cenários (_SCENARIO_OVERRIDES)
│       │   ├── models.py                 ← Dataclasses: Assumptions, Base2024, Schedules
│       │   ├── paths.py                  ← Caminhos absolutos para todos os YAML
│       │   ├── constants.py              ← MESES, ANOS, PRODUTOS, MERCADORIAS
│       │   ├── yaml_io.py                ← I/O, normalização e merge YAML
│       │   └── custom_scenarios.py       ← CRUD cenários customizados
│       │
│       ├── data/                         ← Dados de configuração (YAML)
│       │   ├── historico/
│       │   │   └── 2024/
│       │   │       ├── base.yaml         ← Balanço, DR, DFC reais 2024 (imutável)
│       │   │       ├── mix.yaml          ← Mix real 2024 por mercado/canal
│       │   │       ├── produtos.yaml     ← sales_mix e pvu_base 2024 por produto
│       │   │       └── mercadorias.yaml  ← sales_mix, pvu_base, mix_regiao, sazonalidade 2024
│       │   │
│       │   ├── pressupostos/
│       │   │   ├── globais.yaml          ← Fiscal (IVA/IRC/SS/TSU), prazos, caixa, distribuição, ESG
│       │   │   ├── 2025/
│       │   │   │   ├── macro.yaml        ← Inflação mensal 2025, EUR/USD mensal 2025
│       │   │   │   ├── vendas.yaml       ← Crescimento volume/PVU por produto 2025
│       │   │   │   ├── custos.yaml       ← FSE, pessoal, CMVMC 2025
│       │   │   │   └── mix.yaml          ← Sazonalidade e mix planeamento 2025
│       │   │   └── 2026_2029/
│       │   │       ├── macro.yaml        ← Inflação anual 2026-29, EUR/USD anual
│       │   │       ├── vendas.yaml       ← Crescimento volume/PVU plurianual
│       │   │       └── custos.yaml       ← FSE, pessoal, CMVMC plurianual
│       │   │
│       │   ├── master/
│       │   │   ├── produtos.yaml         ← Estrutura de custos estável (cip, detalhe_mp)
│       │   │   ├── mercadorias.yaml      ← Custo de compra (pcu) por família
│       │   │   └── fse_rubricas.yaml     ← Contrato 14 rubricas FSE
│       │   │
│       │   ├── computed/
│       │   │   └── schedules.yaml        ← Gerado: investimento, financiamento, EOEP saldos
│       │   │
│       │   ├── cenarios/
│       │   │   └── custom_scenarios.yaml ← Cenários customizados persistidos
│       │   │
│       │   └── subsidiarias/
│       │       ├── ecogres/
│       │       │   └── ecogres_assumptions.yaml
│       │       └── hub_logistico/
│       │           └── m6_hub_assumptions.yaml
│       │
│       ├── operacional/                  ← Módulos operacionais (DR + mensais)
│       │   ├── __init__.py
│       │   ├── vendas.py                 ← VN anual e mensal (vendas_mensais_2025) ← MENSAL
│       │   ├── produção.py               ← Planeamento de produção anual
│       │   ├── inventarios.py            ← Saldos de inventário anual
│       │   ├── cmvmc.py                  ← CMVMC anual (produtos + mercadorias)
│       │   ├── pessoal.py                ← Remunerações, encargos, detalhe contabilístico e departamental
│       │   ├── fornecedores.py           ← Saldo de fornecedores anual
│       │   ├── clientes.py               ← Saldo de clientes anual
│       │   └── fse.py                    ← FSE anual + fse_detalhe_mensal_2025 ← MENSAL
│       │
│       ├── investimento/
│       │   ├── __init__.py
│       │   ├── investimento.py           ← CAPEX e calendário de investimento
│       │   └── viabilidade.py            ← VAN, TIR, Payback, ROIC
│       │
│       ├── financiamento/
│       │   ├── __init__.py
│       │   ├── financiamento.py          ← Empréstimos e mapas de dívida
│       │   └── tesouraria.py             ← build_eoep_mensal ← MENSAL
│       │                                   build_tesouraria_mensal ← MENSAL
│       │                                   build_dr_mensal ← MENSAL
│       │                                   rolling_update
│       │
│       ├── demonstracoes/
│       │   ├── __init__.py
│       │   ├── statements.py             ← Orquestrador: DR → Balanço (df_eoep_mensal) → DFC
│       │   ├── dr.py                     ← build_dr (anual 2024-2029)
│       │   ├── balanco.py                ← build_balanco (recebe df_eoep_mensal opcional)
│       │   ├── dfc.py                    ← build_dfc (anual)
│       │   ├── nfm.py                    ← NFM anual
│       │   └── rolling_forecast_mensal.py← Balanço+DFC+NFM mensais integrados
│       │
│       ├── modelo/                       ← Orquestração principal
│       │   ├── __init__.py
│       │   ├── model.py                  ← run_model() → dfs com todos os outputs
│       │   │                               Outputs mensais 2025: eoep_mensal_2025,
│       │   │                               vendas_mensal_2025, dr_mensal_2025,
│       │   │                               tesouraria_mensal_2025, fse_detalhe_mensal_2025
│       │   ├── eoep.py                   ← eoep_calendario_mensal ← MENSAL (bottom-up 2025)
│       │   │                               eoep_anual (df_mensal= para derivar saldos 2025)
│       │   ├── kpis.py                   ← KPIs e rácios financeiros
│       │   ├── pressupostos.py           ← Análise de orçamentos
│       │   └── sensitivity.py            ← Análise de sensibilidade (tornado)
│       │
│       └── projetos/
│           ├── __init__.py
│           ├── ecogres.py                ← Modelo financeiro Ecogres
│           └── hub_logistico.py          ← Modelo financeiro Hub M6 (VAN/TIR)
│           (nota: pasta projetos/ está em engine/projetos/ — importada como engine.projetos)
│
└── tests/
    ├── __init__.py
    ├── conftest.py                       ← Fixtures pytest (cenário Base pré-carregado)
    ├── test_api_detail.py
    ├── test_api_model.py
    ├── test_api_reconcil.py
    ├── test_api_structure.py
    ├── test_fse_mensal.py
    ├── test_fse_reconciliations.py
    ├── test_keys.py
    └── test_kpis_contract.py
```

---

## Fluxo de dados: YAML → `run_model` → API

```
YAML inputs
  ├── historico/2024/      ─┐
  ├── pressupostos/2025/    ├── load(cenario) ──► Assumptions
  ├── pressupostos/2026-29/ │                    Base2024
  ├── master/               │                    Schedules
  └── computed/schedules ───┘
                                    │
                                    ▼
                              run_model()
                                    │
                         ┌──────────┴──────────────────────┐
                         │ Mensais 2025 (bottom-up)         │
                         │  build_eoep_mensal()             │
                         │  vendas_mensais_2025()           │
                         │  build_dr_mensal()               │
                         │  build_tesouraria_mensal()       │
                         │  fse_detalhe_mensal_2025()       │
                         └──────────┬──────────────────────┘
                                    │ df_eoep_mensal (2025 bottom-up)
                                    ▼
                         build_statements()
                           DR → Balanço → DFC
                           (EOEP 2025 derivado do mensal)
                                    │
                                    ▼
                              dfs (dict)
                                    │
                         dataframe_to_records()
                                    │
                                    ▼
                              API JSON
```

---

## Módulos com outputs mensais de 2025

| Módulo | Função | Output |
|---|---|---|
| `engine/modelo/eoep.py` | `eoep_calendario_mensal()` | IVA, SS, IRC PPC mensal |
| `engine/operacional/vendas.py` | `vendas_mensais_2025()` | VN por produto/mercado/mês |
| `engine/operacional/fse.py` | `fse_detalhe_mensal_2025()` | 14 rubricas FSE por mês |
| `engine/financiamento/tesouraria.py` | `build_eoep_mensal()` | wrapper público do calendário EOEP |
| `engine/financiamento/tesouraria.py` | `build_dr_mensal()` | DR mensal 2025 (26 colunas) |
| `engine/financiamento/tesouraria.py` | `build_tesouraria_mensal()` | Orçamento tesouraria 2025 |
| `engine/demonstracoes/rolling_forecast_mensal.py` | `build_rolling_forecast()` | Balanço+DFC+NFM mensais |
