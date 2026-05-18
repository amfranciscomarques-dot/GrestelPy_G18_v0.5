# GrestelPy — G18

Motor de planeamento financeiro da empresa **Grestel** desenvolvido em Python para suporte à UC PEF (2025-26), Grupo 18, ISCA-UA.

Cobre os Momentos **M3** (Planeamento Financeiro) e **M6** (Plano de Negócios), expondo todos os outputs através de uma API REST que alimenta a interface web.

---

## Arranque rápido

### Windows (sem Python instalado)

1. Execute **`SETUP.bat`** — instala tudo automaticamente (precisa de internet, ~5 min na primeira vez)
2. Execute **`start.bat`** — abre o browser em `http://localhost:8000` automaticamente

### Linha de comandos (Python já instalado)

```bash
pip install -r requirements.txt
python server.py
```

| URL | Descrição |
|---|---|
| `http://localhost:8000/` | Interface web |
| `http://localhost:8000/docs` | Swagger UI (API interactiva) |
| `http://localhost:8000/health` | Estado do servidor |

---

## O que o sistema calcula

### Demonstrações financeiras anuais (2024–2029)
- Demonstração de Resultados (DR)
- Balanço
- Demonstração de Fluxos de Caixa (DFC)
- KPIs e rácios financeiros

### Outputs mensais de 2025 (M3 — Fase 1)
| Output | Chave `run_model` | Conteúdo |
|---|---|---|
| Calendário EOEP | `eoep_mensal_2025` | IVA, SS e IRC PPC mês a mês |
| Vendas | `vendas_mensal_2025` | VN por produto × mercado × mês |
| DR mensal | `dr_mensal_2025` | P&L completo para cada mês |
| Tesouraria | `tesouraria_mensal_2025` | Recebimentos, pagamentos, saldo |
| FSE por rubrica | `fse_detalhe_mensal_2025` | 14 rubricas FSE por mês |
| Pessoal mensal | `pessoal_mensal_2025` | Gastos pessoal por mês (14 salários) |
| CMVMC mensal | `cmvmc_mensal_2025` | CMVMC por mês (sazonalidade ponderada) |

> **Princípio bottom-up para 2025:** os saldos EOEP do Balanço de 2025 são derivados do calendário mensal (IVA Nov+Dez pendentes, SS Dez pendente, IRC residual), não lidos directamente do YAML.

### Análise e projetos
- Rolling forecast mensal (Balanço + DFC + NFM mensais)
- Orçamento de produção por produto
- Análise de sensibilidade (tornado)
- Viabilidade do Hub Logístico M6 (VAL, TIR, Payback, Índice de Rendibilidade)
- Subsidiária Ecogres

### OE4 — Plano de Financiamento do Investimento (integrado no Hub)
| Output | Onde | Conteúdo |
|---|---|---|
| Equilíbrio financeiro pré/pós-projeto | Separador Hub | Autonomia financeira, solvabilidade, endividamento, cobertura de juros — 2024 (pré) + 2025-2029 (pós); alerta se AF < 30% |
| Mapa de investimento | Separador Hub | CAPEX por pool de ativo (construção civil, VLMs, AMRs, WMS, integração) + cronograma anual + ΔNFM + PT2030 |
| Mapa de serviço da dívida | Separador Hub | Juros, amortizações, DSCR por ano; indicação do período de carência (2025-2027) |
| Solvabilidade (CP/Passivo) | Separador KPIs | Novo rácio adicionado à tabela de KPIs (2024-2029) |

---

## Cenários

| Cenário | Volume vendas | Preço (spread real) | FSE / Pessoal |
|---|---|---|---|
| **Base** | +3% a.a. | +0,8% real | YAML (referência) |
| **Upside** | +4,5% → +3% | +1,8% → +1,4% | FSE controlado |
| **Downside** | +1,5% → +2,5% | negativo → +0,4% | FSE+Pessoal acima |
| **Stress** | −3% em 2025, depois +1-3% | negativo → +0,9% | FSE choque +9,6% |

O toggle **Hub Logístico** é independente do cenário e aplica-se a **qualquer** combinação. Quando ativo, o engine incorpora automaticamente **todos** os benefícios do Hub no DR/Balanço/DFC:

| Efeito Hub | Fonte | Magnitude |
|---|---|---|
| Poupança operacional (pessoal + FSE) | `hub_dr_impact()` | €380k/ano (cresce 4%/a) |
| Redução de quebras | `hub_dr_impact()` | €50k/ano |
| VN incremental B2C/e-commerce | `hub_dr_impact()` → `build_dr()` | €400k–€800k/ano (a partir de 2026) |
| CAPEX e depreciações | `hub_capex()` | €3,8M (pools por ativo) |
| Financiamento CGD/BPI | `hub_financing()` | €2,85M @ 4,15% |
| Subsídio PT2030 | `pt2030_reconhecimento()` | €1,71M (reconhecido a/c depr.) |
| Libertação de inventário | `hub_dr_impact()` + `balanco.py` | €2M em 2026 (one-time) |
| Melhoria CCC (DMI) | `balanco.py` | redução inventários no balanço |

Cenários customizados persistem em `src/engine/data/cenarios/custom_scenarios.yaml`.

---

## Endpoints principais

```
GET  /api/scenarios/all               → DR/Balanço/DFC/KPIs todos os cenários
POST /api/run                         → execução com overrides custom
GET  /api/rolling-forecast/mensal     → Balanço+DFC+NFM mensais 2025
GET  /api/assumptions/effective       → pressupostos consolidados efectivos
GET  /api/hub/viability               → VAL, TIR, Payback, IR Hub M6
GET  /api/hub/tornado                 → análise sensibilidade Hub M6
GET  /api/hub/debt-service            → mapa de serviço da dívida (DSCR anual) — OE4
GET  /api/hub/investment-map          → mapa de investimento (CAPEX pools + NFM) — OE4
GET  /api/ecogres                     → projecções Ecogres
GET  /api/custom-scenarios            → cenários customizados guardados
```

---

## Inputs (YAML)

```
src/engine/data/
├── historico/2024/          ← dados reais 2024 (imutáveis)
├── pressupostos/
│   ├── globais.yaml         ← fiscal, prazos, pessoal, caixa
│   ├── 2025/                ← macro, vendas, custos, mix mensais
│   └── 2026_2029/           ← macro, vendas, custos anuais
├── master/                  ← catálogos estáveis (produtos, mercadorias, FSE)
├── computed/schedules.yaml  ← parâmetros BAU (CAPEX, amortizações, juros) — editável para ajustes de base
├── cenarios/                ← cenários customizados
└── subsidiarias/            ← Ecogres e Hub Logístico
```

---

## Estrutura do projecto

Ver [docs/project_tree.md](docs/project_tree.md) para a árvore completa.
Ver [docs/guia_docentes.md](docs/guia_docentes.md) para documentação detalhada de endpoints e outputs.
Ver [docs/PEF_2025-26_Resumo_M3_M6_OE4.md](docs/PEF_2025-26_Resumo_M3_M6_OE4.md) para o enquadramento académico completo.

---

