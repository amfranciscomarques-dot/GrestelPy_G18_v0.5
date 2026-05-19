# Contexto para Claude Design — Subtabs Hub Logístico

Este ficheiro substitui os ficheiros `.py` que o Claude Design não aceita.
Contém os contratos de API, shapes de dados reais e instruções de implementação.

---

## Tarefa

Adicionar **subtabs** ao `HubView` em `views.jsx`. Atualmente o HubView é um scroll único.
Deve passar a ter uma barra de 3 subtabs no topo:

| Subtab | Conteúdo |
|--------|----------|
| **Viabilidade** | Conteúdo atual (KPI cards, FCF chart, Tornado, Parâmetros, DR comparativo, KPIs comparativos, Consolidado) |
| **Monte Carlo** | Nova — distribuição estocástica do VAL e TIR |
| **Plano de Financiamento OE4** | Nova — mapa de investimento, estrutura de financiamento, serviço da dívida |

---

## Stack e padrões do frontend

- JSX puro com Babel CDN (sem build, sem npm, sem TypeScript)
- Sem bibliotecas externas — charts são SVG custom definidos em `charts.jsx`
- Fetch nativo em `api.js` com `USE_LIVE_API = true`, base URL `http://localhost:8000`
- Classes CSS: BEM-style `.panel`, `.panel-header`, `.panel-body`, `.ftable`, `.ftable--dense`, `.grid-2`, `.grid-4`, `.kpi`, `.kv`
- Formatação: `fmt.eurC(v)` (euros com casas), `fmt.pct(v)` (percentagem), `fmt.eur(v)` (euros inteiros)
- Estado gerido com `useState` + `useEffect` + `Promise.all` para carregamento paralelo

### Padrão de subtab existente noutras views (para replicar)

Noutras views (ex: ScenarioView) usa-se este padrão:
```jsx
const [subtab, setSubtab] = React.useState('viabilidade');

// Barra de subtabs
<div className="subtab-bar">
  {['viabilidade','monte_carlo','oe4'].map(t => (
    <button key={t}
      className={`subtab-btn${subtab===t?' subtab-btn--active':''}`}
      onClick={()=>setSubtab(t)}>
      {t === 'viabilidade' ? 'Viabilidade' : t === 'monte_carlo' ? 'Monte Carlo' : 'Plano Financiamento OE4'}
    </button>
  ))}
</div>
```

---

## Subtab 1 — Monte Carlo

### Endpoint

```
GET /api/hub/monte-carlo?n=1000&irc_taxa=0.245&seed=42
```

Parâmetros opcionais: `n` (100–5000, defeito 1000), `irc_taxa`, `seed`.

### Shape real da resposta

```json
{
  "n_simulations": 1000,
  "irc_taxa": 0.245,
  "val": {
    "mean": 3154000.0,
    "std": 620000.0,
    "p5": 2121000.0,
    "p10": 2350000.0,
    "p25": 2750000.0,
    "p50": 3197000.0,
    "p75": 3580000.0,
    "p90": 3950000.0,
    "p95": 4205000.0,
    "min": 1200000.0,
    "max": 5100000.0,
    "prob_positivo": 1.0,
    "histogram": {
      "bins":   [float, ...],
      "counts": [int, ...],
      "edges":  [float, ...]
    }
  },
  "tir": {
    "mean": 0.3285,
    "std": 0.061,
    "p5": 0.218,
    "p10": 0.240,
    "p25": 0.290,
    "p50": 0.325,
    "p75": 0.365,
    "p90": 0.410,
    "p95": 0.445,
    "prob_supera_wacc_base": 1.0,
    "n_validas": 998,
    "n_invalidas": 2
  },
  "correlacoes_val": {
    "b2c": 0.531,
    "pessoal": 0.526,
    "inventario": 0.456,
    "capex": -0.394,
    "wacc": -0.342,
    "pt2030_taxa": 0.102
  },
  "distribuicoes_usadas": {
    "inventario":  {"type": "triangular", "min": 1000000, "mode": 2000000, "max": 2500000},
    "pt2030_taxa": {"type": "triangular", "min": 0.20,    "mode": 0.45,    "max": 0.45},
    "b2c":         {"type": "truncnorm",  "mean": 1.0, "std": 0.20, "low": 0.30, "high": 2.0},
    "pessoal":     {"type": "triangular", "min": 200000,  "mode": 380000,  "max": 500000},
    "wacc":        {"type": "triangular", "min": 0.06,    "mode": 0.08,    "max": 0.10},
    "capex":       {"type": "triangular", "min": 3230000, "mode": 3800000, "max": 4370000}
  },
  "parametros_base": {
    "val_base": 3570000.0,
    "tir_base": 0.156,
    "wacc_base": 0.08,
    "capex_base": 3800000.0,
    "irc_taxa": 0.245
  }
}
```

