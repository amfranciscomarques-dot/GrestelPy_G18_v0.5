// app.jsx — Grestel Financial Dashboard

const { useState, useMemo, useEffect } = React;

// -----------------------------------------------------------------------------
// Navigation config
// -----------------------------------------------------------------------------
const NAV = [
  { id: "overview",     label: "Visão Geral",       group: "Síntese" },
  { id: "dr",           label: "Demonstração dos Resultados", group: "Demonstrações" },
  { id: "balanco",      label: "Balanço",           group: "Demonstrações" },
  { id: "dfc",          label: "Fluxos de Caixa",   group: "Demonstrações" },
  { id: "kpis",         label: "KPIs & Rácios",     group: "Análise" },
  { id: "fse",          label: "FSE",               group: "Análise" },
  { id: "pessoal",      label: "Pessoal",            group: "Análise" },
  { id: "rolling",      label: "2025",  group: "Análise" },
  { id: "hub",          label: "Hub Logístico",     group: "Projetos" },
  { id: "ecogres",      label: "Ecogres",           group: "Projetos" },
  { id: "pressupostos", label: "Pressupostos",      group: "Configuração" },
];

// -----------------------------------------------------------------------------
// API adapter utilities
// -----------------------------------------------------------------------------
const API_BASE = "";

function adaptDR(rows) {
  return rows.map(r => ({
    year: r.ano,
    vn: r.vn,
    outros_rend: r.outros_rend,
    cmvmc: -(r.cmvmc || 0),
    fse: -(r.fse || 0),
    pessoal: -(r.gastos_pessoal || 0),
    outros_gastos: -((r.outros_gastos || 0) + (r.imparidades || 0)),
    ebitda: r.ebitda,
    dep: -(r.depreciacoes || 0),
    ebit: r.ebit,
    juros: -(r.juros || 0) - (r.rend_financeiros || 0),
    rai: r.rai,
    irc: -(r.irc || 0),
    rl: r.rl,
  }));
}

function adaptBalanco(rows) {
  return rows.map(r => ({
    year: r.ano,
    AFT_liquido: r.aft_liquido || 0,
    Goodwill: r.goodwill_intang_subs_af || 0,
    Intangiveis: 0,
    Subsidiarias: 0,
    Ativos_Fin_Justo_Valor: 0,
    Outros_Ativos_Fixos: 0,
    Impostos_Diferidos_Ativos: r.impostos_dif_ativos || 0,
    Inventarios: r.inventarios || 0,
    Clientes: r.clientes || 0,
    Outros_AC: (r.outros_ac || 0) + (r.aplicacoes_fin_cp || 0) + (r.eoep_devedor || 0),
    Caixa: r.caixa || 0,
    Capital_Social: r.capital_social || 0,
    Premios_Emissao: r.premios_emissao || 0,
    Outros_IC_Proprio: r.outros_ic_proprio || 0,
    Reservas_Legais: r.reservas_legais || 0,
    Ajust_AF: r.ajust_af || 0,
    Resultados_Transitados: r.resultados_transitados || 0,
    Outras_Var_CP: r.outras_var_cp || 0,
    RL: r.rl || 0,
    Emprestimos_NC: r.emprestimos_nc || 0,
    Impostos_Diferidos_Passivos: r.imp_dif_passivos || 0,
    Emprestimos_C: r.emprestimos_c || 0,
    Fornecedores: r.fornecedores || 0,
    Outros_PC: (r.outros_pc || 0) + (r.eoep_credor || 0) + (r.linha_credito_cp || 0),
    ativo_total: r.total_ativo || 0,
    passivo_total: r.total_passivo || 0,
    capital_total: r.total_cp || 0,
  }));
}

