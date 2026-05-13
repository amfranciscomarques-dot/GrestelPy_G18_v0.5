# GrestelPy — Guia do Docente

> Modelo financeiro da empresa Grestel · PEF 2025-26 · Grupo 18 · ISCA-UA

---

## 1. O que é este sistema

O **GrestelPy** é uma ferramenta de planeamento financeiro desenvolvida em Python para suporte aos Momentos M3 e M6 da UC PEF. Implementa o motor de cálculo da empresa Grestel e dos seus projetos associados (Ecogres e Hub Logístico), expondo os resultados através de uma API REST que alimenta uma interface web.

O sistema produz automaticamente:

- Demonstração de Resultados (DR)
- Balanço
- Demonstração de Fluxos de Caixa (DFC)
- Rolling Forecast Mensal (Fase 1 — M3)
- KPIs e rácios financeiros
- Análise de sensibilidade (tornado)
- Indicadores de viabilidade do projeto Hub Logístico (VAN, TIR, Payback)
- Projeções da subsidiária Ecogres

---

## 2. Iniciar o servidor

**Pré-requisitos:** Python ≥ 3.10, dependências instaladas.

```bash
# Instalar dependências (primeira vez)
pip install -r requirements.txt

# Arrancar o servidor
uvicorn server:app --reload --port 8000
```

Após arranque, aceder a:

| Endereço | Descrição |
|---|---|
| `http://localhost:8000/` | Redireciona para a interface web |
| `http://localhost:8000/interface/` | Interface web interativa |
| `http://localhost:8000/health` | Verificação de estado (`{"ok": true}`) |
| `http://localhost:8000/docs` | Documentação interativa da API (Swagger UI) |

---

## 3. Cenários disponíveis

O modelo suporta quatro cenários pré-definidos, aplicados através de overrides sobre os pressupostos base:

| Cenário | Crescimento volume vendas | Crescimento preço vendas | FSE |
|---|---|---|---|
| **Base** | Conforme YAML (referência) | Conforme YAML (referência) | Conforme YAML |
| **Upside** | +5% a.a. (2025–2028), +4% em 2029 | +5% (2025–2026), descendo até +3% em 2029 | +4% em 2028–2029 |
| **Downside** | +2% a.a. (2025–2027), +1% em 2028–2029 | +1% a.a. | +4% (2025–2027), +6% em 2028–2029 |
| **Stress** | −2% em 2025, depois +1–2% | 0–2% a.a. | +5–6% a.a. com aumento de pessoal |

O cenário **Base** é sempre o ponto de partida e não altera nenhum pressuposto.

---

## 4. Endpoints principais

### 4.1 Executar todos os cenários

```
GET /api/scenarios/all
```

Parâmetros opcionais:

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `hub_on` | bool | `false` | Inclui o projeto Hub Logístico no modelo consolidado |
| `ecogres_on` | bool | `false` | Inclui a subsidiária Ecogres no modelo consolidado |

**Retorna:** DR, Balanço, DFC, KPIs e detalhe FSE (anual e mensal 2025) para cada um dos quatro cenários.

Exemplo:
```
GET /api/scenarios/all?hub_on=true&ecogres_on=true
```

---

### 4.2 Executar cenário único com pressupostos personalizados

```
POST /api/run
```

Corpo JSON:

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

| Campo | Descrição |
|---|---|
| `cenario` | Um de: `Base`, `Upside`, `Downside`, `Stress` |
| `hub_on` | Ativa o projeto Hub Logístico |
| `ecogres_on` | Ativa a subsidiária Ecogres |
| `assumptions` | Overrides pontuais sobre qualquer pressuposto YAML |
| `persist` | Se `true`, guarda o resultado como cenário customizado |

---

### 4.3 Rolling Forecast Mensal (M3 — Fase 1)

```
GET /api/rolling-forecast/mensal?scenario=Base
```

Devolve a **DR mensal** e o **mapa de tesouraria mensal** para o ano de planeamento (2025), base do rolling forecast exigido em M3-Fase 1.

---

### 4.4 Pressupostos efetivos

```
GET /api/assumptions/effective?cenario=Base&hub_on=false&ecogres_on=false
```

Devolve os pressupostos consolidados exatamente como o motor os utiliza para um dado cenário — útil para auditar os inputs aplicados.

---

### 4.5 Configuração

```
GET /api/config/years         → anos disponíveis: [2024, 2025, 2026, 2027, 2028, 2029]
GET /api/config/fse-rubricas  → rubricas FSE contratadas e respetivas chaves YAML
```

---

### 4.6 Projeto Hub Logístico (M6)

```
GET /api/hub/viability?irc_taxa=0.225
GET /api/hub/tornado?irc_taxa=0.225
```

| Endpoint | Retorna |
|---|---|
| `/hub/viability` | VPL, TIR, Payback simples e atualizado, valor terminal, FCF livre |
| `/hub/tornado` | Análise de sensibilidade (tornado) às variáveis críticas do projeto |

O parâmetro `irc_taxa` define a taxa de IRC aplicada (padrão: 22,5%).

---

### 4.7 Subsidiária Ecogres

```
GET /api/ecogres
```

Parâmetros opcionais (todos com valores padrão extraídos do YAML):