### Layout sugerido para a subtab Monte Carlo

```
┌─────────────────────────────────────────────────────┐
│  [3 KPI cards]                                      │
│  VAL médio     P(VAL > 0)     TIR média             │
│  3,15 M€       100,0 %        32,9 %                │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────┐ ┌──────────────────────┐
│  Distribuição do VAL        │ │  Percentis VAL        │
│  [HistogramChart SVG]       │ │  P5   2,12 M€         │
│  (bins + counts do JSON)    │ │  P25  2,75 M€         │
│  linha vertical = val_base  │ │  P50  3,20 M€         │
│                             │ │  P75  3,58 M€         │
│                             │ │  P95  4,21 M€         │
│                             │ │  [barra de fan]       │
└─────────────────────────────┘ └──────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Correlações driver → VAL (importância dos riscos)  │
│  [BarChart horizontal com r de Pearson]             │
│  b2c           ████████████  +0.53                  │
│  pessoal       ████████████  +0.53                  │
│  inventario    ██████████    +0.46                  │
│  capex        ████████████  −0.39                   │
│  wacc         ████████       −0.34                  │
│  pt2030_taxa  ██             +0.10                  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Distribuições usadas (tabela das 6 distribuições)  │
│  Driver | Tipo | Min | Modo | Máx                   │
└─────────────────────────────────────────────────────┘
```

### Nota sobre HistogramChart

Não existe em `charts.jsx` — criar novo componente SVG seguindo o mesmo padrão dos outros charts (props: `bins`, `counts`, `edges`, `baselineMark` para val_base, `width`/`height` via ResizeObserver).

### Chamada API a adicionar em `api.js`

```javascript
hubMonteCarlo: ({ n = 1000, irc_taxa = 0.245, seed } = {}) => {
  const params = new URLSearchParams({ n, irc_taxa });
  if (seed != null) params.append('seed', seed);
  return apiFetch(`/api/hub/monte-carlo?${params}`);
},
```

---

## Subtab 2 — Plano de Financiamento OE4

### Endpoints

```
GET /api/hub/debt-service       → mapa de serviço da dívida
GET /api/hub/investment-map     → mapa de investimento por pool + cronograma + NFM + PT2030
```

### Shape real: `/api/hub/debt-service`

