// data.js — Mock dataset derived from the Grestel backend YAML inputs.
// 2024 actuals come straight from src/engine/data/historico/2024/base.yaml.
// Forward years are projected with the growth rates declared in
// src/engine/data/cenarios/custom_scenarios.yaml.

const GRESTEL = (() => {
  const YEARS = [2024, 2025, 2026, 2027, 2028, 2029];

  // 2024 audited from base.yaml -> dr_2024_real
  const DR_2024 = {
    vn: 37884115.64,
    var_inventarios: 131378.22,
    outros_rend: 3742143.26,
    cmvmc: 15298207.99,
    fse: 7463107.43,
    gastos_pessoal: 14371357.70,
    imparidades: 1904.88,
    outros_gastos: 473380.18,
    ebitda: 4149678.94,
    depreciacoes: 2168714.67,
    ebit: 1980964.27,
    juros: 528161.02,
    rend_financeiros: 64677.79,
    rai: 1517481.04,
    irc: 127272.29,
    rl: 1390208.75,
  };

  // Scenario growth profiles (custom_scenarios.yaml)
  const SCENARIOS = {
    Base: {
      label: "Base",
      desc: "Crescimento moderado alinhado com o sector cerâmico português.",
      vol:    [null, 0.030, 0.030, 0.030, 0.030, 0.030],
      preco:  [null, 0.030, 0.030, 0.030, 0.030, 0.030],
      fse:    [null, 0.030, 0.030, 0.030, 0.030, 0.030],
      pessoal:[null, 0.035, 0.030, 0.030, 0.030, 0.030],
      cmvmc:  [null, 0.030, 0.030, 0.030, 0.030, 0.030],
    },
    Upside: {
      label: "Upside",
      desc: "Aceleração export USA/UE, canal hotelaria e reposicionamento premium.",
      vol:    [null, 0.045, 0.045, 0.040, 0.035, 0.030],
      preco:  [null, 0.040, 0.035, 0.030, 0.030, 0.030],
      fse:    [null, 0.020, 0.025, 0.030, 0.030, 0.030],
      pessoal:[null, 0.030, 0.030, 0.030, 0.030, 0.030],
      cmvmc:  [null, 0.035, 0.035, 0.030, 0.030, 0.030],
    },
    Downside: {
      label: "Downside",
      desc: "Abrandamento UE, concorrência asiática e incerteza tarifária USA.",
      vol:    [null, 0.015, 0.015, 0.020, 0.020, 0.025],
      preco:  [null, 0.015, 0.015, 0.020, 0.020, 0.020],
      fse:    [null, 0.040, 0.045, 0.050, 0.050, 0.050],
      pessoal:[null, 0.040, 0.040, 0.035, 0.035, 0.030],
      cmvmc:  [null, 0.035, 0.040, 0.040, 0.040, 0.040],
    },
    Stress: {
      label: "Stress",
      desc: "Choque energético severo, recessão global, colapso hotelaria.",
      vol:    [null, -0.030, -0.010, 0.015, 0.025, 0.030],
      preco:  [null, 0.005, 0.010, 0.015, 0.020, 0.025],
      fse:    [null, 0.120, 0.080, 0.060, 0.050, 0.040],
      pessoal:[null, 0.050, 0.050, 0.040, 0.040, 0.040],
      cmvmc:  [null, 0.060, 0.050, 0.040, 0.035, 0.030],
    },
  };

  // Project a DR series for a scenario; optional hub/ecogres on adds blocks.
  function projectDR(scenarioKey, opts = {}) {
    const s = SCENARIOS[scenarioKey];
    const hubOn = !!opts.hubOn;
    const ecoOn = !!opts.ecogresOn;

    const series = {
      vn: [DR_2024.vn],
      outros_rend: [DR_2024.outros_rend],
      cmvmc: [DR_2024.cmvmc],
      fse: [DR_2024.fse],
      pessoal: [DR_2024.gastos_pessoal],
      outros_gastos: [DR_2024.outros_gastos + DR_2024.imparidades],
      depreciacoes: [DR_2024.depreciacoes],
      juros: [DR_2024.juros - DR_2024.rend_financeiros],
      irc_taxa: 0.215, // IRC + derramas combinado
    };

    for (let i = 1; i < YEARS.length; i++) {
      const vendasGrowth = (1 + s.vol[i]) * (1 + s.preco[i]) - 1;
      series.vn.push(series.vn[i - 1] * (1 + vendasGrowth));
      series.outros_rend.push(series.outros_rend[i - 1] * 1.015);
      series.cmvmc.push(series.cmvmc[i - 1] * (1 + s.cmvmc[i]));
      let fse = series.fse[i - 1] * (1 + s.fse[i]);
      if (hubOn && YEARS[i] >= 2026) fse -= 300000 * Math.pow(1.02, YEARS[i] - 2026); // poupança operacional
      series.fse.push(fse);
      // Elasticidade pessoal: alpha 0.40 sem hub, 0.15 com hub
      const alpha = hubOn ? 0.15 : 0.40;
      const volFactor = 1 + s.vol[i] * alpha;
      series.pessoal.push(series.pessoal[i - 1] * (1 + s.pessoal[i]) * volFactor);
      series.outros_gastos.push(series.outros_gastos[i - 1] * 1.02);
      // CAPEX hub aumenta depreciação a partir de 2026 (taxa 10%)
      let dep = series.depreciacoes[i - 1] * 1.01;
      if (hubOn && YEARS[i] >= 2026) dep += 550000;
      series.depreciacoes.push(dep);
      // Juros sobem com financiamento Hub (4.125M @ 4.15%) a partir de 2025
      let juros = series.juros[i - 1] * 0.96; // amortização base
      if (hubOn && YEARS[i] >= 2025) juros += 171000;
      series.juros.push(juros);
    }

    // Build DR rows
    const dr = YEARS.map((y, i) => {
      const vn = series.vn[i];
      const outros_rend = series.outros_rend[i];
      const cmvmc = series.cmvmc[i];
      const fse = series.fse[i];
      const pessoal = series.pessoal[i];
      const outros_gastos = series.outros_gastos[i];
      const ebitda = vn + outros_rend - cmvmc - fse - pessoal - outros_gastos;
      const dep = series.depreciacoes[i];
      const ebit = ebitda - dep;
      const juros = series.juros[i];
      const rai = ebit - juros;
      const irc = Math.max(rai, 0) * series.irc_taxa;
      const rl = rai - irc;
      let row = { year: y, vn, outros_rend, cmvmc, fse, pessoal, outros_gastos, ebitda, dep, ebit, juros, rai, irc, rl };
      // Add Ecogres contribution when on
      if (ecoOn && y >= 2024) {
        const eco = ecogresDR(y, opts.hubOn);
        row = { ...row, ecogres_rl: eco.rl };
        row.rl += eco.rl;
      }
      return row;
    });

    return dr;
  }

  function ecogresDR(year, hubOn) {
    // Reconstrução do modelo Ecogres (ecogres_assumptions.yaml)
    // O YAML expõe apenas transações intercompany (2,6 M€). As vendas externas
    // são calibradas para reconciliar com rl_base_2024 = 85k€.
    const yIdx = year - 2024;
    const subc = 2240000 * Math.pow(1.03, yIdx);
    const ced  = 360000  * Math.pow(1.02, yIdx);
    // Calibração: para RL 2024 = 85k€, EBIT = ~108k€, EBITDA = ~383k€
    // logo Receita Total 2024 = 5.48M (custos) + 0.38M (EBITDA) ≈ 5,86 M€
    // Externas = 5,86 − 2,60 = ~3,26 M€
    const vendas_externas = 3260000 * Math.pow(1.025, yIdx);
    const custos_op = 5480000 * Math.pow(1.02, yIdx);
    const dep = 275000 * Math.pow(1.01, yIdx);
    const transfer_hub = (hubOn && year >= 2026 ? 180000 * Math.pow(1.02, year - 2026) : 0);
    const rec_total = subc + ced + vendas_externas + transfer_hub;
    const alpha = hubOn ? 0.15 : 0.40;
    const custos_aj = custos_op * (1 + (yIdx * 0.005 * alpha));
    const ebitda = rec_total - custos_aj;
    const ebit = ebitda - dep;
    const rai = ebit - 5000 + 5000; // rendimentos financeiros 5k
    const irc = Math.max(rai, 0) * 0.21;
    const rl = rai - irc;
    return { year, subc, ced, vendas_externas, transfer_hub, custos_op: custos_aj, dep, rec_total, ebitda, ebit, rai, irc, rl };
  }

  function projectEcogres(hubOn) {
    return YEARS.map(y => ecogresDR(y, hubOn));
  }

  // Balanço de abertura 2024 -> evolução com regras simples
  const BAL_2024 = {
    AFT_liquido: 12466455.49, Goodwill: 1701103.8, Intangiveis: 151088.11,
    Subsidiarias: 3062681.47, Ativos_Fin_Justo_Valor: 249000, Outros_Ativos_Fixos: 181793.21,
    Impostos_Diferidos_Ativos: 116.17,
    Inventarios: 13061556.31, Clientes: 4962136, Outros_AC: 3880444.15, Caixa: 542390.86,
    Capital_Social: 526318, Premios_Emissao: 623684, Outros_IC_Proprio: 1233333.32,
    Reservas_Legais: 144220.69, Ajust_AF: 2114812.59, Resultados_Transitados: 5770439.81,
    Outras_Var_CP: 396649.04, RL: 1390208.75,
    Emprestimos_NC: 12203268.53, Impostos_Diferidos_Passivos: 2.77,
    Emprestimos_C: 5530545.28, Fornecedores: 3914140.07, Outros_PC: 6411142.72,
  };

  function projectBalanco(dr, opts = {}) {
    const hubOn = !!opts.hubOn;
    const rows = [];
    let bal = { ...BAL_2024 };
    // 2024 row
    rows.push(yearBalance(2024, bal));
    let acumulado = bal.RL;
    let caixa = bal.Caixa;
    for (let i = 1; i < YEARS.length; i++) {
      const r = dr[i];
      const year = YEARS[i];
      const dep = r.dep;
      // CAPEX maintenance ~ 1.5% VN + Hub CAPEX
      let capex = r.vn * 0.015;
      if (hubOn && year === 2025) capex += 3300000;
      if (hubOn && year === 2026) capex += 2200000;
      bal.AFT_liquido = Math.max(0, bal.AFT_liquido - dep + capex);
      bal.Inventarios = bal.Inventarios * (1 + (r.vn / dr[i-1].vn - 1));
      bal.Clientes = r.vn * 45 / 360;
      bal.Fornecedores = (r.cmvmc + r.fse) * 63 / 360;
      bal.Outros_AC = bal.Outros_AC * 1.02;
      bal.Outros_PC = bal.Outros_PC * 1.02;
      // Dívida: amortiza ~12% ao ano + hub financiamento
      bal.Emprestimos_NC = bal.Emprestimos_NC * 0.92;
      bal.Emprestimos_C = bal.Emprestimos_C * 0.85;
      if (hubOn && year === 2025) bal.Emprestimos_NC += 4125000;
      if (hubOn && year >= 2028) bal.Emprestimos_NC -= 412500;
      // Resultado e caixa
      acumulado += r.rl;
      bal.RL = r.rl;
      bal.Resultados_Transitados = bal.Resultados_Transitados + (rows[i-1] ? rows[i-1].RL : 0);
      // Caixa fecha o balanço (resíduo)
      const ativoSemCaixa = ativos(bal) - bal.Caixa;
      const passivoCP = passivos(bal) + capitais(bal) - bal.Caixa;
      // simples: caixa cresce com lucro - capex - amortizações
      caixa = caixa + r.rl + dep - capex - (i === 1 && hubOn ? 0 : 800000);
      bal.Caixa = Math.max(300000, caixa);
      rows.push(yearBalance(year, bal));
    }
    return rows;
  }
  function ativos(b) {
    return b.AFT_liquido + b.Goodwill + b.Intangiveis + b.Subsidiarias + b.Ativos_Fin_Justo_Valor +
           b.Outros_Ativos_Fixos + b.Impostos_Diferidos_Ativos + b.Inventarios + b.Clientes + b.Outros_AC + b.Caixa;
  }
  function passivos(b) {
    return b.Emprestimos_NC + b.Impostos_Diferidos_Passivos + b.Emprestimos_C + b.Fornecedores + b.Outros_PC;
  }
  function capitais(b) {
    return b.Capital_Social + b.Premios_Emissao + b.Outros_IC_Proprio + b.Reservas_Legais +
           b.Ajust_AF + b.Resultados_Transitados + b.Outras_Var_CP + b.RL;
  }
  function yearBalance(year, bal) {
    return { year, ...bal, ativo_total: ativos(bal), passivo_total: passivos(bal), capital_total: capitais(bal) };
  }

  // DFC método indireto (fallback; via API é usado adaptDFC com dados do engine)
  function projectDFC(dr, balancos, opts = {}) {
    const hubOn = !!opts.hubOn;
    const rows = [];
    for (let i = 0; i < YEARS.length; i++) {
      const y = YEARS[i];
      const r = dr[i];
      if (i === 0) {
        // 2024 histórico — valores derivados do engine (método indireto)
        rows.push({
          year: y,
          rl: 1390208.75,
          dep_amort: 2168714.67,
          imparidades: 1904.88,
          juros_pagos: 528161.02,
          rend_fin: -64677.79,
          var_nfm: -5562351.13,
          irc_pago: -127272.29,
          fluxo_operacional: -1665311.89,
          pag_aft: -1224709.40,
          pag_intang: 0,
          div_recebidos: 656742.53,
          fluxo_investimento: -344818.37,
          rec_emprestimos: 17636212.43,
          pag_emprestimos: -14829115.28,
          juros_pagos_fin: -528161.02,
          pag_dividendos: 0,
          fluxo_financiamento: 2000679.68,
          variacao_caixa: -9450.58,
        });
        continue;
      }
      // Ajustamentos não-caixa (dep e juros estão negativos em adaptDR)
      const dep_amort = -r.dep;
      const juros_pagos = -r.juros;
      const imparidades = 0;
      const rend_fin = 0;
      const irc_pago = r.irc;  // negativo em adaptDR
      // Variação do fundo de maneio estimada via balanços
      const b = balancos[i], bPrev = balancos[i - 1];
      const var_nfm = bPrev
        ? (bPrev.Inventarios - b.Inventarios) + (bPrev.Clientes - b.Clientes) + (b.Fornecedores - bPrev.Fornecedores)
        : 0;
      const fluxo_operacional = r.rl + dep_amort + juros_pagos + var_nfm + irc_pago;
      // Investimento
      let pag_aft = -r.vn * 0.015;
      if (hubOn && y === 2025) pag_aft -= 3300000;
      if (hubOn && y === 2026) pag_aft -= 2200000;
      const pag_intang = 0;
      const div_recebidos = 250000;
      const fluxo_investimento = pag_aft + pag_intang + div_recebidos;
      // Financiamento
      let rec_emprestimos = 0, pag_emprestimos = -1000000;
      if (hubOn && y === 2025) rec_emprestimos += 4125000;
      if (hubOn && y === 2027) rec_emprestimos += 2200000;
      if (hubOn && y >= 2028) pag_emprestimos -= 412500;
      const juros_pagos_fin = r.juros;  // negativo
      const pag_dividendos = 0;
      const fluxo_financiamento = rec_emprestimos + pag_emprestimos + juros_pagos_fin + pag_dividendos;
      const variacao_caixa = fluxo_operacional + fluxo_investimento + fluxo_financiamento;
      rows.push({
        year: y,
        rl: r.rl, dep_amort, imparidades, juros_pagos, rend_fin, var_nfm, irc_pago,
        fluxo_operacional,
        pag_aft, pag_intang, div_recebidos, fluxo_investimento,
        rec_emprestimos, pag_emprestimos, juros_pagos_fin, pag_dividendos, fluxo_financiamento,
        variacao_caixa,
      });
    }
    return rows;
  }

  function projectKPIs(dr, bal) {
    return dr.map((r, i) => {
      const b = bal[i];
      return {
        year: r.year,
        margem_ebitda: r.ebitda / r.vn,
        margem_ebit: r.ebit / r.vn,
        margem_liquida: r.rl / r.vn,
        roa: r.rl / b.ativo_total,
        roe: r.rl / b.capital_total,
        autonomia_financeira: b.capital_total / b.ativo_total,
        liquidez_geral: (b.Inventarios + b.Clientes + b.Outros_AC + b.Caixa) / (b.Emprestimos_C + b.Fornecedores + b.Outros_PC),
        endividamento: (b.Emprestimos_NC + b.Emprestimos_C) / b.ativo_total,
        cobertura_juros: r.ebit / Math.max(r.juros, 1),
        pmr_dias: 45,
        pmp_dias: 63,
      };
    });
  }

  // Pessoal detalhe 2024 (base.yaml + globais.yaml)
  const PESSOAL_CONTAB_2024 = {
    Remuneracoes:    11400000.00,
    Encargos_TSU:     2707500.00,
    Seguros_AT:        150480.00,
    Outros_Encargos:   113377.70,
  };
  const PESSOAL_DEPART_PESOS = {
    Producao:   0.65,
    RD:         0.05,
    Comercial:  0.10,
    Financeira: 0.12,
    Marketing:  0.08,
  };

  function projectPessoalContab(scenarioKey, opts = {}) {
    const dr = projectDR(scenarioKey, opts);
    const total2024 = DR_2024.gastos_pessoal;
    const remun2024 = PESSOAL_CONTAB_2024.Remuneracoes;
    const tsu = 0.2375;
    const sat = 0.0132;
    const series = { Remuneracoes: [], Encargos_TSU: [], Seguros_AT: [], Outros_Encargos: [] };
    for (let i = 0; i < YEARS.length; i++) {
      const total = dr[i].pessoal;
      const remun = remun2024 * (total / total2024);
      const tsu_v = remun * tsu;
      const sat_v = remun * sat;
      series.Remuneracoes.push(remun);
      series.Encargos_TSU.push(tsu_v);
      series.Seguros_AT.push(sat_v);
      series.Outros_Encargos.push(total - remun - tsu_v - sat_v);
    }
    return series;
  }

  function projectPessoalDepart(scenarioKey, opts = {}) {
    const dr = projectDR(scenarioKey, opts);
    const series = {};
    for (const [k, p] of Object.entries(PESSOAL_DEPART_PESOS)) {
      series[k] = dr.map(r => r.pessoal * p);
    }
    return series;
  }

  // FSE detalhe 2024 (base.yaml)
  const FSE_2024 = {
    Subcontratos: 1492621.48, Eletricidade: 894972.89, Gas_Natural: 447486.44,
    Agua: 89497.29, Manutencao: 224743.22, Transportes_Fretes: 745810.74,
    Seguros: 149262.15, Comunicacoes: 89497.29, Honorarios: 224743.22,
    Rendas: 897573.89, Limpeza: 149262.15, Vigilancia: 134935.93,
    Marketing_Publicidade: 372905.37, Outros_FSE: 2509310.48,
  };

  function projectFSE(scenarioKey) {
    const s = SCENARIOS[scenarioKey];
    const series = {};
    for (const k of Object.keys(FSE_2024)) {
      series[k] = [FSE_2024[k]];
      for (let i = 1; i < YEARS.length; i++) {
        // gás e eletricidade reagem mais ao cenário stress
        const isEnergia = (k === "Gas_Natural" || k === "Eletricidade");
        const mult = isEnergia ? 1.2 : 1.0;
        series[k].push(series[k][i - 1] * (1 + s.fse[i] * mult));
      }
    }
    return series;
  }

  // Hub Logístico — viabilidade
  function hubViability(wacc = 0.08) {
    // Fallback — espelha m6_hub_assumptions.yaml (CAPEX fase 1 otimizado: 3 800 k€)
    const irc_taxa = 0.215;
    const capex = [0, 2280000, 1520000, 0, 0, 0, 0, 0, 0, 0, 0]; // 2025-2034 (idx0 = 2024)
    const dep_anual = 380000;      // 3 800 k€ × 10 %
    const beneficio_anual_base = 310000;
    const pt2030_anual = 171000;   // 1 710 k€ / 10 anos (reconhecimento SNC)
    const fcf_livre = [];
    let cumulative = 0;
    const cumulative_arr = [];
    for (let i = 0; i < 11; i++) {
      const year = 2024 + i;
      let fcf = 0;
      fcf -= capex[i];
      if (year >= 2026) {
        const yIdx = year - 2026;
        const ebitda = (beneficio_anual_base + pt2030_anual) * Math.pow(1.04, yIdx);
        const ebit = ebitda - dep_anual;
        const nopat = ebit > 0 ? ebit * (1 - irc_taxa) : ebit;
        fcf += nopat + dep_anual;
      }
      if (year === 2026) fcf += 2000000; // libertação de inventário (WMS centralizado)
      fcf_livre.push(fcf);
      cumulative += fcf;
      cumulative_arr.push(cumulative);
    }
    // VAN com valor terminal aprox.
    const vt = 500000;
    const vpl = fcf_livre.reduce((a, v, i) => a + v / Math.pow(1 + wacc, i), 0) + vt;
    function npv(rate) {
      return fcf_livre.reduce((a, v, i) => a + v / Math.pow(1 + rate, i), 0) + vt;
    }
    let lo = -0.5, hi = 1.0;
    for (let k = 0; k < 80; k++) {
      const mid = (lo + hi) / 2;
      if (npv(mid) > 0) lo = mid; else hi = mid;
    }
    const tir = (lo + hi) / 2;
    let pay_s = null, pay_a = null;
    let acum_s = 0, acum_a = 0;
    for (let i = 0; i < fcf_livre.length; i++) {
      acum_s += fcf_livre[i];
      acum_a += fcf_livre[i] / Math.pow(1 + wacc, i);
      if (pay_s === null && acum_s > 0) pay_s = i;
      if (pay_a === null && acum_a > 0) pay_a = i;
    }
    return {
      vpl, tir, payback_simples: pay_s, payback_atualizado: pay_a,
      valor_terminal: vt,
      fcf: fcf_livre, fcf_cumulativo: cumulative_arr,
      anos: YEARS.concat([2030, 2031, 2032, 2033, 2034]),
      parametros: { wacc, capex_total: 3800000, beneficio_liquido_anual: 310000 },
    };
  }

  function hubTornado() {
    return [
      { variavel: "Poupança operacional",    low: -2.4, high: 3.1 },
      { variavel: "WACC",                    low: -1.9, high: 1.8 },
      { variavel: "CAPEX base",              low: -1.6, high: 1.6 },
      { variavel: "Crescimento benefícios",  low: -1.2, high: 1.4 },
      { variavel: "Libertação inventário",   low: -0.9, high: 1.0 },
      { variavel: "Subsídio PT2030",         low: -0.7, high: 0.7 },
      { variavel: "OPEX incremental",        low: -0.5, high: 0.6 },
    ];
  }

  // Rolling Forecast 2025 — mensal
  const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
  function rollingForecast(scenarioKey, opts = {}) {
    const s = SCENARIOS[scenarioKey];
    const dr2025 = projectDR(scenarioKey, opts)[1];
    // Sazonalidade PT
    const saz = [0.08,0.08,0.09,0.09,0.09,0.09,0.08,0.06,0.08,0.09,0.09,0.08];
    let cash = 542390.86;
    return MESES.map((m, i) => {
      const vn_m = dr2025.vn * saz[i];
      const cmvmc_m = dr2025.cmvmc * saz[i];
      const fse_m = dr2025.fse / 12;
      let pessoal_m = dr2025.pessoal / 14; // 14 meses (sub férias/natal)
      if (i === 5) pessoal_m *= 2; // Junho
      if (i === 10) pessoal_m *= 2; // Novembro
      const ebitda_m = vn_m + (dr2025.outros_rend / 12) - cmvmc_m - fse_m - pessoal_m - (dr2025.outros_gastos / 12);
      const dep_m = dr2025.dep / 12;
      const ebit_m = ebitda_m - dep_m;
      // tesouraria simplificada
      const rec_m = vn_m * 0.95;
      const pag_m = -(cmvmc_m + fse_m + pessoal_m) * 0.98;
      const inv_m = -dr2025.vn * 0.015 / 12;
      const fin_m = -120000;
      cash = cash + rec_m + pag_m + inv_m + fin_m;
      return {
        mes: m, vn: vn_m, cmvmc: cmvmc_m, fse: fse_m, pessoal: pessoal_m,
        ebitda: ebitda_m, ebit: ebit_m,
        recebimentos: rec_m, pagamentos: pag_m, investimento: inv_m, financiamento: fin_m,
        caixa_fim: cash,
      };
    });
  }

  // Vendas por mercado (globais.yaml)
  const MERCADOS = {
    PT:  { peso: 0.17, label: "Portugal" },
    UE:  { peso: 0.30, label: "União Europeia" },
    USA: { peso: 0.35, label: "Estados Unidos" },
    ROW: { peso: 0.18, label: "Resto do Mundo" },
  };
  const CANAIS = {
    Private_Label: 0.25, Hotelaria: 0.31, Retalho: 0.26, E_Commerce: 0.18,
  };

  // Pressupostos exibidos
  const ASSUMPTIONS = {
    IRC_taxa_geral: 0.20, Derrama_Municipal: 0.015, Derrama_Estadual: 0.0135,
    TSU_Empresa: 0.2375, SIFIDE_taxa_credito: 0.325,
    PMR_dias: 45, PMP_Inventarios_dias: 63, DMI_PA_dias: 160, DMI_MP_dias: 160,
    Caixa_minima: 500000, Caixa_maxima: 1500000,
    Payout_ratio: 0.20, Reserva_legal_pct: 0.05,
    Headcount_2024: 734, Custo_pessoal_2024: 14371357.70,
    Elasticidade_alpha_sem_hub: 0.40, Elasticidade_alpha_com_hub: 0.15,
    Reducao_gas_pecas: 0.05, Eficiencia_gas_anual: 0.03,
  };

  return {
    YEARS, SCENARIOS, MESES, MERCADOS, CANAIS, ASSUMPTIONS,
    DR_2024, FSE_2024, BAL_2024, PESSOAL_CONTAB_2024, PESSOAL_DEPART_PESOS,
    projectDR, projectBalanco, projectDFC, projectKPIs,
    projectFSE, projectEcogres,
    projectPessoalContab, projectPessoalDepart,
    hubViability, hubTornado,
    rollingForecast,
  };
})();
