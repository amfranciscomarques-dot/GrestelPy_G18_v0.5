# Monte Carlo — Viabilidade do Hub Logístico 4.0

## O que é e para que serve

A análise tornado e o ponto crítico determinísticos respondem à pergunta  
*"o que acontece ao VAL se este driver variar isoladamente de X para Y?"*

A simulação Monte Carlo responde a perguntas mais ricas:

| Pergunta | Resposta do Monte Carlo |
|----------|------------------------|
| Qual a probabilidade de o projeto ser viável? | `val.prob_positivo` |
| Qual a distribuição provável do VAL? | percentis P5–P95 + histograma |
| Qual o driver de risco mais importante? | correlações de Pearson r(driver, VAL) |
| Qual o VAL num cenário pessimista realista? | P5 ou P10 do VAL |

---

## Endpoint

```
GET /api/hub/monte-carlo
```

### Parâmetros

| Parâmetro | Tipo | Defeito | Descrição |
|-----------|------|---------|-----------|
| `n` | int | 1 000 | Número de simulações (100–5 000) |
| `irc_taxa` | float | 0,245 | Taxa combinada IRC + Derrama |
| `seed` | int | *(aleat.)* | Seed para reprodutibilidade |

### Exemplo de chamada

```
GET /api/hub/monte-carlo?n=2000&seed=42
```

---

## Drivers e distribuições

| Driver | Distribuição | Parâmetros | Justificação |
|--------|-------------|------------|--------------|
| `inventario` | Triangular | min=1 M€, mode=2 M€, max=2,5 M€ | Evento pontual com teto físico (stock atual: 13 M€) |
| `pt2030_taxa` | Triangular degenerada | min=20 %, mode=45 %, max=45 % | Cenário base = montante máximo; risco só para baixo |
| `b2c` | Normal truncada | μ=1,0, σ=0,20, ∈ [0,3; 2,0] | Incerteza de crescimento de mercado digital |
| `pessoal` | Triangular | min=200 k€, mode=380 k€, max=500 k€ | Eficácia da automação AMR+VLM |
| `wacc` | Triangular | min=6 %, mode=8 %, max=10 % | Risco de financiamento (rating Grestel 2024) |
| `capex` | Triangular | min=−15 %, mode=base, max=+15 % | Derrapagem típica em projetos Industry 4.0 |

### Nota sobre a triangular degenerada (PT2030)

`Triangular(min=0.20, mode=0.45, max=0.45)` é formalmente válida: a moda coincide
com o máximo, criando uma distribuição assimétrica à esquerda onde a maioria das
amostras está próxima de 45 % mas existe cauda significativa para aprovações parciais
(20 %–35 %). Isto modela corretamente que o cenário base GrestelPy já assume aprovação
máxima — qualquer desvio é negativo.

---

## Estrutura da resposta

```json
{
  "n_simulations": 1000,
  "irc_taxa": 0.245,

  "val": {
    "mean": 3154000.0,
    "std":   620000.0,
    "p5":   2121000.0,
    "p10":  2350000.0,
    "p25":  2750000.0,
    "p50":  3197000.0,
    "p75":  3580000.0,
    "p90":  3950000.0,
    "p95":  4205000.0,
    "min":  1200000.0,
    "max":  5100000.0,
    "prob_positivo": 1.0,
    "histogram": {
      "bins":   [float, ...],   // centros de 40 bins
      "counts": [int, ...],     // frequência por bin
      "edges":  [float, ...]    // 41 arestas dos bins
    }
  },

  "tir": {
    "mean": 0.3285,
    "std":  0.061,
    "p5":   0.218,
    "p50":  0.325,
    "p95":  0.445,
    "prob_supera_wacc_base": 1.0,
    "n_validas": 1000,
    "n_invalidas": 0
  },

  "correlacoes_val": {
    "b2c":          0.531,
    "pessoal":      0.526,
    "inventario":   0.456,
    "capex":       -0.394,
    "wacc":        -0.342,
    "pt2030_taxa":  0.102
  },

  "distribuicoes_usadas": { ... },

  "parametros_base": {
    "val_base":  3570000.0,
    "tir_base":  0.156,
    "wacc_base": 0.08,
    "capex_base": 3800000.0,
    "irc_taxa":  0.245
  }
}
```

