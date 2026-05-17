# Grestel Dashboard · Contrato de API

Documento de referência para integração frontend ↔ backend.

## Configuração

Definir antes do carregamento dos scripts:

```html
<script>
  // URL do backend
  window.GRESTEL_API_URL = "https://api.grestel.pt";

  // Allowlist: apenas os endpoints listados batem na API.
  // Os restantes continuam a usar os mocks (data.js).
  // Omitir para "tudo live"; deixar vazio para "tudo mock".
  window.GRESTEL_LIVE_ENDPOINTS = ["vendasAnalise"];
</script>
<script src="data.js"></script>
<script src="api.js"></script>
```

Modos resultantes:

| `GRESTEL_API_URL` | `GRESTEL_LIVE_ENDPOINTS` | Comportamento |
|---|---|---|
| não definido | — | Tudo mock (desenvolvimento offline) |
| definido | não definido | Tudo live (produção) |
| definido | `["vendasAnalise"]` | Só vendas em live; restante em mock (modo de migração) |
| definido | `[]` | Tudo mock (force-override para debugging) |

**Fallback automático:** se um endpoint marcado como live devolver erro (404, 500, network), o `api.js` faz fallback para o mock correspondente e regista warning na consola. A UI continua funcional.

**Subscrever a mudanças de estado:**

```js
API.onStatusChange(state => {
  console.log("Endpoint status:", state);
  // { vendasAnalise: "mock-fallback", projecao: "mock", ... }
});
```

Nomes de endpoints disponíveis: `health`, `historico2024`, `cenarios`, `pressupostos`, `projecao`, `vendasAnalise`, `rolling`, `hubViabilidade`, `hubTornado`, `ecogres`.

## Autenticação

A definir com o backend. O `api.js` suporta header `Authorization`:

```js
API.setAuthToken("Bearer eyJ...");
```

`credentials: "include"` está ativo (cookie de sessão também funciona).

## Convenções

- Todos os valores monetários em **euros**, sem agregação (€ inteiros, com decimais quando aplicável).
- Datas em **ISO 8601 UTC**: `2026-05-14T09:42:00Z`.
- Anos como inteiros: `2024`, não `"2024"`.
- Erros respondem com `4xx`/`5xx` + corpo JSON `{ "error": "...", "detail": "..." }`.

## Endpoints

### `GET /api/health`

Estado do engine.

```json
{
  "status": "ok",
  "last_engine_run": "2026-05-14T09:42:00Z",
  "engine_version": "v0.5.0"
}
```

### `GET /api/historico/2024`

Demonstrações auditadas 2024.

```json
{
  "dr": {
    "vn": 37884115.64, "var_inventarios": 131378.22, "outros_rend": 3742143.26,
    "cmvmc": 15298207.99, "fse": 7463107.43, "gastos_pessoal": 14371357.70,
    "imparidades": 1904.88, "outros_gastos": 473380.18,
    "ebitda": 4149678.94, "depreciacoes": 2168714.67, "ebit": 1980964.27,
    "juros": 528161.02, "rend_financeiros": 64677.79,
    "rai": 1517481.04, "irc": 127272.29, "rl": 1390208.75
  },
  "balanco": {
    "AFT_liquido": 12466455.49, "Goodwill": 1701103.8, "Intangiveis": 151088.11,
    "Subsidiarias": 3062681.47, "Inventarios": 13061556.31, "Clientes": 4962136,
    "Caixa": 542390.86, "Capital_Social": 526318, "Emprestimos_NC": 12203268.53,
    "Fornecedores": 3914140.07, "...": "..."
  },
  "fse": {
    "Subcontratos": 1492621.48, "Eletricidade": 894972.89, "Gas_Natural": 447486.44,
    "...": "..."
  }
}
```

### `GET /api/cenarios`

Drivers de cada cenário.

```json
{
  "Base": {
    "label": "Base",
    "desc": "Crescimento moderado alinhado com o sector cerâmico português.",
    "vol":    [null, 0.030, 0.030, 0.030, 0.030, 0.030],
    "preco":  [null, 0.030, 0.030, 0.030, 0.030, 0.030],
    "fse":    [null, 0.030, 0.030, 0.030, 0.030, 0.030],
    "pessoal":[null, 0.035, 0.030, 0.030, 0.030, 0.030],
    "cmvmc":  [null, 0.030, 0.030, 0.030, 0.030, 0.030]
  },
  "Upside":   { "...": "..." },
  "Downside": { "...": "..." },
  "Stress":   { "...": "..." }
}
```

