// api.js — API adapter (mock ↔ live backend)
// Para usar o backend Python: definir USE_LIVE_API = true e BACKEND_URL.
const USE_LIVE_API = true;
const BACKEND_URL  = "http://localhost:8000";

const API = (() => {
  const useMock = !USE_LIVE_API;

  // ─── health ────────────────────────────────────────────────────────────────
  async function health() {
    if (useMock) {
      return {
        status: "ok",
        engine_version: "v0.7-mock",
        last_engine_run: new Date().toISOString(),
      };
    }
    const r = await fetch(BACKEND_URL + "/health");
    if (!r.ok) throw new Error("Health check failed: " + r.status);
    const d = await r.json();
    return {
      status: d.ok ? "ok" : "error",
      engine_version: d.engine_version || "live",
      last_engine_run: d.last_engine_run || new Date().toISOString(),
    };
  }

  // ─── projecao ──────────────────────────────────────────────────────────────
  async function projecao({ cenario, hub_on, ecogres_on }) {
    if (useMock) {
      const dr   = GRESTEL.projectDR(cenario, { hubOn: hub_on, ecogresOn: ecogres_on });
      const bal  = GRESTEL.projectBalanco(dr, { hubOn: hub_on });
      const dfc  = GRESTEL.projectDFC(dr, bal, { hubOn: hub_on });
      const kpis = GRESTEL.projectKPIs(dr, bal);
      const fse  = GRESTEL.projectFSE(cenario);
      return { dr, balanco: bal, dfc, kpis, fse };
    }
    // Live: POST /api/run — executa um único cenário
    const r = await fetch(BACKEND_URL + "/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cenario, hub_on, ecogres_on }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Erro na API");
    }
    const { outputs } = await r.json();
    return {
      dr:      normalizeDR(outputs.dr || []),
      balanco: normalizeBal(outputs.balanco || []),
      dfc:     normalizeDFC(outputs.dfc || []),
      kpis:    normalizeKPIs(outputs.kpis || []),
      fse:     normalizeFSE(outputs.fse_detalhe_anual || []),
    };
  }

  // ─── vendasAnalise ─────────────────────────────────────────────────────────
  const PROD_LABEL = {
    Pratos: "Pratos", Tigelas: "Tigelas", Canecas: "Canecas",
    Pecas_Servir: "Peças de Serviço", Forno_Cozinha: "Forno & Cozinha",
  };
  const MERC_LABEL = {
    Cutelaria: "Cutelaria",
    Vidros_Cristais: "Vidros & Cristais",
    Texteis_Acessorios: "Têxteis & Acessórios",
  };

  function _buildFamilias(rows, keyField, labelMap) {
    const by2024 = {}, by2025 = {};
    for (const r of rows) {
      const k = r[keyField];
      if (r.ano === 2024) {
        if (!by2024[k]) by2024[k] = { vn: 0, qtd: 0 };
        by2024[k].vn  += r.vn  || 0;
        by2024[k].qtd += r.qtd || 0;
      } else if (r.ano === 2025) {
        if (!by2025[k]) by2025[k] = { vn: 0, qtd: 0 };
        by2025[k].vn  += r.vn  || 0;
        by2025[k].qtd += r.qtd || 0;
      }
    }
    const total25 = Object.values(by2025).reduce((s, d) => s + d.vn, 0) || 1;
    return Object.entries(by2025).map(([k, d25]) => {
      const d24 = by2024[k] || { vn: 0, qtd: 0 };
      const pvu_2024 = d24.qtd > 0 ? d24.vn / d24.qtd : 0;
      const pvu_25   = d25.qtd > 0 ? d25.vn / d25.qtd : 0;
      return {
        fam:      labelMap[k] || k,
        item:     labelMap[k] || k,
        receita:  d25.vn,
        peso:     d25.vn / total25,
        unidades: d25.qtd,
        pvu_2024,
        pvu_25,
        delta_pvu: pvu_2024 > 0 ? (pvu_25 - pvu_2024) / pvu_2024 : 0,
      };
    });
  }

  async function vendasAnalise({ cenario, hub_on, ecogres_on }) {
    if (useMock) {
      const dr = GRESTEL.projectDR(cenario, { hubOn: hub_on, ecogresOn: ecogres_on });
      return GRESTEL.projectVendasAnalise(dr);
    }
    // Live: busca dados reais do backend (PVU, qtd, vn por família)
    const r = await fetch(BACKEND_URL + "/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cenario, hub_on, ecogres_on }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Erro na API");
    }
    const { outputs } = await r.json();
    const dr = normalizeDR(outputs.dr || []);
    // Estrutura base (full, annual, meses, mercados, canais, totais)
    const base = GRESTEL.projectVendasAnalise(dr);
    // Substituir familiasProd e mercadorias com dados reais do backend
    const familiasProd = _buildFamilias(outputs.vendas_produto_anual || [], "produto", PROD_LABEL);
    const mercadorias  = _buildFamilias(outputs.vendas_mercadoria_anual || [], "mercadoria", MERC_LABEL);
    return { ...base, familiasProd, mercadorias };
  }

  // ─── Normalização: backend (snake_case, sinais contabilísticos) → frontend ──

  // DR: backend tem valores negativos para custos; frontend usa positivos.
  function normalizeDR(rows) {
    return rows.map(r => ({
      year:        r.ano,
      vn:          r.vn          || 0,
      outros_rend: r.outros_rend || 0,
      cmvmc:       Math.abs(r.cmvmc         || 0),
      fse:         Math.abs(r.fse           || 0),
      pessoal:     Math.abs(r.gastos_pessoal|| 0),
      outros_gastos: Math.abs(r.outros_gastos || 0) + Math.abs(r.imparidades || 0),
      ebitda:      r.ebitda      || 0,
      dep:         Math.abs(r.depreciacoes  || 0),
      ebit:        r.ebit        || 0,
      juros:       Math.abs(r.juros         || 0),
      rai:         r.rai         || 0,
      irc:         Math.abs(r.irc           || 0),
      rl:          r.rl          || 0,
    }));
  }

  // Balanço: backend usa lowercase; frontend usa PascalCase (herdado dos YAMLs).
  function normalizeBal(rows) {
    return rows.map(r => ({
      year:                      r.ano,
      AFT_liquido:               r.aft_liquido                || 0,
      Goodwill:                  r.goodwill                   || 0,
      Intangiveis:               r.intangiveis                || 0,
      Subsidiarias:              r.subsidiarias               || 0,
      Ativos_Fin_Justo_Valor:    r.ativos_fin_justo_valor     || 0,
      Outros_Ativos_Fixos:       r.outros_ativos_fixos        || 0,
      Impostos_Diferidos_Ativos: r.impostos_dif_ativos        || 0,
      Inventarios:               r.inventarios                || 0,
      Clientes:                  r.clientes                   || 0,
      Outros_AC:                 (r.outros_ac || 0) + (r.aplicacoes_fin_cp || 0) + (r.eoep_devedor || 0),
      Caixa:                     r.caixa                      || 0,
      Capital_Social:            r.capital_social             || 0,
      Premios_Emissao:           r.premios_emissao            || 0,
      Outros_IC_Proprio:         r.outros_ic_proprio          || 0,
      Reservas_Legais:           r.reservas_legais            || 0,
      Ajust_AF:                  r.ajust_af                   || 0,
      Resultados_Transitados:    r.resultados_transitados     || 0,
      Outras_Var_CP:             r.outras_var_cp              || 0,
      RL:                        r.rl                         || 0,
      Emprestimos_NC:            r.emprestimos_nc             || 0,
      Impostos_Diferidos_Passivos: r.imp_dif_passivos         || 0,
      Emprestimos_C:             r.emprestimos_c              || 0,
      Fornecedores:              r.fornecedores               || 0,
      Outros_PC:                 (r.outros_pc || 0) + (r.eoep_credor || 0) + (r.linha_credito_cp || 0),
      ativo_total:               r.total_ativo                || 0,
      passivo_total:             r.total_passivo              || 0,
      capital_total:             r.total_cp                   || 0,
    }));
  }

  // DFC: adapta nomes de campos do backend para o frontend.
  function normalizeDFC(rows) {
    return rows.map(r => ({
      year:               r.ano,
      recebimentos:       r.recebimentos_clientes || r.recebimentos       || 0,
      pag_fornecedores:   r.pagamentos_fornecedores || r.pag_fornecedores || 0,
      pag_pessoal:        r.pagamentos_pessoal    || r.pag_pessoal        || 0,
      fluxo_operacional:  r.fluxo_operacional     || 0,
      capex_aft:          r.capex_aft             || r.investimento        || 0,
      dividendos_recebidos: r.dividendos_recebidos || 0,
      fluxo_investimento: r.fluxo_investimento    || 0,
      rec_emprestimos:    r.rec_emprestimos        || 0,
      pag_emprestimos:    r.pag_emprestimos        || 0,
      fluxo_financiamento: r.fluxo_financiamento  || 0,
      variacao_caixa:     r.variacao_caixa         || 0,
    }));
  }

  // KPIs: campo `ano` → `year`; nomes idênticos ao GRESTEL.
  function normalizeKPIs(rows) {
    return rows.map(r => ({
      year:                 r.ano                  || r.year,
      margem_ebitda:        r.margem_ebitda        || 0,
      margem_ebit:          r.margem_ebit          || 0,
      margem_liquida:       r.margem_liquida       || 0,
      roa:                  r.roa                  || 0,
      roe:                  r.roe                  || 0,
      autonomia_financeira: r.autonomia_financeira || 0,
      liquidez_geral:       r.liquidez_geral       || 0,
      endividamento:        r.endividamento        || 0,
      cobertura_juros:      r.cobertura_juros      || 0,
      pmr_dias:             r.pmr_dias             || 45,
      pmp_dias:             r.pmp_dias             || 63,
    }));
  }

  // FSE: backend [{ano, rubrica, valor}] → frontend {rubrica: [val por ano]}.
  function normalizeFSE(rows) {
    const years = GRESTEL.YEARS;
    const out = {};
    for (const row of rows) {
      if (!out[row.rubrica]) out[row.rubrica] = new Array(years.length).fill(0);
      const yi = years.indexOf(row.ano);
      if (yi >= 0) out[row.rubrica][yi] = row.valor || 0;
    }
    return out;
  }

  return { useMock, health, projecao, vendasAnalise };
})();