### Campos chave

| Campo | Interpretação |
|-------|---------------|
| `val.prob_positivo` | P(VAL > 0) — proporção de simulações onde o projeto cria valor |
| `val.p5` | VAL no cenário pessimista realista (só 5 % das simulações ficam abaixo) |
| `tir.prob_supera_wacc_base` | Proporção de simulações onde TIR > WACC base (8 %) |
| `correlacoes_val.capex` | Negativo: CAPEX mais alto → VAL mais baixo (esperado) |
| `correlacoes_val.b2c` | O maior coeficiente positivo → crescimento B2C é o driver mais impactante no VAL |

---

## Interpretação dos resultados (caso base GrestelPy)

Com os pressupostos padrão do YAML (`m6_hub_assumptions.yaml`) e n=1 000:

- **VAL médio ≈ 3,15 M€** — projeto robusto mesmo na média estocástica
- **P(VAL > 0) = 100 %** — nenhuma combinação dos 6 drivers testados torna o projeto inviável
- **TIR média ≈ 33 %** — excede amplamente o WACC base de 8 %
- **Driver mais impactante**: B2C e poupança operacional (r ≈ 0,53 cada) — a eficácia
  da automação e a penetração e-commerce são os fatores que mais determinam o resultado
- **PT2030 (r ≈ 0,10)**: correlação baixa porque a distribuição triangular já concentra
  amostras próximo do máximo (45 % = base) — o risco de aprovação parcial existe mas
  não domina a variância do VAL

---

## Metodologia

### Loop interno

Para cada iteração `i = 1 … N`:

1. Amostrar todos os drivers simultaneamente (independentes entre si)
2. `copy.deepcopy(hub_base)` — garante isolamento entre iterações
3. Aplicar mutações ao hub copiado (mesma lógica de `sensibilidade_hub()`)
4. Chamar `viabilidade_hub(hub_mutado, irc_taxa=irc_taxa, wacc=wacc_i)` — o WACC é
   passado como kwarg (não como mutação do dict), consistente com o comportamento
   de `sensibilidade_hub()` para o driver `wacc`
5. Registar VAL e TIR

### Dependência PT2030 ↔ CAPEX

O montante PT2030 é calculado como `taxa_pt2030 × capex_amostrado` (não `× capex_base`).
Isto é financeiramente correto: o subsídio é uma % do investimento real, que varia com o
CAPEX amostrado. Implica que os dois drivers não são independentes no seu efeito sobre o
PT2030 — mas são independentes nas suas distribuições de amostragem.

### RFAI e CAPEX

Quando o RFAI está ativo (`rfai.aplicar: true`), o `capex_elegivel` é escalado com o
mesmo fator do CAPEX (`capex_amostrado / capex_base`). Garante consistência interna:
mais investimento → mais base elegível para crédito fiscal.

### TIR inválida

`viabilidade_hub()` retorna `tir=None` quando não existe mudança de sinal nos FCFs
acumulados (projeto com FCFs sempre negativos ou sempre positivos no horizonte). Em
cenários muito pessimistas (CAPEX alto, benefícios baixos, WACC alto) isto pode ocorrer.
O campo `tir.n_invalidas` contabiliza estes casos; as estatísticas TIR excluem-nos.

---

## Limitações

1. **Independência entre drivers** — o modelo assume correlação zero entre os 6 drivers.
   Na realidade, WACC e crescimento B2C podem ser correlacionados (ciclo macroeconómico).
   Para correlações estruturais, seria necessária uma cópula Gaussiana.

2. **Sem incerteza no cronograma** — o horizonte (10 anos) e datas de arranque (2026)
   são tratados como certos. O risco de atraso de obra não está modelado nas distribuições.

3. **Distribuições subjetivas** — os parâmetros das triangulares foram calibrados com
   os ranges do tornado existente, que são julgamentos de especialista, não dados históricos.

---

## Ficheiros relevantes

| Ficheiro | Função |
|----------|--------|
| `src/engine/projetos/monte_carlo_hub.py` | Implementação da simulação |
| `src/engine/projetos/hub_logistico.py` | `viabilidade_hub()`, `sensibilidade_hub()` |
| `src/api/routes/hub.py` | Endpoint `GET /api/hub/monte-carlo` |
| `src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml` | Pressupostos base |