Arrays alinhados com `[2024, 2025, 2026, 2027, 2028, 2029]` — o índice 0 é `null` (ano-base).

### `GET /api/pressupostos`

Taxas fiscais, prazos, elasticidades.

```json
{
  "IRC_taxa_geral": 0.20,
  "Derrama_Municipal": 0.015,
  "Derrama_Estadual": 0.0135,
  "TSU_Empresa": 0.2375,
  "SIFIDE_taxa_credito": 0.325,
  "PMR_dias": 45,
  "PMP_Inventarios_dias": 63,
  "DMI_PA_dias": 160,
  "Caixa_minima": 500000,
  "Caixa_maxima": 1500000,
  "Payout_ratio": 0.20,
  "Headcount_2024": 734,
  "Elasticidade_alpha_sem_hub": 0.40,
  "Elasticidade_alpha_com_hub": 0.15
}
```

### `POST /api/projecao` ★ endpoint principal

Devolve séries projetadas para um cenário.

**Request:**

```json
{ "cenario": "Base", "hub_on": false, "ecogres_on": true }
```

**Response:**

```json
{
  "dr": [
    {
      "year": 2024,
      "vn": 37884115.64, "outros_rend": 3742143.26, "cmvmc": 15298207.99,
      "fse": 7463107.43, "pessoal": 14371357.70, "outros_gastos": 475285.06,
      "ebitda": 4149678.94, "dep": 2168714.67, "ebit": 1980964.27,
      "juros": 463483.23, "rai": 1517481.04, "irc": 127272.29, "rl": 1390208.75
    },
    { "year": 2025, "...": "..." },
    { "year": 2026, "...": "..." },
    { "year": 2027, "...": "..." },
    { "year": 2028, "...": "..." },
    { "year": 2029, "...": "..." }
  ],
  "balanco": [
    {
      "year": 2024,
      "AFT_liquido": 12466455.49, "Goodwill": 1701103.8, "Inventarios": 13061556.31,
      "Clientes": 4962136, "Caixa": 542390.86,
      "Capital_Social": 526318, "Emprestimos_NC": 12203268.53,
      "ativo_total": 40258904.57, "passivo_total": 28058098.37, "capital_total": 12200806.20,
      "...": "..."
    },
    { "year": 2025, "...": "..." }
  ],
  "dfc": [
    {
      "year": 2024,
      "recebimentos": 39676113.70, "pag_fornecedores": -25706012.11, "pag_pessoal": -13696972.32,
      "fluxo_operacional": -1665311.89, "capex_aft": -1224709.40,
      "fluxo_investimento": -344818.37, "fluxo_financiamento": 2000679.68,
      "variacao_caixa": -9450.58
    }
  ],
  "kpis": [
    {
      "year": 2024,
      "margem_ebitda": 0.1096, "margem_ebit": 0.0523, "margem_liquida": 0.0367,
      "roa": 0.0345, "roe": 0.1140, "autonomia_financeira": 0.3030,
      "liquidez_geral": 1.3766, "endividamento": 0.4404, "cobertura_juros": 3.75,
      "pmr_dias": 45, "pmp_dias": 63
    }
  ],
  "fse": {
    "Subcontratos":  [1492621.48, 1537400.12, 1583522.13, "...", "..."],
    "Eletricidade":  [894972.89,  921822.08,  949476.74,  "...", "..."],
    "Gas_Natural":   [447486.44,  460911.04,  474738.37,  "...", "..."],
    "...": "..."
  }
}
```

### `GET /api/vendas/analise`

Detalhe da tab "Análise de Vendas".

**Query params:** `?cenario=Base&hub_on=false&ecogres_on=true`