function adaptKPIs(rows) {
  return rows.map(r => ({
    year: r.ano,
    margem_ebitda: r.margem_ebitda || r.ebitda_margin || 0,
    margem_ebit: r.margem_ebit || r.ebit_margin || 0,
    margem_liquida: r.margem_rl || r.rl_margin || 0,
    roa: r.roa || r.ROA || 0,
    roe: r.roe || r.ROE || 0,
    autonomia_financeira: r.autonomia_financeira || 0,
    liquidez_geral: r.liquidez_geral || 0,
    endividamento: r.endividamento || 0,
    cobertura_juros: r.cobertura_juros || 0,
    pmr_dias: r.PMR || 45,
    pmp_dias: r.PMP || 63,
  }));
}

function adaptDFC(rows) {
  return rows.map(r => ({
    year: r.ano,
    rl: r.rl || 0,
    dep_amort: r.dep_amort || 0,
    imparidades: r.imparidades || 0,
    juros_pagos: r.juros_pagos || 0,
    rend_fin: r.rend_fin || 0,
    var_nfm: r.var_nfm || 0,
    irc_pago: r.irc_pago || 0,
    fluxo_operacional: r.fluxo_operacional || 0,
    pag_aft: r.pag_aft || 0,
    pag_intang: r.pag_intang || 0,
    div_recebidos: r.div_recebidos || 0,
    fluxo_investimento: r.fluxo_investimento || 0,
    rec_emprestimos: r.rec_emprestimos || 0,
    pag_emprestimos: r.pag_emprestimos || 0,
    juros_pagos_fin: r.juros_pagos_fin || 0,
    pag_dividendos: r.pag_dividendos || 0,
    fluxo_financiamento: r.fluxo_financiamento || 0,
    variacao_caixa: r.variacao_caixa || 0,
  }));
}

function pivotFSE(rows) {
  const grouped = {};
  for (const row of rows) {
    if (!grouped[row.rubrica]) grouped[row.rubrica] = [];
    grouped[row.rubrica].push({ ano: row.ano, valor: row.valor });
  }
  const result = {};
  for (const [rubrica, entries] of Object.entries(grouped)) {
    result[rubrica] = entries.sort((a, b) => a.ano - b.ano).map(e => e.valor);
  }
  return result;
}

function pivotPessoal(rows, key) {
  const grouped = {};
  for (const row of rows) {
    const k = row[key];
    if (!grouped[k]) grouped[k] = [];
    grouped[k].push({ ano: row.ano, valor: row.valor });
  }
  const result = {};
  for (const [k, entries] of Object.entries(grouped)) {
    result[k] = entries.sort((a, b) => a.ano - b.ano).map(e => e.valor);
  }
  return result;
}