| Parâmetro | Descrição |
|---|---|
| `hub_on` | Considera transferências de/para o Hub Logístico |
| `cresc_subc` | Taxa de crescimento da subcontratação (%) |
| `cresc_ced` | Taxa de crescimento da cedência de pessoal (%) |
| `cresc_custos` | Taxa de crescimento dos custos operacionais |
| `cresc_dep` | Taxa de crescimento das depreciações |
| `alpha_sem_hub` / `alpha_com_hub` | Elasticidade de pessoal sem/com Hub ativo |
| `transfer_price` | Preço de transferência intercompany (€) |
| `transfer_inicio` | Ano de início das transferências |
| `irc_taxa` | Taxa de IRC da Ecogres |

---

### 4.8 Cenários Customizados

```
GET    /api/custom-scenarios              → lista cenários guardados
POST   /api/custom-scenarios/{nome}       → cria ou atualiza cenário
DELETE /api/custom-scenarios/{nome}       → elimina cenário
```

Corpo do POST:

```json
{
  "label": "Cenário alternativo",
  "description": "Simulação com preços +3%",
  "overrides": {
    "crescimento_preco_vendas": { "2026": 0.03, "2027": 0.03 }
  }
}
```

Os cenários customizados são persistidos em `src/engine/data/cenarios/custom_scenarios.yaml` e ficam disponíveis entre sessões.

---

## 5. Estrutura dos outputs

Todos os endpoints de cenários devolvem dados no formato:

```json
{
  "rows": [
    { "rubrica": "Vendas", "2025": 12500000, "2026": 13125000, ... },
    ...
  ]
}
```

As demonstrações financeiras cobrem o período **2024–2029** (2024 = histórico real; 2025–2029 = projeções).

---

## 6. Dados de entrada (YAML)

Todos os pressupostos estão em ficheiros YAML editáveis em `src/engine/data/`:

| Diretório | Conteúdo |
|---|---|
| `assumptions/` | Pressupostos gerais (FSE, depreciação, IRC, pessoal) |
| `drivers/2025/` | Drivers mensais de vendas, custos e mix para 2025 |
| `drivers/2026_2029/` | Drivers anuais de vendas e custos para 2026–2029 |
| `historico/2024/` | Base financeira real de 2024 (ponto de partida) |
| `master/` | Produtos, mercadorias e calendários de pagamento |
| `contrato/fse.yaml` | FSE contratado por rubrica |
| `subsidiarias/` | Pressupostos Ecogres e Hub Logístico |

Para alterar pressupostos permanentemente, editar o YAML correspondente e reiniciar o servidor (ou recarregar via `--reload`). Para alterações pontuais sem persistência, usar `POST /api/run` com o campo `assumptions`.

---

## 7. Cobertura dos requisitos PEF

| Requisito | Onde é gerado |
|---|---|
| Rolling forecast mensal (M3-F1) | `GET /api/rolling-forecast/mensal` |
| Projeções 5 anos (M3-F2) | `GET /api/scenarios/all` → DR/Balanço/DFC 2025–2029 |
| 15 orçamentos mensais | Motor: `operacoes/`, `pessoal/`, `financas/`, `integracao/fse.py` |
| DR, DFC, Balanço previsionais | `statements/dr.py`, `dfc.py`, `balanco.py` |
| KPIs mensuráveis | `analitica/kpis.py` → campo `kpis` na resposta |
| Análise de sensibilidade | `GET /api/hub/tornado` (Hub); `analitica/sensitivity.py` |
| Análise de cenários | Cenários Base / Upside / Downside / Stress + customizados |
| VAN, TIR, Payback (M6) | `GET /api/hub/viability` |
| NFM (Necessidades Fundo de Maneio) | `statements/nfm.py` |
| Mapas de serviço da dívida | `financas/financiamento.py` |
| Subsidiária Ecogres | `GET /api/ecogres` |
| Projeto Hub Logístico (M6) | `GET /api/hub/viability` + `GET /api/hub/tornado` |

---

## 8. Verificação rápida

Sequência de validação para confirmar que o sistema está operacional:

```bash
# 1. Estado do servidor
curl http://localhost:8000/health

# 2. Cenário Base (sem projetos)
curl "http://localhost:8000/api/scenarios/all"

# 3. Cenário Base com Hub e Ecogres
curl "http://localhost:8000/api/scenarios/all?hub_on=true&ecogres_on=true"

# 4. Rolling forecast mensal
curl "http://localhost:8000/api/rolling-forecast/mensal?scenario=Base"

# 5. Viabilidade Hub Logístico
curl "http://localhost:8000/api/hub/viability"

# 6. Pressupostos efetivos do cenário Upside
curl "http://localhost:8000/api/assumptions/effective?cenario=Upside"
```

---

## 9. Notas técnicas

- O servidor arranca na porta **8000** por padrão; alterar com `--port XXXX`.
- O modo `--reload` reinicia automaticamente quando um ficheiro Python ou YAML é alterado.
- Erros são devolvidos em JSON com campos `error`, `detail` e `path`.
- Os outputs em Excel (`*.xlsx`) e CSV (`*.csv`) gerados durante desenvolvimento estão excluídos do repositório (ver `.gitignore`).
- A suite de testes corre com `pytest tests/` a partir da raiz do projeto.

---

*GrestelPy v0.3.0 · Engine v0.5.0 · PEF 2025-26 · Grupo G18 · ISCA-UA*
