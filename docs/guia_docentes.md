# GrestelPy — Guia do Docente

> Motor financeiro da empresa Grestel · PEF 2025-26 · Grupo 18 · ISCA-UA

---

## 1. O que é este sistema

O **GrestelPy** é uma ferramenta de planeamento financeiro desenvolvida em Python para suporte aos Momentos M3 e M6 da UC PEF. Implementa o motor de cálculo da empresa Grestel e dos seus projetos associados (Ecogres e Hub Logístico M6), expondo os resultados através de uma API REST que alimenta uma interface web.

### O que o sistema produz

**Anuais (2024–2029):**
- Demonstração de Resultados (DR)
- Balanço
- Demonstração de Fluxos de Caixa (DFC)
- KPIs e rácios financeiros
- Detalhe FSE por rubrica (14 rubricas)
- Detalhe de Pessoal (contabilístico e departamental)
- Orçamento de Produção por produto

**Mensais de 2025 (M3 — Fase 1):**

| Output | Chave em `run_model` | Dimensão |
|---|---|---|
| Calendário fiscal EOEP | `eoep_mensal_2025` | 12 meses × 9 colunas |
| Vendas por produto/mercado | `vendas_mensal_2025` | 216 linhas × 4 colunas |
| DR mensal completa | `dr_mensal_2025` | 12 meses × 26 colunas |
| Orçamento de tesouraria | `tesouraria_mensal_2025` | 12 meses × 15 colunas |
| FSE por rubrica | `fse_detalhe_mensal_2025` | dict: 14 rubricas × 12 meses |
| Pessoal mensal | `pessoal_mensal_2025` | 12 meses × 2 colunas (mes, gastos_pessoal) |
| CMVMC mensal | `cmvmc_mensal_2025` | 12 meses × 2 colunas (mes, cmvmc) |

> **Princípio bottom-up para 2025:** os saldos EOEP no Balanço de 2025 são derivados do calendário mensal:
> - EOEP devedor/credor IVA = saldo IVA de Nov + Dez (pagamento M+2, pendente em Jan/Fev 2026)
> - EOEP credor SS = SS de Dezembro (pagamento M+1, pendente em Jan 2026)
> - EOEP credor IRC = IRC do ano menos pagamentos por conta efectuados

**Rolling Forecast (Balanço + DFC + NFM mensais):**
- `GET /api/rolling-forecast/mensal` — loop integrado DFC→Caixa→Balanço

**Projetos:**
- Hub Logístico M6: VAN, TIR, Payback, FCF, análise tornado
- Subsidiária Ecogres: DR, projecções, transferências intercompany

---

## 2. Iniciar o servidor

**Windows (sem Python instalado):** executar `SETUP.bat` uma vez, depois `start.bat`.

**Com Python instalado:**

```bash
pip install -r requirements.txt
python server.py
```

| Endereço | Descrição |
|---|---|
| `http://localhost:8000/` | Redireciona para a interface web |
| `http://localhost:8000/interface/` | Interface web interactiva |
| `http://localhost:8000/health` | Verificação de estado (`{"ok": true}`) |
| `http://localhost:8000/docs` | Documentação interactiva da API (Swagger UI) |

---

## 3. Cenários disponíveis

| Cenário | Volume vendas | PVU (preço) | FSE | Pessoal |
|---|---|---|---|---|
| **Base** | YAML | YAML | YAML | YAML |
| **Upside** | +5% a.a. (2025–28), +4% em 2029 | spread real +2,7% (2025) → +1,4% (2029) | +2,3–2,4% spread real em 2028–29 | — |
| **Downside** | +2% a.a. (2025–27), +1% em 2028–29 | spread real −1,2% (2025) → −0,6% (2029) | +1,8–4,3% spread real | — |
| **Stress** | −2% em 2025, recupera +1–2% | spread real −2,2% → +0,4% | +3,7–4,3% spread real | +2,7% spread real |

Os valores de PVU e FSE são **spreads reais** acima da inflação — o motor compõe com a inflação de `macro.yaml` em runtime:  
`taxa_nominal = (1 + inflação) × (1 + spread_real) − 1`

---

## 4. Endpoints

### 4.1 Executar todos os cenários

```
GET /api/scenarios/all?hub_on=false&ecogres_on=false
```

Retorna DR, Balanço, DFC, KPIs, FSE detalhe anual e mensal, Pessoal e Produção para os quatro cenários.

---

### 4.2 Executar cenário único com pressupostos personalizados

```
POST /api/run
```

```json
{
  "cenario": "Base",
  "hub_on": false,
  "ecogres_on": false,
  "assumptions": {
    "crescimento_volume_vendas": { "2026": 0.04 }
  },
  "persist": false
}
```