// -----------------------------------------------------------------------------
// Shell
// -----------------------------------------------------------------------------
function App() {
  const [view, setView] = useState("overview");
  const [scenario, setScenario] = useState("Base");
  const [hubOn, setHubOn] = useState(false);
  // Ecogres é subsidiária — sempre consolidada
  const ecogresOn = true;

  const [apiData, setApiData] = useState(null);
  const [apiStatus, setApiStatus] = useState("loading");
  const [lastRun, setLastRun] = useState(null);
  const [apiEff, setApiEff] = useState(null);

  useEffect(() => {
    setApiStatus("loading");
    const params = new URLSearchParams({ hub_on: hubOn, ecogres_on: ecogresOn });
    fetch(`${API_BASE}/api/scenarios/all?${params}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        setApiData(data);
        setApiStatus("ok");
        setLastRun(new Date());
      })
      .catch(() => setApiStatus("error"));
  }, [hubOn, ecogresOn]);

  useEffect(() => {
    const params = new URLSearchParams({ cenario: scenario, hub_on: hubOn, ecogres_on: ecogresOn });
    fetch(`${API_BASE}/api/assumptions/effective?${params}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => setApiEff(data.effective ?? null))
      .catch(() => setApiEff(null));
  }, [scenario, hubOn, ecogresOn]);

  const ctx = useMemo(() => {
    if (apiData && apiData[scenario]) {
      const sc = apiData[scenario];
      const dr = adaptDR(sc.dr.rows);
      const bal = adaptBalanco(sc.balanco.rows);
      const dfc = adaptDFC(sc.dfc.rows);
      const kpis = adaptKPIs(sc.kpis.rows);
      const fse = pivotFSE(sc.fse_detalhe_anual.rows);
      const pessoal_contab = pivotPessoal((sc.pessoal_contab_anual?.rows) || [], "rubrica");
      const pessoal_depart = pivotPessoal((sc.pessoal_depart_anual?.rows) || [], "departamento");
      const allDR = {};
      for (const k of Object.keys(apiData)) allDR[k] = adaptDR(apiData[k].dr.rows);
      return { dr, bal, dfc, kpis, fse, pessoal_contab, pessoal_depart, scenario, hubOn, ecogresOn, allDR, eff: apiEff };
    }
    // Fallback to client-side while API loads or on error
    const dr = GRESTEL.projectDR(scenario, { hubOn, ecogresOn });
    const bal = GRESTEL.projectBalanco(dr, { hubOn });
    const dfc = GRESTEL.projectDFC(dr, bal, { hubOn });
    const kpis = GRESTEL.projectKPIs(dr, bal);
    const fse = GRESTEL.projectFSE(scenario);
    const pessoal_contab = GRESTEL.projectPessoalContab(scenario, { hubOn, ecogresOn });
    const pessoal_depart = GRESTEL.projectPessoalDepart(scenario, { hubOn, ecogresOn });
    return { dr, bal, dfc, kpis, fse, pessoal_contab, pessoal_depart, scenario, hubOn, ecogresOn, allDR: null, eff: apiEff };
  }, [apiData, scenario, hubOn, ecogresOn, apiEff]);

  return (
    <div className="app">
      <Sidebar view={view} setView={setView} apiStatus={apiStatus} lastRun={lastRun} />
      <div className="main">
        <Topbar
          view={view}
          scenario={scenario}
          setScenario={setScenario}
          hubOn={hubOn}
          setHubOn={setHubOn}
        />
        <div className="content">
          {view === "overview" && <OverviewView ctx={ctx} />}
          {view === "dr" && <DRView ctx={ctx} />}
          {view === "balanco" && <BalancoView ctx={ctx} />}
          {view === "dfc" && <DFCView ctx={ctx} />}
          {view === "kpis" && <KPIView ctx={ctx} />}
          {view === "fse" && <FSEView ctx={ctx} />}
          {view === "pessoal" && <PessoalView ctx={ctx} />}
          {view === "rolling" && <RollingView ctx={ctx} />}
          {view === "hub" && <HubView ctx={ctx} />}
          {view === "ecogres" && <EcogresView ctx={ctx} />}
          {view === "pressupostos" && <PressupostosView ctx={ctx} />}
        </div>
      </div>
    </div>
  );
}