```json
{
  "full": [
    { "year": 2020, "vn": 31400000, "produtos": 28140000, "mercadorias": 3260000, "hist": true },
    { "year": 2021, "...": "..." },
    { "year": 2024, "...": "...", "hist": true },
    { "year": 2025, "...": "...", "hist": false }
  ],
  "annual": [
    { "year": 2024, "vn": 37884115.64, "produtos": 33035908.84, "mercadorias": 4848206.80 }
  ],
  "meses": [
    { "mes": "Jan", "produtos": 2710000, "mercadorias": 350000, "total": 3060000 },
    { "mes": "Fev", "...": "..." }
  ],
  "familiasProd": [
    { "fam": "Pratos & Travessas", "peso": 0.34, "unidades": 4120000, "pvu_2024": 2.78, "receita": 11800000, "pvu_25": 2.86, "delta_pvu": 0.029 }
  ],
  "mercadorias": [
    { "item": "Embalagens primárias", "peso": 0.32, "unidades": 1900000, "pvu_2024": 0.82, "receita": 1620000, "pvu_25": 0.85, "delta_pvu": 0.037 }
  ],
  "mercados_2025": {
    "PT":  { "peso": 0.16, "label": "Portugal" },
    "UE":  { "peso": 0.31, "label": "União Europeia" },
    "USA": { "peso": 0.36, "label": "Estados Unidos" },
    "ROW": { "peso": 0.17, "label": "Resto do Mundo" }
  },
  "canais_2025": {
    "Private_Label": 0.24, "Hotelaria": 0.33, "Retalho": 0.25, "E_Commerce": 0.18
  },
  "totais_2025": { "produtos": 35140000, "mercadorias": 5160000, "total": 40300000 }
}
```

### `GET /api/rolling`

Rolling forecast mensal para 2025.

**Query params:** `?cenario=Base&hub_on=false&ecogres_on=true`

```json
[
  {
    "mes": "Jan", "vn": 2760000, "cmvmc": 1280000, "fse": 640000, "pessoal": 1080000,
    "ebitda": 60000, "ebit": -120000,
    "recebimentos": 2622000, "pagamentos": -2940000,
    "investimento": -50000, "financiamento": -120000,
    "caixa_fim": 530000
  }
]
```

### `GET /api/hub/viabilidade`

VAN/TIR do projeto Hub Logístico.

**Query params:** `?irc=0.21`

```json
{
  "vpl": 4180000, "tir": 0.142,
  "payback_simples": 2028, "payback_atualizado": 2029,
  "valor_terminal": 600000,
  "fcf": [0, -3300000, -2200000, 2400000, 350000, "..."],
  "fcf_cumulativo": [0, -3300000, -5500000, -3100000, "..."],
  "anos": [2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034],
  "parametros": { "wacc": 0.08, "capex_total": 5500000, "beneficio_liquido_anual": 255000 }
}
```

### `GET /api/hub/tornado`

Sensibilidade VAN (M€).

```json
[
  { "variavel": "Poupança operacional", "low": -2.4, "high": 3.1 },
  { "variavel": "WACC",                 "low": -1.9, "high": 1.8 }
]
```

### `GET /api/ecogres`

DR anual da subsidiária Ecogres.

**Query params:** `?hub_on=false`

```json
[
  {
    "year": 2024,
    "subc": 2240000, "ced": 360000, "vendas_externas": 3260000, "transfer_hub": 0,
    "custos_op": 5480000, "dep": 275000,
    "rec_total": 5860000, "ebitda": 380000, "ebit": 105000, "rai": 105000,
    "irc": 22050, "rl": 82950
  }
]
```

## Erros

```json
{
  "error": "cenario_invalido",
  "detail": "Cenário 'Foo' não existe. Aceitáveis: Base, Upside, Downside, Stress."
}
```

Códigos HTTP esperados:

- `200` — sucesso
- `400` — pedido mal formado (parâmetro inválido)
- `401` — não autenticado
- `403` — sem permissão
- `404` — recurso não encontrado
- `500` — erro do engine (motor de cálculo)
- `503` — engine ocupado / a reinicializar

## CORS

Backend deve permitir:

```
Access-Control-Allow-Origin: <domínio do frontend>
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
```

## Cache

Recomendado `ETag` + `Cache-Control: private, max-age=300` para endpoints estáticos:
- `/api/historico/*`
- `/api/pressupostos`
- `/api/cenarios`

Dinâmicos (`/api/projecao`, `/api/rolling`) devem usar `no-store` ou `max-age=60` consoante a tolerância a valores ligeiramente desatualizados.