```json
{
  "rows": [
    {
      "ano": 2025,
      "saldo_em_divida": 2850000.0,
      "saldo_fim": 2850000.0,
      "juros_pagos_total": 118275.0,
      "juros_capitalizados": 118275.0,
      "juros_expensed_dr": 0.0,
      "amortizacao_capital": 0.0,
      "servico_total_divida": 118275.0,
      "ebitda_hub_incremental": 0.0,
      "dscr_hub": 0.0,
      "periodo_carencia": true
    },
    {
      "ano": 2026,
      "saldo_em_divida": 2850000.0,
      "saldo_fim": 2850000.0,
      "juros_pagos_total": 118275.0,
      "juros_capitalizados": 0.0,
      "juros_expensed_dr": 118275.0,
      "amortizacao_capital": 0.0,
      "servico_total_divida": 118275.0,
      "ebitda_hub_incremental": 664465.0,
      "dscr_hub": 5.62,
      "periodo_carencia": true
    },
    {
      "ano": 2027,
      "saldo_em_divida": 2850000.0,
      "saldo_fim": 2850000.0,
      "juros_pagos_total": 118275.0,
      "juros_capitalizados": 0.0,
      "juros_expensed_dr": 118275.0,
      "amortizacao_capital": 0.0,
      "servico_total_divida": 118275.0,
      "ebitda_hub_incremental": 811865.0,
      "dscr_hub": 6.86,
      "periodo_carencia": true
    },
    {
      "ano": 2028,
      "saldo_em_divida": 2850000.0,
      "saldo_fim": 2565000.0,
      "juros_pagos_total": 118275.0,
      "juros_capitalizados": 0.0,
      "juros_expensed_dr": 118275.0,
      "amortizacao_capital": 285000.0,
      "servico_total_divida": 403275.0,
      "ebitda_hub_incremental": 869761.0,
      "dscr_hub": 2.16,
      "periodo_carencia": false
    },
    {
      "ano": 2029,
      "saldo_em_divida": 2565000.0,
      "saldo_fim": 2280000.0,
      "juros_pagos_total": 106447.5,
      "juros_capitalizados": 0.0,
      "juros_expensed_dr": 106447.5,
      "amortizacao_capital": 285000.0,
      "servico_total_divida": 391447.5,
      "ebitda_hub_incremental": 815672.84,
      "dscr_hub": 2.08,
      "periodo_carencia": false
    }
  ]
}
```

### Shape real: `/api/hub/investment-map`

```json
{
  "capex_base": 3800000.0,
  "pools": [
    {"pool": "construcao_civil",    "descricao": "Reabilitação G1 + estrutura metálica + honorários + preparação", "montante": 2130000, "ano_inicio": 2025, "taxa_depreciacao": 0.04,  "vida_util_anos": 25},
    {"pool": "integracao_formacao", "descricao": "Integração de sistemas e formação inicial",                       "montante": 150000,  "ano_inicio": 2025, "taxa_depreciacao": 0.33,  "vida_util_anos": 3},
    {"pool": "vlm",                 "descricao": "4 módulos VLM 14 m — core value driver",                          "montante": 870000,  "ano_inicio": 2026, "taxa_depreciacao": 0.125, "vida_util_anos": 8},
    {"pool": "robotica_amr",        "descricao": "3 AMRs + estações pick-and-pack",                                 "montante": 375000,  "ano_inicio": 2026, "taxa_depreciacao": 0.2,   "vida_util_anos": 5},
    {"pool": "wms_software",        "descricao": "WMS integrado",                                                   "montante": 275000,  "ano_inicio": 2026, "taxa_depreciacao": 0.25,  "vida_util_anos": 4}
  ],
  "capex_anual": [
    {"ano": 2025, "capex": 2280000},
    {"ano": 2026, "capex": 1520000}
  ],
  "nfm": [
    {"ano": 2025, "delta_nfm": 0.0},
    {"ano": 2026, "delta_nfm": 47000.0},
    {"ano": 2027, "delta_nfm": 0.0},
    {"ano": 2028, "delta_nfm": 25000.0},
    {"ano": 2029, "delta_nfm": 6250.0}
  ],
  "pt2030_montante": 1710000.0,
  "pt2030_ano": 2027
}
```

### Estrutura financeira real do projeto (para cards de contexto)