Retorna todos os outputs em `{"status": "ok", "outputs": {...}}`.

---

### 4.3 Rolling Forecast Mensal (M3 — Fase 1)

```
GET /api/rolling-forecast/mensal?scenario=Base
```

Retorna:

| Chave | Conteúdo |
|---|---|
| `dr_mensal` | DR mensal 2025 (12 linhas) |
| `balanco_mensal` | Balanço mensal 2025, Caixa derivada do DFC |
| `dfc_mensal` | DFC mensal pelo método indirecto |
| `nfm_mensal` | NFM e Ciclo de Conversão de Caixa por mês |
| `tesouraria_completa` | Recebimentos, pagamentos, serviço dívida, CAPEX |

---

### 4.4 Pressupostos efectivos

```
GET /api/assumptions/effective?cenario=Base&hub_on=false&ecogres_on=false
```

Devolve os pressupostos consolidados tal como o motor os utiliza — útil para auditar os inputs.

---

### 4.5 Hub Logístico (M6)

```
GET /api/hub/viability?irc_taxa=0.225
GET /api/hub/tornado?irc_taxa=0.225
```

| Endpoint | Retorna |
|---|---|
| `/hub/viability` | VPL, TIR, Payback simples e actualizado, valor terminal, FCF |
| `/hub/tornado` | Análise de sensibilidade (tornado) às variáveis críticas |

---

### 4.6 Subsidiária Ecogres

```
GET /api/ecogres
```

Parâmetros opcionais: `hub_on`, `cresc_subc`, `cresc_ced`, `cresc_custos`, `cresc_dep`, `alpha_sem_hub`, `alpha_com_hub`, `transfer_price`, `transfer_inicio`, `irc_taxa`.

---

### 4.7 Configuração

```
GET /api/config/years         → [2024, 2025, 2026, 2027, 2028, 2029]
GET /api/config/fse-rubricas  → rubricas FSE e chaves YAML
```

---

### 4.8 Cenários Customizados

```
GET    /api/custom-scenarios
POST   /api/custom-scenarios/{nome}
DELETE /api/custom-scenarios/{nome}
```

Persistem em `src/engine/data/cenarios/custom_scenarios.yaml`.

---

### 4.9 Tracker de Objetivos SMART (M3)

```
GET /api/smart/tracker?cenario=Base&hub_on=false&ecogres_on=false
```

Retorna uma linha por objetivo × ano com status de cumprimento calculado a partir da projeção do modelo:

| Campo | Descrição |
|---|---|
| `id` | Identificador do objetivo (`vn_2025`, `ebitda_margin_2025`, …) |
| `nome` | Nome legível |
| `categoria` | `economica` / `financeira` / `operacional` / `esg` |
| `ano` | Ano de avaliação |
| `valor` | Valor projetado pelo modelo |
| `alvo` | Target SMART definido em `smart_objetivos.yaml` |
| `status` | `cumprido` / `em_risco` (desvio ≤5%) / `nao_cumprido` |
| `desvio_pct` | `(valor − alvo) / |alvo|` |

**Objetivos cobertos:**

| ID | KPI fonte | Alvo | Ano(s) |
|---|---|---|---|
| `vn_2025` | `kpis.vn` | ≥ 45,6 M€ | 2025 |
| `ebitda_margin_2025` | `kpis.margem_ebitda` | ≥ 19,5% | 2025 |
| `autonomia_financeira` | `kpis.autonomia_financeira` | ≥ 35% | 2025–2029 |
| `ccc_2027` | `kpis.ciclo_caixa` | ≤ 260 dias | 2027 |
| `gas_peca_2026` | `gas_por_peca_anual.var_vs_2024` | ≤ −10% | 2026 |

Os objetivos são declarados em `src/engine/data/master/smart_objetivos.yaml` — editar para ajustar targets sem tocar em código.

---

## 5. Fluxo de cálculo interno