function Sidebar({ view, setView, apiStatus, lastRun }) {
  const groups = {};
  for (const item of NAV) {
    (groups[item.group] ||= []).push(item);
  }
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">G</div>
        <div>
          <div className="brand-name">Grestel</div>
          <div className="brand-sub">Modelo financeiro · v0.5</div>
        </div>
      </div>
      <nav className="nav">
        {Object.entries(groups).map(([g, items]) => (
          <div key={g} className="nav-group">
            <div className="nav-label">{g}</div>
            {items.map(it => (
              <button
                key={it.id}
                className={"nav-item " + (view === it.id ? "is-active" : "")}
                onClick={() => setView(it.id)}
              >
                {it.label}
              </button>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="foot-row">
          <span>API</span>
          <span className={"dot dot--" + (apiStatus === "ok" ? "ok" : apiStatus === "error" ? "err" : "warn")} />
          <span className="mono">{apiStatus === "ok" ? "8000" : apiStatus === "error" ? "offline" : "…"}</span>
        </div>
        <div className="foot-row"><span>Engine</span><span className="mono">v0.5.0</span></div>
        <div className="foot-row">
          <span>Última corrida</span>
          <span className="mono">
            {lastRun
              ? lastRun.toLocaleDateString("pt-PT", { day: "2-digit", month: "short", year: "2-digit" }) + " · " +
                lastRun.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })
              : "—"}
          </span>
        </div>
      </div>
    </aside>
  );
}

function Topbar({ view, scenario, setScenario, hubOn, setHubOn }) {
  const title = NAV.find(n => n.id === view)?.label || "";
  const desc = GRESTEL.SCENARIOS[scenario].desc;
  return (
    <header className="topbar">
      <div className="topbar-l">
        <div className="crumbs">
          <span className="crumb-muted">{NAV.find(n => n.id === view)?.group}</span>
          <span className="crumb-sep">/</span>
          <span className="crumb">{title}</span>
        </div>
        <div className="topbar-desc">{desc}</div>
      </div>
      <div className="topbar-r">
        <div className="seg">
          {Object.keys(GRESTEL.SCENARIOS).map(k => (
            <button
              key={k}
              className={"seg-btn " + (scenario === k ? "is-on" : "")}
              onClick={() => setScenario(k)}
            >{k}</button>
          ))}
        </div>
        <Toggle label="Hub Logístico" on={hubOn} onChange={setHubOn} />
        <div className="chip-static" title="Subsidiária — sempre consolidada">
          <span className="dot dot--ok" /> Ecogres consolidada
        </div>
        <button className="btn-ghost">Exportar</button>
      </div>
    </header>
  );
}

function Toggle({ label, on, onChange }) {
  return (
    <button className={"toggle " + (on ? "is-on" : "")} onClick={() => onChange(!on)}>
      <span className="toggle-track"><span className="toggle-thumb" /></span>
      <span className="toggle-label">{label}</span>
    </button>
  );
}

// -----------------------------------------------------------------------------
// KPI card
// -----------------------------------------------------------------------------
function KPI({ label, value, sub, trend, spark, sparkColor, tone, hint }) {
  return (
    <div className={"kpi " + (tone ? "kpi--" + tone : "")}>
      <div className="kpi-label">{label}{hint && <span className="kpi-hint" title={hint}>·</span>}</div>
      <div className="kpi-row">
        <div className="kpi-value">{value}</div>
        {spark && <Sparkline values={spark} color={sparkColor || "var(--muted)"} width={80} height={28} />}
      </div>
      <div className="kpi-foot">
        {trend != null && <span className={"delta " + (trend >= 0 ? "delta--pos" : "delta--neg")}>{fmt.pctSigned(trend)}</span>}
        {sub && <span className="kpi-sub">{sub}</span>}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Section panel
// -----------------------------------------------------------------------------
function Panel({ title, sub, right, children, pad = true }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <div className="panel-title">{title}</div>
          {sub && <div className="panel-sub">{sub}</div>}
        </div>
        {right && <div className="panel-right">{right}</div>}
      </div>
      <div className={"panel-body " + (pad ? "" : "panel-body--flat")}>{children}</div>
    </div>
  );
}

// =============================================================================
// VIEWS
// =============================================================================

// ---- Overview ---------------------------------------------------------------
function OverviewView({ ctx }) {
  const { dr, kpis } = ctx;
  const cur = dr.find(r => r.year === 2025);
  const prev = dr.find(r => r.year === 2024);
  const k2029 = kpis.find(r => r.year === 2029);

  const compareSeries = useMemo(() => {
    const colors = { Base: "var(--ink)", Upside: "var(--pos)", Downside: "var(--accent)", Stress: "var(--neg)" };
    return Object.keys(GRESTEL.SCENARIOS).map(k => {
      const d = ctx.allDR?.[k] || GRESTEL.projectDR(k, { hubOn: ctx.hubOn, ecogresOn: ctx.ecogresOn });
      return {
        labels: GRESTEL.YEARS.map(String),
        values: d.map(r => r.vn),
        color: colors[k],
        width: k === ctx.scenario ? 2.4 : 1.4,
        dash: k === ctx.scenario ? null : "3 3",
        name: k,
      };
    });
  }, [ctx.hubOn, ctx.ecogresOn, ctx.scenario, ctx.allDR]);

  const ebitdaSeries = [{
    labels: GRESTEL.YEARS.map(String),
    values: dr.map(r => r.ebitda),
    color: "var(--accent)",
    fill: true,
  }];

  const margemSeries = [
    { labels: GRESTEL.YEARS.map(String), values: dr.map(r => r.ebitda / r.vn), color: "var(--accent)" },
    { labels: GRESTEL.YEARS.map(String), values: dr.map(r => r.rl / r.vn), color: "var(--ink)" },
  ];

  return (
    <>
      <div className="grid-kpis">
        <KPI
          label="Volume de Negócios"
          value={fmt.eurC(cur.vn)}
          trend={(cur.vn - prev.vn) / prev.vn}
          sub="vs. 2024 real"
          spark={dr.map(r => r.vn)}
          sparkColor="var(--ink)"
        />
        <KPI
          label="EBITDA"
          value={fmt.eurC(cur.ebitda)}
          trend={(cur.ebitda - prev.ebitda) / prev.ebitda}
          sub={"margem " + fmt.pct(cur.ebitda / cur.vn)}
          spark={dr.map(r => r.ebitda)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="Resultado Líquido"
          value={fmt.eurC(cur.rl)}
          trend={(cur.rl - prev.rl) / prev.rl}
          sub={"margem " + fmt.pct(cur.rl / cur.vn)}
          spark={dr.map(r => r.rl)}
          sparkColor="var(--pos)"
        />
        <KPI
          label="Margem EBITDA"
          value={fmt.pct(cur.ebitda / cur.vn)}
          trend={(cur.ebitda / cur.vn) - (prev.ebitda / prev.vn)}
          sub="pontos percentuais vs 2024"
          spark={dr.map(r => r.ebitda / r.vn)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="ROE 2029"
          value={fmt.pct(k2029.roe)}
          sub={"autonomia fin. " + fmt.pct(k2029.autonomia_financeira)}
          spark={kpis.map(r => r.roe)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="Caixa 2029"
          value={fmt.eurC(ctx.bal[ctx.bal.length - 1].Caixa)}
          sub={"endivid. " + fmt.pct(k2029.endividamento)}
          spark={ctx.bal.map(r => r.Caixa)}
          sparkColor="var(--ink)"
        />
      </div>

      <div className="grid-2-3">
        <Panel
          title="Volume de Negócios · Comparação de cenários"
          sub="€ milhões · 2024 real + projeção 2025–2029"
          right={<Legend items={[
            { label: "Base", color: "var(--ink)" },
            { label: "Upside", color: "var(--pos)" },
            { label: "Downside", color: "var(--accent)" },
            { label: "Stress", color: "var(--neg)" },
          ]} />}
        >
          <LineChart series={compareSeries} height={300} />
        </Panel>
        <Panel title="EBITDA" sub={"Cenário " + ctx.scenario}>
          <LineChart series={ebitdaSeries} height={300} />
        </Panel>
      </div>

      <div className="grid-2-3">
        <Panel
          title="Margens · EBITDA vs Resultado Líquido"
          sub="evolução em % do volume de negócios"
          right={<Legend items={[{ label: "Margem EBITDA", color: "var(--accent)" }, { label: "Margem Líquida", color: "var(--ink)" }]} />}
        >
          <LineChart series={margemSeries} height={260} yFormat={(v) => fmt.pct(v, 0)} />
        </Panel>
        <Panel title="Mix de mercado · vendas 2024" sub="por geografia">
          {(() => {
            // Terracota family — burnt sienna → terracota → ocre → areia.
            const geoPalette = [
              "oklch(0.34 0.075 40)",   // Portugal — burnt sienna escuro
              "oklch(0.54 0.115 45)",   // União Europeia — terracota
              "oklch(0.68 0.105 65)",   // Estados Unidos — ocre / clay
              "oklch(0.83 0.035 75)",   // Resto do Mundo — areia
            ];
            const chanPalette = [
              "oklch(0.34 0.075 40)",
              "oklch(0.54 0.115 45)",
              "oklch(0.68 0.105 65)",
              "oklch(0.83 0.035 75)",
            ];
            // Text colors — light text on the two darker segments, dark on the lighter two.
            const chanTextColor = [
              "var(--surface)",
              "var(--surface)",
              "var(--ink)",
              "var(--ink)",
            ];
            const totalVN = prev.vn;
            const geoItems = Object.entries(GRESTEL.MERCADOS).map(([k, v], i) => ({
              label: v.label,
              value: totalVN * v.peso,
              color: geoPalette[i],
            }));
            const chanItems = Object.entries(GRESTEL.CANAIS).map(([k, v], i) => ({
              label: k.replace(/_/g, " "),
              value: v,
              amount: totalVN * v,
              color: chanPalette[i],
              textColor: chanTextColor[i],
            }));
            return (
              <>
                <div className="donut-row">
                  <Donut items={geoItems} size={172} thickness={26} />
                  <div className="legend-col">
                    {geoItems.map((it, i) => (
                      <div key={i} className="legend-row">
                        <span className="swatch" style={{ background: it.color }} />
                        <span className="legend-label">{it.label}</span>
                        <span className="legend-value mono">{fmt.pct(it.value / totalVN, 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="sub-section">
                  <div className="sub-label">Canais 2024</div>
                  <StackedBar items={chanItems} height={34} />
                  <div className="legend-h" style={{ marginTop: 8 }}>
                    {chanItems.map((it, i) => (
                      <div key={i} className="legend-h-item">
                        <span className="swatch" style={{ background: it.color }} />
                        <span>{it.label}</span>
                        <span className="mono">{fmt.pct(it.value, 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            );
          })()}
        </Panel>
      </div>

      <Panel title="Quadro-síntese · 2025–2029" sub="cenário ativo">
        <table className="ftable">
          <thead>
            <tr>
              <th></th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
            </tr>
          </thead>
          <tbody>
            <FRow label="Volume de Negócios" values={dr.map(r => r.vn)} />
            <FRow label="EBITDA" values={dr.map(r => r.ebitda)} />
            <FRow label="EBIT" values={dr.map(r => r.ebit)} />
            <FRow label="Resultado Líquido" values={dr.map(r => r.rl)} bold />
            <tr className="row-sep"><td colSpan={GRESTEL.YEARS.length + 1}></td></tr>
            <FRow label="Margem EBITDA" values={dr.map(r => r.ebitda / r.vn)} fmt={(v) => fmt.pct(v)} />
            <FRow label="Margem Líquida" values={dr.map(r => r.rl / r.vn)} fmt={(v) => fmt.pct(v)} />
          </tbody>
        </table>
      </Panel>
    </>
  );
}

function FRow({ label, values, bold, fmt: f = fmt.eur }) {
  return (
    <tr className={bold ? "is-bold" : ""}>
      <td>{label}</td>
      {values.map((v, i) => <td key={i} className="mono num">{f(v)}</td>)}
    </tr>
  );
}

function Legend({ items }) {
  return (
    <div className="legend">
      {items.map((it, i) => (
        <div key={i} className="legend-row">
          <span className="swatch" style={{ background: it.color }} />
          <span className="legend-label">{it.label}</span>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { App, Sidebar, Topbar, Toggle, KPI, Panel, FRow, Legend });