```
Empréstimo bancário (CGD/BPI):  2 850 000 €  @ 4,15 % a.a.
  Desembolso: 2025
  Carência:   2025–2027 (3 anos, só juros)
  Amortização: 285 000 €/ano a partir de 2028
  Juros 2025 capitalizados (NCRF 10): 118 275 €

Subsídio PT2030 (a fundo perdido): 1 710 000 €  (45 % do CAPEX)
  Recebimento: 2027

Capital próprio (suportado pela Grestel): 240 000 €

CAPEX total:                       3 800 000 €
  2025: 2 280 000 €  (construção civil + integração)
  2026: 1 520 000 €  (VLMs + AMRs + WMS)

NFM total:                            78 250 €
  2026: 47 000 € (arranque operacional)
  2028+: 31 250 € (serviços logísticos externos)

RFAI (CFI art. 22-23):
  Crédito gerado:   380 000 € (10 % × 3 800 000 €)
  Absorvido no horizonte: 380 000 € (100 %)
```

### Layout sugerido para a subtab OE4

```
┌─────────────────────────────────────────────────────┐
│  Situação pré-projeto (cards resumo autonomia finan.)│
│  [3 cards: Autonomia Fin. | Solvabilidade | Endivid.]│
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Mapa de Investimento                               │
│  [Tabela: pool | descrição | montante | vida útil]  │
│  [StackedBar: CAPEX 2025 por pool / 2026 por pool]  │
│  Total CAPEX: 3 800 000 €                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Estrutura de Financiamento                         │
│  [Donut ou 3 cards horizontais]                     │
│  Empréstimo  2 850 000 €  75 %                      │
│  PT2030      1 710 000 €  — subsidio (reduce need)  │
│  Cap. Próprio  240 000 €  6,3 %                     │
│  [linha: PT2030 recebido em 2027, após investimento]│
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Mapa de Serviço da Dívida                          │
│  [Tabela: ano | saldo | juros | amort | serviço | DSCR]│
│  [chip "Carência" para 2025-2027]                   │
│  [BarChart: saldo_em_divida + amortizacao por ano]  │
│  DSCR mínimo alvo: 1,20× (covenant bancário típico) │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  NFM — Necessidades de Fundo de Maneio              │
│  [Tabela simples: ano | delta_nfm]                  │
│  Total acumulado: 78 250 €                          │
└─────────────────────────────────────────────────────┘
```

### Chamadas API a adicionar em `api.js`

```javascript
hubDebtService: () => apiFetch('/api/hub/debt-service'),
hubInvestmentMap: () => apiFetch('/api/hub/investment-map'),
```

(já existem mas verificar se estão implementadas — o endpoint `/api/hub/debt-service` existe)

---

## Ficheiros a editar

| Ficheiro | O que fazer |
|----------|------------|
| `views.jsx` | 1. Adicionar estado `subtab` ao `HubView`. 2. Adicionar barra de subtabs. 3. Condicionar render atual à subtab "viabilidade". 4. Criar `HubMonteCarloView` e `HubOE4View` como componentes inline. |
| `api.js` | Adicionar `hubMonteCarlo()`, confirmar que `hubDebtService()` e `hubInvestmentMap()` existem. |
| `charts.jsx` | Criar `HistogramChart` para o histograma do VAL (bins, counts, edges, linha vertical baseline). |
| `data.js` | Adicionar mock `hubMonteCarlo()` com a estrutura do JSON acima (para modo offline). |

---

## Notas de implementação

- O carregamento de Monte Carlo pode ser lento (1–3 s para n=1000). Mostrar spinner/`LoadingShell` durante a chamada. Não fazer a chamada até o utilizador clicar na subtab (lazy load).
- DSCR < 1.2 deve mostrar célula com cor de aviso (`.tone--neg`). Período de carência (`periodo_carencia: true`) deve mostrar chip/badge "Carência".
- `prob_positivo` e `prob_supera_wacc_base` vêm como decimais (0–1), converter com `fmt.pct()`.
- `correlacoes_val` já vem ordenado por `|r|` decrescente — usar essa ordem no gráfico de barras.
- Não inventar dados — usar **apenas** os campos documentados neste ficheiro.