```
YAML (inputs)
    │
    ▼
load(cenario) ──► Assumptions + Base2024 + Schedules
    │
    ▼
run_model()
    ├── build_eoep_mensal()          ← NOVO: calendário fiscal mensal (antes das demonstrações)
    │
    ├── build_statements()           ← DR → Balanço (EOEP 2025 derivado do mensal) → DFC
    │
    ├── vendas_mensais_2025()        ← VN mensal por produto/mercado
    ├── build_dr_mensal()            ← DR mensal 2025
    ├── build_tesouraria_mensal()    ← Tesouraria mensal 2025
    ├── build_pessoal_mensal()       ← Pessoal mensal (14 salários)
    ├── build_cmvmc_mensal()         ← CMVMC mensal (sazonalidade ponderada)
    ├── fse_detalhe_mensal_2025()    ← FSE 14 rubricas mensais
    │
    ├── fse_detalhe_anual()          ← FSE anual por rubrica
    ├── pessoal_contab_anual()       ← Pessoal detalhe contabilístico
    ├── pessoal_depart_anual()       ← Pessoal por departamento
    ├── producao_anual()             ← Orçamento de produção
    └── build_kpis()                 ← KPIs e rácios
    │
    ▼
dataframe_to_records() ──► API (JSON)

                              ↑ também usado por:
                         smart/tracker
                           build_kpis() + gas_por_peca_anual()
                                    │
                         build_smart_tracker()  ← smart.py
                           compara projeção vs. smart_objetivos.yaml
                                    │
                                    ▼
                         status: cumprido / em_risco / nao_cumprido
```

---

## 6. Dados de entrada (YAML)

| Ficheiro/Directório | Conteúdo | Editável |
|---|---|---|
| `pressupostos/globais.yaml` | Fiscal (IVA, IRC, SS, TSU), prazos (PMR/PMP), caixa mín/máx, ESG, **sazonalidade mensal por mercado** | ✓ |
| `pressupostos/2025/macro.yaml` | Inflação mensal 2025, EUR/USD mensal 2025 | ✓ |
| `pressupostos/2025/vendas.yaml` | Crescimento volume e PVU por produto 2025 | ✓ |
| `pressupostos/2025/custos.yaml` | FSE, pessoal, CMVMC 2025 | ✓ |
| `pressupostos/2025/mix.yaml` | Mix USA/ROW dentro do segmento EXT e mix por canal por produto × mercado — ficheiro de trabalho do rolling forecast (atualizar com vendas reais mensais). **Não** inclui sazonalidade (está em `globais.yaml`) nem o mix de produto/VN (derivado de `historico/2024/produtos.yaml`) | ✓ |
| `pressupostos/2026_2029/` | Pressupostos plurianuais (macro, vendas, custos) | ✓ |
| `historico/2024/base.yaml` | Balanço, DR e DFC reais 2024 | ✗ (histórico) |
| `historico/2024/mix.yaml` | Mix real 2024 por mercado/canal | ✗ |
| `historico/2024/produtos.yaml` | `sales_mix_2024`, `pvu_base_2024` por produto | ✗ |
| `historico/2024/mercadorias.yaml` | `sales_mix_2024`, `pvu_base_2024`, sazonalidade por mercadoria | ✗ |
| `master/produtos.yaml` | Estrutura de custos (CIP, MP) — estável | ✓ (raramente) |
| `master/mercadorias.yaml` | Custo de compra (`pcu`) por família | ✓ (raramente) |
| `master/fse_rubricas.yaml` | Contrato de rubricas FSE | ✓ (raramente) |
| `computed/schedules.yaml` | CAPEX, amortizações, juros, depreciações, saldos empréstimos — parâmetros BAU | ✓ (BAU) |
| `cenarios/custom_scenarios.yaml` | Cenários customizados guardados via API | ✗ (gerido pela API) |
| `subsidiarias/ecogres/` | Pressupostos Ecogres | ✓ |
| `subsidiarias/hub_logistico/` | Pressupostos Hub M6 | ✓ |

---

## 7. Cobertura dos requisitos PEF

| Requisito M3/M6 | Onde é gerado | Estado |
|---|---|---|
| Orçamento de vendas mensal | `vendas_mensal_2025` em `run_model` | ✅ |
| Orçamento de produção | `producao_anual` em `run_model` | ✅ |
| Orçamento gastos com pessoal | `pessoal_contab_anual`, `pessoal_depart_anual` | ✅ |
| Orçamento FSE mensal (14 rubricas) | `fse_detalhe_mensal_2025` | ✅ |
| Orçamento CMVMC | `cmvmc_anual` (anual); `cmvmc_mensal_2025` (mensal independente) | ✅ |
| Calendarização fiscal (IVA, SS, IRC) | `eoep_mensal_2025` | ✅ |
| Orçamento de tesouraria mensal | `tesouraria_mensal_2025` | ✅ |
| Necessidades de Fundo de Maneio | `nfm_mensal` (rolling forecast) | ✅ |
| DR, DFC, Balanço previsionais (5 anos) | `dr`, `balanco`, `dfc` em `run_model` | ✅ |
| Rolling forecast mensal M3-F1 | `GET /api/rolling-forecast/mensal` | ✅ |
| KPIs mensuráveis | `kpis` em `run_model` | ✅ |
| Análise de cenários (4 cenários) | `GET /api/scenarios/all` | ✅ |
| Análise de sensibilidade | `GET /api/hub/tornado` + `sensitivity.py` | ✅ |
| VAN, TIR, Payback Hub M6 | `GET /api/hub/viability` | ✅ |
| Subsidiária Ecogres | `GET /api/ecogres` | ✅ |
| Outputs mensais expostos na API | `GET /api/scenarios/all` | ✅ |
| Gastos pessoal mensal independente | `pessoal_mensal_2025` em `run_model` | ✅ |
| CMVMC mensal independente | `cmvmc_mensal_2025` em `run_model` | ✅ |
| Base BAU M6 solidificada | `schedules.yaml` — CAPEX 900k, amort. 5,53M | ✅ |
| Sistematização objetivos SMART (M3) | `GET /api/smart/tracker` + `smart_objetivos.yaml` | ✅ |

