# GrestelPy — G18

Motor de planeamento financeiro da empresa **Grestel** desenvolvido em Python para suporte à UC PEF (2025-26), Grupo 18, ISCA-UA.

Cobre os Momentos **M3** (Planeamento Financeiro) e **M6** (Plano de Negócios), expondo todos os outputs através de uma API REST que alimenta a interface web.

---

## Arranque rápido

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
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
- Viabilidade do Hub Logístico M6 (VAN, TIR, Payback)
- Subsidiária Ecogres

---

## Cenários

| Cenário | Volume vendas | Preço vendas | FSE |
|---|---|---|---|
| **Base** | YAML (referência) | YAML (referência) | YAML |
| **Upside** | +5% a.a. | +5% → +3% | +4% em 2028-29 |
| **Downside** | +2% → +1% | +1% a.a. | +4% → +6% |
| **Stress** | −2% em 2025, depois +1-2% | 0-2% a.a. | +5-6% + pessoal |

Cenários customizados persistem em `src/engine/data/cenarios/custom_scenarios.yaml`.

---

## Endpoints principais

```
GET  /api/scenarios/all               → DR/Balanço/DFC/KPIs todos os cenários
POST /api/run                         → execução com overrides custom
GET  /api/rolling-forecast/mensal     → Balanço+DFC+NFM mensais 2025
GET  /api/assumptions/effective       → pressupostos consolidados efectivos
GET  /api/hub/viability               → VAN, TIR, Payback Hub M6
GET  /api/hub/tornado                 → análise sensibilidade Hub M6
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

## To-do / Trabalho pendente

### API — expor outputs mensais
- [ ] `GET /api/scenarios/all` — adicionar `eoep_mensal_2025`, `vendas_mensal_2025`, `dr_mensal_2025`, `tesouraria_mensal_2025` à resposta
- [ ] `POST /api/run` — idem (os DataFrames já estão em `dfs`; falta serializar e incluir na resposta)

### Engine — cálculos em falta
- [x] Pessoal mensal 2025 como output independente (`pessoal_mensal_2025`) — `build_pessoal_mensal()` em `tesouraria.py`
- [x] CMVMC mensal 2025 como output independente (`cmvmc_mensal_2025`) — `build_cmvmc_mensal()` em `tesouraria.py`
- [x] `Schedules.juros_total` — chave presente em `schedules.yaml`, acessível via `sched.financiamento["juros_total"]`

### Rolling Forecast — articulação mensal ↔ anual
- [ ] Balanço mensal (`balanco_mensal`) e DFC mensal (`dfc_mensal`) expostos no endpoint `rolling-forecast/mensal`
- [ ] Verificar reconciliação: soma DFC mensal = DFC anual 2025

### Testes
- [x] Testes de regressão para os novos outputs mensais — `tests/test_mensais_reconciliacao.py` (41 testes)
- [x] Teste de reconciliação: `sum(dr_mensal_2025.vn) == dr[ano==2025].vn` — Grupo 2 (9 testes)
- [x] Teste: saldos EOEP 2025 no Balanço = derivados do calendário mensal — Grupo 3 (12 testes)

### M6 — Plano de Negócios
- [x] Base BAU 2025 solidificada: CAPEX €900k (Madrid + Lisboa), amortizações €5,53M (só IAPMEI), juros €419k — `schedules.yaml`
- [ ] Integração do plano de investimento M6 no motor anual (2026–2029 com projecto)
- [ ] DR/Balanço/DFC comparativos sem-projecto vs. com-projecto
- [ ] VAN, TIR, Payback consolidados (Grestel + Ecogres + Hub)
- [ ] OE4: análise equilíbrio financeiro pré/pós-projecto (autonomia financeira ≥ 30%)

---

*GrestelPy · Engine v0.6+ · PEF 2025-26 · Grupo G18 · ISCA-UA*