---

## 8. Testes automatizados

`tests/test_mensais_reconciliacao.py` — **41 testes**, organizados em 3 grupos:

| Grupo | Nº testes | O que verifica |
|---|---|---|
| **Estrutura e regressão** | 20 | 12 linhas, colunas obrigatórias, sem NaN, ordem MESES correcta; 14 salários (Jun/Nov = 2×); Agosto menor (sazonalidade) |
| **Reconciliação mensal ↔ anual** | 9 | `sum(dr_mensal.vn) ≈ dr[2025].vn` e análogo para CMVMC, FSE, pessoal; EBITDA = VN − CMVMC − FSE − pessoal linha a linha |
| **EOEP fiscal derivado** | 12 | EOEP devedor = \|IVA Nov+Dez\|; art.º 105.º CIRC (PPC só Jul/Set/Dez); SS desfasado 1 mês; saldo Dez ≈ referência anual |

> **Nota:** o DR mensal é simplificado (sem `outros_rendimentos`), pelo que a soma anual do EBITDA mensal não reconcilia com o EBITDA anual completo — comportamento esperado e documentado nos docstrings dos testes.

```bash
pytest tests/test_mensais_reconciliacao.py -v
```

---

## 9. Base BAU para M6

Antes de activar o Hub Logístico (`hub_on=true`), o `schedules.yaml` deve reflectir o plano estratégico BAU da gerência. Valores de referência ajustados em 2026-05-14:

| Parâmetro | Anterior | Novo (BAU M6) | Justificação |
|---|---|---|---|
| CAPEX AFT 2025 | 500k | **900k** | Flagship Madrid + outlet Lisboa + modernização |
| Amortizações 2025 | 7.951k | **5.531k** | Paga só IAPMEI; moratória em BPI/Santander/CGD/Abanca |
| Empréstimos NC fim-2025 | 8.873k | **12.549k** | Dívida comercial mantida (sem amortização) |
| Empréstimos C fim-2025 | 2.043k | **788k** | Apenas Santander + Locações vencíveis em 2026 |
| Juros 2025 | 382k | **419k** | Maior dívida média em circulação |
| Dividendos distribuídos 2025 | 0 | **0** | Resultado 2024 aplicado em reservas |

Gearing estimado fim-2025: **44%** (intervalo alvo 40–65%).

Para repor os valores originais ou ajustar individualmente, editar directamente `src/engine/data/computed/schedules.yaml` nas secções `investimento` e `financiamento`.

---

## 10. Verificação rápida

```bash
# Estado do servidor
curl http://localhost:8000/health

# Cenário Base
curl "http://localhost:8000/api/scenarios/all"

# Base com Hub + Ecogres
curl "http://localhost:8000/api/scenarios/all?hub_on=true&ecogres_on=true"

# Rolling forecast mensal
curl "http://localhost:8000/api/rolling-forecast/mensal?scenario=Base"

# Viabilidade Hub M6
curl "http://localhost:8000/api/hub/viability"

# Pressupostos efectivos Upside
curl "http://localhost:8000/api/assumptions/effective?cenario=Upside"

# Suite de testes
pytest tests/
```

---

## 11. Notas técnicas

- Servidor na porta **8000**; alterar com `--port XXXX`.
- Modo `--reload` reinicia quando qualquer `.py` ou `.yaml` é alterado.
- Erros retornados em JSON com campos `error`, `detail` e `path`.
- Os valores de spread real nos cenários Upside/Downside/Stress são compostos com a inflação de `macro.yaml` em runtime — alterar a inflação propaga automaticamente a todos os drivers ligados à inflação.
- O calendário EOEP mensal é calculado **antes** das demonstrações anuais: os saldos de Balanço 2025 derivam dos mensais (bottom-up), não do `schedules.yaml`.

---

*GrestelPy · Engine v0.7 · PEF 2025-26 · Grupo G18 · ISCA-UA · actualizado 2026-05-18*
