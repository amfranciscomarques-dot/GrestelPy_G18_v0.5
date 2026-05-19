// views.jsx — Demais views do dashboard (DR, Balanço, DFC, KPIs, FSE, Rolling, Hub, Ecogres, Pressupostos)

// Shared palettes for mix charts (donuts + stacked bars).
// Terracota family — same hue band, lightness ramp from burnt sienna to sand.
const MIX_PALETTE_4 = [
  "oklch(0.34 0.075 40)",   // burnt sienna — escuro
  "oklch(0.54 0.115 45)",   // terracota
  "oklch(0.68 0.105 65)",   // ocre / clay
  "oklch(0.83 0.035 75)",   // areia / cream
];
const MIX_PALETTE_4_TEXT = ["var(--surface)", "var(--surface)", "var(--ink)", "var(--ink)"];
const MIX_PALETTE_7 = [
  "oklch(0.30 0.070 35)",
  "oklch(0.42 0.100 40)",
  "oklch(0.54 0.115 45)",
  "oklch(0.64 0.110 55)",
  "oklch(0.72 0.090 70)",
  "oklch(0.80 0.050 80)",
  "oklch(0.87 0.022 80)",
];

// ---- Demonstração de Resultados ---------------------------------------------
function DRView({ ctx }) {
  const { dr } = ctx;
  const rubricas = [
    { label: "Vendas e Serviços Prestados", key: "vn", strong: true },
    { label: "Outros Rendimentos", key: "outros_rend" },
    { label: "Custo das Mercadorias Vendidas e MC", key: "cmvmc", neg: true },
    { label: "Fornecimentos e Serviços Externos", key: "fse", neg: true },
    { label: "Gastos com o Pessoal", key: "pessoal", neg: true },
    { label: "Outros Gastos / Imparidades", key: "outros_gastos", neg: true },
    { label: "EBITDA", key: "ebitda", subtotal: true },
    { label: "Depreciações e Amortizações", key: "dep", neg: true },
    { label: "EBIT", key: "ebit", subtotal: true },
    { label: "Juros Líquidos", key: "juros", neg: true },
    { label: "Resultado Antes de Impostos", key: "rai", subtotal: true },
    { label: "IRC + Derramas", key: "irc", neg: true },
    { label: "Resultado Líquido", key: "rl", total: true },
  ];

  // EBITDA bridge: 2024 -> 2025
  const r24 = dr[0], r25 = dr[1];
  const bridge = [
    { label: "EBITDA 2024", value: r24.ebitda, type: "total" },
    { label: "Δ Vendas", value: r25.vn - r24.vn, type: "delta" },
    { label: "Δ Outros Rend.", value: r25.outros_rend - r24.outros_rend, type: "delta" },
    { label: "Δ CMVMC", value: -(r25.cmvmc - r24.cmvmc), type: "delta" },
    { label: "Δ FSE", value: -(r25.fse - r24.fse), type: "delta" },
    { label: "Δ Pessoal", value: -(r25.pessoal - r24.pessoal), type: "delta" },
    { label: "Δ Outros Gastos", value: -(r25.outros_gastos - r24.outros_gastos), type: "delta" },
    { label: "EBITDA 2025", value: r25.ebitda, type: "total" },
  ];

  return (
    <>
      <div className="grid-3">
        <KPI label="VN 2025"    value={fmt.eurC(r25.vn)}     trend={(r25.vn - r24.vn) / r24.vn} sub="vs 2024 auditado" />
        <KPI label="EBITDA 2025" value={fmt.eurC(r25.ebitda)} trend={(r25.ebitda - r24.ebitda) / r24.ebitda} sub={"margem " + fmt.pct(r25.ebitda / r25.vn)} />
        <KPI label="RL 2025"     value={fmt.eurC(r25.rl)}     trend={(r25.rl - r24.rl) / r24.rl} sub={"margem " + fmt.pct(r25.rl / r25.vn)} />
      </div>

      <Panel title="Ponte EBITDA · 2024 → 2025" sub="contribuição de cada rubrica para a variação">
        <WaterfallChart items={bridge} height={260} />
      </Panel>

      <Panel title="Demonstração de Resultados" sub="€ · valores anuais">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th style={{ width: "32%" }}>Rubrica</th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
              <th className="mono num">CAGR 25-29</th>
            </tr>
          </thead>
          <tbody>
            {rubricas.map((r, i) => {
              const vals = dr.map(d => d[r.key]);
              const cagr = Math.pow(vals[5] / vals[1], 1 / 4) - 1;
              return (
                <tr key={r.key} className={[r.strong ? "is-bold" : "", r.subtotal ? "is-subtotal" : "", r.total ? "is-total" : ""].join(" ")}>
                  <td>{r.label}</td>
                  {vals.map((v, ix) => (
                    <td key={ix} className="mono num">{r.neg ? "(" + fmt.eur(Math.abs(v)).replace("€", "€") + ")" : fmt.eur(v)}</td>
                  ))}
                  <td className="mono num">{fmt.pctSigned(cagr)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- Balanço ----------------------------------------------------------------
function BalancoView({ ctx }) {
  const { bal } = ctx;
  const last = bal[bal.length - 1];
  const first = bal[0];

  const ativoRows = [
    { label: "Activos Fixos Tangíveis", key: "AFT_liquido" },
    { label: "Goodwill", key: "Goodwill" },
    { label: "Intangíveis", key: "Intangiveis" },
    { label: "Participações em Subsidiárias", key: "Subsidiarias" },
    { label: "Ativos Financeiros (JV)", key: "Ativos_Fin_Justo_Valor" },
    { label: "Outros Activos Fixos", key: "Outros_Ativos_Fixos" },
  ];
  const correntesRows = [
    { label: "Inventários", key: "Inventarios" },
    { label: "Clientes", key: "Clientes" },
    { label: "Outros Activos Correntes", key: "Outros_AC" },
    { label: "Caixa e Equivalentes", key: "Caixa" },
  ];
  const cpRows = [
    { label: "Capital Social", key: "Capital_Social" },
    { label: "Prémios de Emissão", key: "Premios_Emissao" },
    { label: "Outros IC Próprio", key: "Outros_IC_Proprio" },
    { label: "Reservas Legais", key: "Reservas_Legais" },
    { label: "Ajustamentos AF", key: "Ajust_AF" },
    { label: "Resultados Transitados", key: "Resultados_Transitados" },
    { label: "Outras Var. CP", key: "Outras_Var_CP" },
    { label: "Resultado Líquido", key: "RL" },
  ];
  const passivoRows = [
    { label: "Empréstimos NC", key: "Emprestimos_NC" },
    { label: "Impostos Diferidos Passivos", key: "Impostos_Diferidos_Passivos" },
    { label: "Empréstimos Correntes", key: "Emprestimos_C" },
    { label: "Fornecedores", key: "Fornecedores" },
    { label: "Outros Passivos Correntes", key: "Outros_PC" },
  ];

  // Stacked bar: Ativo composition over years
  const ativoStack = bal.map(b => ({
    label: String(b.year),
    bars: [
      { key: "AFT", value: b.AFT_liquido, color: "var(--ink)" },
      { key: "Intangíveis", value: b.Goodwill + b.Intangiveis + b.Subsidiarias + b.Outros_Ativos_Fixos + b.Ativos_Fin_Justo_Valor, color: "var(--accent)" },
      { key: "Inventários", value: b.Inventarios, color: "var(--pos)" },
      { key: "Clientes", value: b.Clientes, color: "var(--muted)" },
      { key: "Outros AC", value: b.Outros_AC, color: "var(--faint-strong)" },
      { key: "Caixa", value: b.Caixa, color: "var(--neg)" },
    ]
  }));

  return (
    <>
      <div className="grid-3">
        <KPI label="Activo Total"    value={fmt.eurC(last.ativo_total)}   trend={(last.ativo_total - first.ativo_total) / first.ativo_total} sub={"2029 · vs 2024"} />
        <KPI label="Capital Próprio" value={fmt.eurC(last.capital_total)} trend={(last.capital_total - first.capital_total) / first.capital_total} sub="2029" />
        <KPI label="Dívida Total"    value={fmt.eurC(last.Emprestimos_NC + last.Emprestimos_C)} trend={((last.Emprestimos_NC + last.Emprestimos_C) - (first.Emprestimos_NC + first.Emprestimos_C)) / (first.Emprestimos_NC + first.Emprestimos_C)} sub="NC + Correntes" />
      </div>

      <Panel title="Composição do Activo · 2024 → 2029" sub="€ · barras empilhadas">
        <BarChart groups={ativoStack} stacked height={280} />
        <div className="legend-h" style={{ marginTop: 8 }}>
          {[
            { label: "AFT", color: "var(--ink)" },
            { label: "Intangíveis & participações", color: "var(--accent)" },
            { label: "Inventários", color: "var(--pos)" },
            { label: "Clientes", color: "var(--muted)" },
            { label: "Outros AC", color: "var(--faint-strong)" },
            { label: "Caixa", color: "var(--neg)" },
          ].map((it, i) => (
            <div key={i} className="legend-h-item">
              <span className="swatch" style={{ background: it.color }} />
              <span>{it.label}</span>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid-2">
        <Panel title="ACTIVO" sub="€">
          <table className="ftable ftable--dense">
            <thead><tr><th>Rubrica</th>{GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}</tr></thead>
            <tbody>
              <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Activo Não Corrente</td></tr>
              {ativoRows.map(r => (
                <tr key={r.key}><td>{r.label}</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b[r.key])}</td>)}</tr>
              ))}
              <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Activo Corrente</td></tr>
              {correntesRows.map(r => (
                <tr key={r.key}><td>{r.label}</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b[r.key])}</td>)}</tr>
              ))}
              <tr className="is-total">
                <td>Total Activo</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b.ativo_total)}</td>)}
              </tr>
            </tbody>
          </table>
        </Panel>

        <Panel title="CAPITAL PRÓPRIO + PASSIVO" sub="€">
          <table className="ftable ftable--dense">
            <thead><tr><th>Rubrica</th>{GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}</tr></thead>
            <tbody>
              <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Capital Próprio</td></tr>
              {cpRows.map(r => (
                <tr key={r.key}><td>{r.label}</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b[r.key])}</td>)}</tr>
              ))}
              <tr className="is-subtotal">
                <td>Subtotal CP</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b.capital_total)}</td>)}
              </tr>
              <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Passivo</td></tr>
              {passivoRows.map(r => (
                <tr key={r.key}><td>{r.label}</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b[r.key])}</td>)}</tr>
              ))}
              <tr className="is-subtotal">
                <td>Subtotal Passivo</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b.passivo_total)}</td>)}
              </tr>
              <tr className="is-total">
                <td>Total CP + Passivo</td>{bal.map((b, i) => <td key={i} className="mono num">{fmt.eur(b.capital_total + b.passivo_total)}</td>)}
              </tr>
            </tbody>
          </table>
        </Panel>
      </div>
    </>
  );
}

// ---- DFC -------------------------------------------------------------------
function DFCView({ ctx }) {
  const { dfc } = ctx;
  const [year, setYear] = useState(2025);
  const r = dfc.find(d => d.year === year);
  const items = [
    { label: "Recebimentos clientes", value: r.recebimentos, type: "delta" },
    { label: "Pagamentos fornecedores", value: r.pag_fornecedores, type: "delta" },
    { label: "Pagamentos pessoal", value: r.pag_pessoal, type: "delta" },
    { label: "Fluxo operacional", value: r.fluxo_operacional, type: "total" },
    { label: "CAPEX", value: r.capex_aft, type: "delta" },
    { label: "Dividendos recebidos", value: r.dividendos_recebidos, type: "delta" },
    { label: "Fluxo investimento", value: r.fluxo_investimento, type: "total" },
    { label: "Recebimento emp.", value: r.rec_emprestimos, type: "delta" },
    { label: "Pagamento emp.", value: r.pag_emprestimos, type: "delta" },
    { label: "Fluxo financiamento", value: r.fluxo_financiamento, type: "total" },
    { label: "Variação Caixa", value: r.variacao_caixa, type: "total" },
  ];

  return (
    <>
      <div className="grid-3">
        <KPI label={"Fluxo Operacional " + year} value={fmt.eurC(r.fluxo_operacional)} tone={r.fluxo_operacional >= 0 ? "pos" : "neg"} />
        <KPI label={"Fluxo Investimento " + year} value={fmt.eurC(r.fluxo_investimento)} tone={r.fluxo_investimento >= 0 ? "pos" : "neg"} />
        <KPI label={"Fluxo Financiamento " + year} value={fmt.eurC(r.fluxo_financiamento)} tone={r.fluxo_financiamento >= 0 ? "pos" : "neg"} />
      </div>

      <Panel
        title={"Demonstração de Fluxos de Caixa · " + year}
        sub="método directo"
        right={
          <div className="seg seg--sm">
            {GRESTEL.YEARS.map(y => (
              <button key={y} className={"seg-btn " + (year === y ? "is-on" : "")} onClick={() => setYear(y)}>{y}</button>
            ))}
          </div>
        }
      >
        <WaterfallChart items={items} height={360} />
      </Panel>

      <Panel title="Fluxos por ano" sub="€ · valores anuais">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Rubrica</th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
            </tr>
          </thead>
          <tbody>
            <FRow label="Recebimentos clientes" values={dfc.map(d => d.recebimentos)} />
            <FRow label="Pagamentos fornecedores" values={dfc.map(d => d.pag_fornecedores)} />
            <FRow label="Pagamentos pessoal" values={dfc.map(d => d.pag_pessoal)} />
            <tr className="is-subtotal"><td>Fluxo operacional</td>{dfc.map((d, i) => <td key={i} className="mono num">{fmt.eur(d.fluxo_operacional)}</td>)}</tr>
            <FRow label="CAPEX" values={dfc.map(d => d.capex_aft)} />
            <FRow label="Dividendos recebidos" values={dfc.map(d => d.dividendos_recebidos)} />
            <tr className="is-subtotal"><td>Fluxo investimento</td>{dfc.map((d, i) => <td key={i} className="mono num">{fmt.eur(d.fluxo_investimento)}</td>)}</tr>
            <FRow label="Recebimentos empréstimos" values={dfc.map(d => d.rec_emprestimos)} />
            <FRow label="Pagamentos empréstimos" values={dfc.map(d => d.pag_emprestimos)} />
            <tr className="is-subtotal"><td>Fluxo financiamento</td>{dfc.map((d, i) => <td key={i} className="mono num">{fmt.eur(d.fluxo_financiamento)}</td>)}</tr>
            <tr className="is-total"><td>Variação Caixa</td>{dfc.map((d, i) => <td key={i} className="mono num">{fmt.eur(d.variacao_caixa)}</td>)}</tr>
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- KPIs / Rácios ---------------------------------------------------------
function KPIView({ ctx }) {
  const { kpis } = ctx;
  const rows = [
    { label: "Margem EBITDA",      key: "margem_ebitda",       fmt: v => fmt.pct(v) },
    { label: "Margem EBIT",        key: "margem_ebit",         fmt: v => fmt.pct(v) },
    { label: "Margem Líquida",     key: "margem_liquida",      fmt: v => fmt.pct(v) },
    { label: "ROA",                key: "roa",                 fmt: v => fmt.pct(v) },
    { label: "ROE",                key: "roe",                 fmt: v => fmt.pct(v) },
    { label: "Autonomia Financeira", key: "autonomia_financeira", fmt: v => fmt.pct(v) },
    { label: "Endividamento",      key: "endividamento",       fmt: v => fmt.pct(v) },
    { label: "Liquidez Geral",     key: "liquidez_geral",      fmt: v => fmt.ratio(v) },
    { label: "Cobertura de Juros", key: "cobertura_juros",     fmt: v => fmt.ratio(v) },
    { label: "PMR (dias)",         key: "pmr_dias",            fmt: v => fmt.num(v) + " d" },
    { label: "PMP (dias)",         key: "pmp_dias",            fmt: v => fmt.num(v) + " d" },
  ];
  return (
    <Panel title="KPIs & rácios financeiros" sub="evolução 2024–2029">
      <table className="ftable">
        <thead>
          <tr>
            <th>Rácio</th>
            <th className="num">Tendência</th>
            {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const vals = kpis.map(k => k[r.key]);
            return (
              <tr key={r.key}>
                <td>{r.label}</td>
                <td className="num"><Sparkline values={vals} width={80} height={24} color="var(--accent)" /></td>
                {vals.map((v, ix) => <td key={ix} className="mono num">{r.fmt(v)}</td>)}
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}

// ---- FSE -------------------------------------------------------------------
function FSEView({ ctx }) {
  const { fse } = ctx;
  const keys = Object.keys(fse);
  const total = GRESTEL.YEARS.map((_, i) => keys.reduce((a, k) => a + fse[k][i], 0));

  const sorted = [...keys].sort((a, b) => fse[b][0] - fse[a][0]);
  const top = sorted.slice(0, 6);
  const rest = sorted.slice(6);
  const restSum = GRESTEL.YEARS.map((_, i) => rest.reduce((a, k) => a + fse[k][i], 0));

  const palette = MIX_PALETTE_7;

  const stackGroups = GRESTEL.YEARS.map((y, i) => ({
    label: String(y),
    bars: top.map((k, ki) => ({ key: k, value: fse[k][i], color: palette[ki] })).concat([
      { key: "Outros", value: restSum[i], color: palette[6] }
    ]),
  }));

  const donutItems = top.map((k, ki) => ({ label: k.replace(/_/g, " "), value: fse[k][0], color: palette[ki] }))
    .concat([{ label: "Outros", value: restSum[0], color: palette[6] }]);

  return (
    <>
      <div className="grid-3">
        <KPI label="FSE 2024" value={fmt.eurC(total[0])} sub="auditado · R&C 2024" />
        <KPI label="FSE 2025" value={fmt.eurC(total[1])} trend={(total[1] - total[0]) / total[0]} />
        <KPI label="FSE 2029" value={fmt.eurC(total[5])} trend={(total[5] - total[1]) / total[1]} sub="vs 2025" />
      </div>

      <div className="grid-2-3">
        <Panel title="FSE · composição por ano" sub="€ · barras empilhadas">
          <BarChart groups={stackGroups} stacked height={300} />
        </Panel>
        <Panel title="Mix 2024" sub="€ · 14 rubricas">
          <Donut items={donutItems} />
          <div className="legend-col" style={{ marginTop: 10 }}>
            {donutItems.map((it, i) => (
              <div key={i} className="legend-row">
                <span className="swatch" style={{ background: it.color }} />
                <span className="legend-label">{it.label}</span>
                <span className="legend-value mono">{fmt.eurC(it.value)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel title="FSE · detalhe por rubrica" sub="€ · 14 rubricas declaradas em contrato">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Rubrica</th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
              <th className="mono num">% 2024</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(k => (
              <tr key={k}>
                <td>{k.replace(/_/g, " ")}</td>
                {GRESTEL.YEARS.map((_, i) => <td key={i} className="mono num">{fmt.eur(fse[k][i])}</td>)}
                <td className="mono num">{fmt.pct(fse[k][0] / total[0])}</td>
              </tr>
            ))}
            <tr className="is-total">
              <td>Total FSE</td>
              {total.map((v, i) => <td key={i} className="mono num">{fmt.eur(v)}</td>)}
              <td></td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- Rolling Forecast 2025 -------------------------------------------------
function RollingView({ ctx }) {
  const rf = useMemo(() => GRESTEL.rollingForecast(ctx.scenario, { hubOn: ctx.hubOn, ecogresOn: ctx.ecogresOn }),
                     [ctx.scenario, ctx.hubOn, ctx.ecogresOn]);

  const cashSeries = [{ labels: rf.map(r => r.mes), values: rf.map(r => r.caixa_fim), color: "var(--accent)", fill: true }];
  const vendasGroups = rf.map(r => ({
    label: r.mes,
    bars: [{ key: "vn", value: r.vn, color: "var(--ink)" }],
  }));

  return (
    <>
      <div className="grid-4">
        <KPI label="VN acumulado" value={fmt.eurC(rf.reduce((a, r) => a + r.vn, 0))} sub="12 meses · 2025" />
        <KPI label="EBITDA acumulado" value={fmt.eurC(rf.reduce((a, r) => a + r.ebitda, 0))} />
        <KPI label="Caixa Dez 2025" value={fmt.eurC(rf[11].caixa_fim)} tone={rf[11].caixa_fim >= 500000 ? "pos" : "neg"} />
        <KPI label="Caixa mín. ano" value={fmt.eurC(Math.min(...rf.map(r => r.caixa_fim)))} sub="limite mínimo 500 k€" tone={Math.min(...rf.map(r => r.caixa_fim)) >= 500000 ? "pos" : "neg"} />
      </div>

      <div className="grid-2-3">
        <Panel title="Vendas mensais · 2025" sub="aplicação da sazonalidade dos mercados">
          <BarChart groups={vendasGroups} height={260} />
        </Panel>
        <Panel title="Tesouraria · saldo de caixa fim de mês" sub="limite mínimo 500 k€ · limite máximo 1,5 M€">
          <LineChart series={cashSeries} height={260} />
        </Panel>
      </div>

      <Panel title="Rolling Forecast Mensal · 2025" sub="€ · método directo · cenário ativo">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Rubrica</th>
              {rf.map(r => <th key={r.mes} className="mono num">{r.mes}</th>)}
            </tr>
          </thead>
          <tbody>
            <FRow label="Vendas" values={rf.map(r => r.vn)} />
            <FRow label="CMVMC" values={rf.map(r => -r.cmvmc)} />
            <FRow label="FSE" values={rf.map(r => -r.fse)} />
            <FRow label="Pessoal" values={rf.map(r => -r.pessoal)} />
            <tr className="is-subtotal"><td>EBITDA</td>{rf.map((r, i) => <td key={i} className="mono num">{fmt.eur(r.ebitda)}</td>)}</tr>
            <tr className="row-sep"><td colSpan={13}></td></tr>
            <FRow label="Recebimentos" values={rf.map(r => r.recebimentos)} />
            <FRow label="Pagamentos" values={rf.map(r => r.pagamentos)} />
            <FRow label="Investimento" values={rf.map(r => r.investimento)} />
            <FRow label="Financiamento" values={rf.map(r => r.financiamento)} />
            <tr className="is-total"><td>Caixa fim de mês</td>{rf.map((r, i) => <td key={i} className="mono num">{fmt.eur(r.caixa_fim)}</td>)}</tr>
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- Hub Logístico ---------------------------------------------------------
// Wrapper com 3 subtabs: Viabilidade · Monte Carlo · Plano de Financiamento OE4
// Cada subtab faz lazy-load das suas APIs e fica montada após a primeira visita.
function HubView({ ctx }) {
  const [subtab, setSubtab] = React.useState("viabilidade");
  const [seen, setSeen] = React.useState({ viabilidade: true });
  React.useEffect(() => { setSeen(s => ({ ...s, [subtab]: true })); }, [subtab]);

  const tabs = [
    { id: "viabilidade",  label: "Viabilidade" },
    { id: "monte_carlo",  label: "Monte Carlo" },
    { id: "oe4",          label: "Plano de Financiamento OE4" },
  ];

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div className="seg">
          {tabs.map(t => (
            <button
              key={t.id}
              className={"seg-btn " + (subtab === t.id ? "is-on" : "")}
              onClick={() => setSubtab(t.id)}
            >{t.label}</button>
          ))}
        </div>
      </div>
      <div style={{ display: subtab === "viabilidade" ? "contents" : "none" }}>
        {seen.viabilidade && <HubViabilidadeView ctx={ctx} />}
      </div>
      <div style={{ display: subtab === "monte_carlo" ? "contents" : "none" }}>
        {seen.monte_carlo && <HubMonteCarloView ctx={ctx} />}
      </div>
      <div style={{ display: subtab === "oe4" ? "contents" : "none" }}>
        {seen.oe4 && <HubOE4View ctx={ctx} />}
      </div>
    </>
  );
}

// Subtab Viabilidade — KPIs, FCF, Tornado, Parâmetros, DR/KPIs comparativo, Consolidado.
function HubViabilidadeView({ ctx }) {
  const [viab, setViab] = React.useState(null);
  const [torn, setTorn] = React.useState(null);
  const [comp, setComp] = React.useState(null);
  const [consol, setConsol] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      API.hubViability(),
      API.hubTornado(),
      API.hubComparativo({ cenario: ctx.scenario }),
      API.hubConsolidado({ cenario: ctx.scenario }),
    ])
      .then(([v, t, c, s]) => {
        if (cancelled) return;
        setViab(v); setTorn(t); setComp(c); setConsol(s);
        setLoading(false);
      })
      .catch(err => {
        if (cancelled) return;
        setError(err.message || String(err));
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [ctx.scenario]);

  if (loading && !viab) return <LoadingShell />;
  if (error && !viab) return <ErrorBanner message={error} onRetry={() => setError(null)} />;
  if (!viab) return null;

  const wacc = viab.parametros?.wacc || 0.08;
  const fcfSeries = [
    { labels: (viab.anos || []).map(String), values: viab.fcf || [], color: "var(--ink)" },
    { labels: (viab.anos || []).map(String), values: viab.fcf_cumulativo || [], color: "var(--accent)", fill: true },
  ];

  // Formatação do payback — aceita número ou string do backend
  function fmtPayback(v) {
    if (v == null) return "—";
    if (typeof v === "string") return v;
    return Number(v).toFixed(1) + " anos";
  }

  const p = viab.parametros || {};

  return (
    <>
      {/* ── KPIs principais ─────────────────────────────────────────────── */}
      <div className="grid-4">
        <KPI label={"VAL @ " + fmt.pct(wacc, 0)} value={fmt.eurC(viab.vpl)} tone={viab.vpl >= 0 ? "pos" : "neg"} sub={"horizonte 10 anos · VR ativos " + fmt.eurC(viab.valor_residual_ativos || 0) + " + NFM " + fmt.eurC(viab.nfm_recovery_terminal || 0)} />
        <KPI label="TIR" value={viab.tir != null ? fmt.pct(viab.tir, 1) : "—"} tone={viab.tir != null && viab.tir >= wacc ? "pos" : "neg"} sub={"vs WACC " + fmt.pct(wacc, 0)} />
        <KPI label="Payback simples" value={fmtPayback(viab.payback_simples)} sub="anos a partir de 2024" />
        <KPI label="Payback actualizado" value={fmtPayback(viab.payback_atualizado)} sub={"descontado a " + fmt.pct(wacc, 0)} />
      </div>

      {/* ── FCF ─────────────────────────────────────────────────────────── */}
      <Panel
        title="Fluxos de caixa livres · Hub Logístico 4.0 (M6)"
        sub={"CAPEX " + fmt.eurC(p.capex_base || 6000000) + " · poupança operacional " + fmt.eurC(p.poupanca_operacional || 480000) + "/ano · WACC " + fmt.pct(wacc, 0)}
      >
        <LineChart series={fcfSeries} height={280} />
        <div className="legend" style={{ marginTop: 8 }}>
          <div className="legend-row"><span className="swatch" style={{ background: "var(--ink)" }} /><span>FCF anual (FCFF)</span></div>
          <div className="legend-row"><span className="swatch" style={{ background: "var(--accent)" }} /><span>FCF acumulado</span></div>
        </div>
      </Panel>

      {/* ── Tornado + Parâmetros ──────────────────────────────────────────── */}
      <div className="grid-2">
        <Panel title="Análise de sensibilidade · Tornado" sub="impacto no VAL em M€ — 6 variáveis críticas (one-at-a-time)">
          {torn && torn.length > 0
            ? <TornadoChart rows={torn} height={320} />
            : <div className="muted" style={{ padding: 24 }}>A carregar tornado…</div>
          }
          {torn && torn.length > 0 && (
            <table className="ftable ftable--dense" style={{ marginTop: 12 }}>
              <thead>
                <tr>
                  <th>Variável</th>
                  <th className="mono num">Pessimista</th>
                  <th className="mono num">Otimista</th>
                  <th className="mono num">Swing VAL</th>
                </tr>
              </thead>
              <tbody>
                {torn.map((row, i) => {
                  const swing = typeof row.impacto_total === "number"
                    ? row.impacto_total
                    : Math.abs((row.high || 0) - (row.low || 0));
                  return (
                    <tr key={i}>
                      <td style={{ fontSize: 11 }}>{row.variavel || row.label}</td>
                      <td className="mono num neg" style={{ fontSize: 11 }}>{row.desc_low || fmt.num(row.low, 2) + " M€"}</td>
                      <td className="mono num pos" style={{ fontSize: 11 }}>{row.desc_high || fmt.num(row.high, 2) + " M€"}</td>
                      <td className="mono num" style={{ fontSize: 11, fontWeight: 600 }}>{fmt.num(swing, 2)} M€</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>
        <Panel title="Parâmetros do projeto" sub="m6_hub_assumptions.yaml">
          <dl className="kv">
            <KV k="CAPEX base" v={fmt.eurC(p.capex_base || 3800000)} />
            <KV k="Cronograma 2025" v={fmt.eurC(p.capex_2025 || 2280000)} />
            <KV k="Cronograma 2026" v={fmt.eurC(p.capex_2026 || 1520000)} />
            <KV k="WACC" v={fmt.pct(wacc, 0)} />
            <KV k="IRC taxa" v={fmt.pct(p.irc_taxa || 0.245, 1)} />
            <KV k="Crescimento terminal" v={fmt.pct(p.crescimento_terminal || 0.02, 0)} />
            <KV k="Horizonte" v={(p.horizonte_anos || 10) + " anos"} />
            <KV k="Poupança operacional" v={fmt.eurC(p.poupanca_operacional || 380000) + " / ano"} />
            <KV k="Redução quebras" v={fmt.eurC(p.reducao_quebras || 50000) + " / ano"} />
            <KV k="OPEX incremental" v={"− " + fmt.eurC(p.opex_incremental || 120000) + " / ano"} />
            <KV k="Benefício líquido base" v={fmt.eurC(p.beneficio_liquido_anual || 310000) + " / ano"} />
            <KV k="Crescimento benefícios" v={"+" + fmt.pct(p.crescimento_anual || 0.04, 0) + " / ano"} />
            <KV k="Libertação inventário 2026" v={fmt.eurC(p.libertacao_inventario || 2000000)} />
            <KV k="Banco Hub" v={fmt.eurC(p.banco_montante || 2850000) + " @ " + fmt.pct(p.banco_taxa_juro || 0.0415, 2)} />
            <KV k="PT2030" v={fmt.eurC(p.pt2030_montante || 1710000) + " · " + (p.pt2030_ano || 2027)} />
            <KV k="RFAI crédito total" v={fmt.eurC(p.rfai_credito_total_gerado || 0)} />
            <KV k="Índice rendibilidade" v={viab.indice_rendibilidade != null ? viab.indice_rendibilidade.toFixed(2) + "×" : "—"} />
          </dl>
        </Panel>
      </div>

      {/* ── DR/Balanço/DFC Comparativo sem vs com Hub ─────────────────────── */}
      {comp && (
        <Panel
          title="DR comparativo · Sem Hub vs. Com Hub"
          sub={"cenário " + (comp.cenario || ctx.scenario) + " · diferença = Com Hub − Sem Hub · em €"}
        >
          <HubComparativoDR sem={comp.sem_hub?.dr || []} com={comp.com_hub?.dr || []} />
        </Panel>
      )}

      {comp && (
        <Panel title="KPIs comparativos · Sem Hub vs. Com Hub" sub="rácios financeiros — impacto marginal do projeto">
          <HubComparativoKPIs sem={comp.sem_hub?.kpis || []} com={comp.com_hub?.kpis || []} />
        </Panel>
      )}

      {/* ── VAL/TIR/Payback Consolidados ─────────────────────────────────── */}
      {consol && (
        <Panel title="Consolidado · Hub + Ecogres + Grupo Grestel" sub="visão integrada do portfolio de investimentos">
          <HubConsolidadoView consol={consol} />
        </Panel>
      )}
    </>
  );
}

// Sub-componente: tabela DR comparativa sem vs. com Hub
function HubComparativoDR({ sem, com }) {
  const years = GRESTEL.YEARS;
  const semByYear = Object.fromEntries((sem || []).map(r => [r.year || r.ano, r]));
  const comByYear = Object.fromEntries((com || []).map(r => [r.year || r.ano, r]));

  const rows = [
    { label: "Volume de Negócios", field: "vn", bold: false },
    { label: "Outros Rendimentos", field: "outros_rend", bold: false },
    { label: "CMVMC", field: "cmvmc", sign: -1 },
    { label: "FSE", field: "fse", sign: -1 },
    { label: "Gastos Pessoal", field: "pessoal", sign: -1 },
    { label: "EBITDA", field: "ebitda", bold: true },
    { label: "Depreciações", field: "dep", sign: -1 },
    { label: "EBIT", field: "ebit", bold: true },
    { label: "Resultado Líquido", field: "rl", bold: true },
  ];

  function val(byYear, y, field) {
    const r = byYear[y];
    return r != null ? (r[field] || 0) : null;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="ftable ftable--dense">
        <thead>
          <tr>
            <th style={{ minWidth: 180 }}>Rubrica</th>
            {years.map(y => (
              <React.Fragment key={y}>
                <th className="mono num" colSpan={3} style={{ textAlign: "center", borderBottom: "1px solid var(--border)" }}>{y}</th>
              </React.Fragment>
            ))}
          </tr>
          <tr>
            <th />
            {years.map(y => (
              <React.Fragment key={y}>
                <th className="mono num" style={{ fontSize: 10, color: "var(--muted)" }}>Sem Hub</th>
                <th className="mono num" style={{ fontSize: 10, color: "var(--accent)" }}>Com Hub</th>
                <th className="mono num" style={{ fontSize: 10, color: "var(--pos)" }}>Δ</th>
              </React.Fragment>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(({ label, field, bold }) => (
            <tr key={field} className={bold ? "is-subtotal" : ""}>
              <td style={{ fontWeight: bold ? 600 : undefined }}>{label}</td>
              {years.map(y => {
                const s = val(semByYear, y, field);
                const c = val(comByYear, y, field);
                const delta = (s != null && c != null) ? c - s : null;
                return (
                  <React.Fragment key={y}>
                    <td className="mono num" style={{ fontSize: 11, color: "var(--muted)" }}>{s != null ? fmt.eur(s) : "—"}</td>
                    <td className="mono num" style={{ fontSize: 11 }}>{c != null ? fmt.eur(c) : "—"}</td>
                    <td className={"mono num " + (delta > 0 ? "pos" : delta < 0 ? "neg" : "")} style={{ fontSize: 11, fontWeight: 600 }}>
                      {delta != null ? (delta >= 0 ? "+" : "") + fmt.eur(delta) : "—"}
                    </td>
                  </React.Fragment>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Sub-componente: KPIs comparativos
function HubComparativoKPIs({ sem, com }) {
  const years = GRESTEL.YEARS;
  const semByYear = Object.fromEntries((sem || []).map(r => [r.year || r.ano, r]));
  const comByYear = Object.fromEntries((com || []).map(r => [r.year || r.ano, r]));

  const rows = [
    { label: "Margem EBITDA", field: "margem_ebitda", fmt: "pct" },
    { label: "Margem EBIT", field: "margem_ebit", fmt: "pct" },
    { label: "Margem Líquida", field: "margem_liquida", fmt: "pct" },
    { label: "ROE", field: "roe", fmt: "pct" },
    { label: "Autonomia Financeira", field: "autonomia_financeira", fmt: "pct" },
    { label: "Cobertura de Juros", field: "cobertura_juros", fmt: "x" },
  ];

  function fmtKPI(v, type) {
    if (v == null) return "—";
    if (type === "pct") return fmt.pct(v, 1);
    if (type === "x") return Number(v).toFixed(1) + "×";
    return Number(v).toFixed(2);
  }

  return (
    <table className="ftable ftable--dense">
      <thead>
        <tr>
          <th style={{ minWidth: 180 }}>KPI</th>
          {years.map(y => (
            <React.Fragment key={y}>
              <th className="mono num" colSpan={2} style={{ textAlign: "center" }}>{y}</th>
            </React.Fragment>
          ))}
        </tr>
        <tr>
          <th />
          {years.map(y => (
            <React.Fragment key={y}>
              <th className="mono num" style={{ fontSize: 10, color: "var(--muted)" }}>Sem Hub</th>
              <th className="mono num" style={{ fontSize: 10, color: "var(--accent)" }}>Com Hub</th>
            </React.Fragment>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(({ label, field, fmt: ftype }) => (
          <tr key={field}>
            <td style={{ fontSize: 11 }}>{label}</td>
            {years.map(y => {
              const s = (semByYear[y] || {})[field];
              const c = (comByYear[y] || {})[field];
              const better = c != null && s != null && c > s;
              return (
                <React.Fragment key={y}>
                  <td className="mono num" style={{ fontSize: 11, color: "var(--muted)" }}>{fmtKPI(s, ftype)}</td>
                  <td className={"mono num " + (better ? "pos" : "")} style={{ fontSize: 11, fontWeight: better ? 600 : undefined }}>{fmtKPI(c, ftype)}</td>
                </React.Fragment>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Sub-componente: visão consolidada Hub + Ecogres + Grupo
function HubConsolidadoView({ consol }) {
  const hub = consol.hub || {};
  const eco = consol.ecogres || {};
  const grupo = consol.grupo || {};
  const anos = grupo.anos || GRESTEL.YEARS.map(Number);

  const deltaEbitda = grupo.delta_ebitda_hub || [];
  const deltaRL     = grupo.delta_rl_hub     || [];

  return (
    <>
      {/* Cards sumário */}
      <div className="grid-3" style={{ marginBottom: 16 }}>
        <div>
          <div className="sub-label" style={{ marginBottom: 8, fontWeight: 600 }}>Hub Logístico 4.0</div>
          <dl className="kv">
            <KV k="VAL" v={fmt.eurC(hub.vpl)} />
            <KV k="TIR" v={hub.tir != null ? fmt.pct(hub.tir, 1) : "—"} />
            <KV k="Payback simples" v={hub.payback_simples != null ? Number(hub.payback_simples).toFixed(1) + " anos" : "—"} />
            <KV k="Payback atualizado" v={hub.payback_atualizado != null ? Number(hub.payback_atualizado).toFixed(1) + " anos" : "—"} />
            <KV k="CAPEX" v={fmt.eurC(hub.capex_base || 0)} />
            <KV k="PT2030" v={fmt.eurC(hub.pt2030_montante || 0)} />
            <KV k="WACC" v={fmt.pct(hub.wacc || 0.08, 0)} />
            <KV k="Índice rendibilidade" v={hub.indice_rendibilidade != null ? hub.indice_rendibilidade.toFixed(2) + "×" : "—"} />
          </dl>
        </div>
        <div>
          <div className="sub-label" style={{ marginBottom: 8, fontWeight: 600 }}>Ecogres · Pasta & Grés</div>
          <dl className="kv">
            <KV k="RL acumulado 2025-29" v={fmt.eurC(eco.rl_acumulado_projetado || 0)} />
            <KV k="EBITDA 2029" v={fmt.eurC(eco.ebitda_2029 || 0)} />
          </dl>
          {eco.anos && (
            <table className="ftable ftable--dense" style={{ marginTop: 8 }}>
              <thead>
                <tr>
                  <th>Ano</th>
                  <th className="mono num">EBITDA</th>
                  <th className="mono num">RL</th>
                </tr>
              </thead>
              <tbody>
                {eco.anos.slice(1).map((ano, i) => (
                  <tr key={ano}>
                    <td className="mono">{ano}</td>
                    <td className="mono num">{fmt.eur(eco.ebitda_anual?.[i + 1] || 0)}</td>
                    <td className={"mono num " + ((eco.rl_anual?.[i + 1] || 0) >= 0 ? "pos" : "neg")}>{fmt.eur(eco.rl_anual?.[i + 1] || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div>
          <div className="sub-label" style={{ marginBottom: 8, fontWeight: 600 }}>Impacto Incremental Hub no Grupo</div>
          <table className="ftable ftable--dense">
            <thead>
              <tr>
                <th>Ano</th>
                <th className="mono num">Δ EBITDA</th>
                <th className="mono num">Δ RL</th>
              </tr>
            </thead>
            <tbody>
              {anos.map((ano, i) => (
                <tr key={ano}>
                  <td className="mono">{ano}</td>
                  <td className={"mono num " + ((deltaEbitda[i] || 0) >= 0 ? "pos" : "neg")}>{fmt.eur(deltaEbitda[i] || 0)}</td>
                  <td className={"mono num " + ((deltaRL[i] || 0) >= 0 ? "pos" : "neg")}>{fmt.eur(deltaRL[i] || 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function KV({ k, v }) {
  return (
    <div className="kv-row">
      <dt>{k}</dt>
      <dd className="mono">{v}</dd>
    </div>
  );
}

// ---- Hub · Monte Carlo ------------------------------------------------------
// Simulação estocástica do VAL e TIR. Lazy-load via API.hubMonteCarlo().
function HubMonteCarloView({ ctx }) {
  const [mc, setMc] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [n, setN] = React.useState(1000);
  const [seed, setSeed] = React.useState(42);
  const [params, setParams] = React.useState({ n: 1000, seed: 42 });

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    API.hubMonteCarlo({ n: params.n, seed: params.seed })
      .then(d => { if (!cancelled) { setMc(d); setLoading(false); } })
      .catch(err => { if (!cancelled) { setError(err.message || String(err)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [params]);

  if (loading && !mc) return <LoadingShell />;
  if (error && !mc) return <ErrorBanner message={error} onRetry={() => setParams(p => ({ ...p }))} />;
  if (!mc) return null;

  const v = mc.val, t = mc.tir, base = mc.parametros_base;
  const corr = Object.entries(mc.correlacoes_val).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  const driverLabels = {
    b2c:                   "Crescimento B2C / e-commerce",
    pessoal:               "Custo de pessoal",
    inventario:            "Libertação de inventário",
    capex:                 "CAPEX total",
    wacc:                  "WACC",
    pt2030_taxa:           "Co-financiamento PT2030",
    preco_eletricidade:    "Preço da eletricidade",
    eur_usd:               "Taxa de câmbio EUR/USD",
    crescimento_logistico: "Taxa de crescimento logístico",
  };

  return (
    <>
      <Panel
        title="Parâmetros da simulação"
        sub={`última corrida: ${mc.n_simulations} simulações · IRC ${fmt.pct(mc.irc_taxa, 1)} · ${t.n_validas} TIR válidas / ${t.n_invalidas} inválidas`}
        right={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <label style={{ fontSize: 12, color: "var(--muted)", display: "inline-flex", gap: 6, alignItems: "center" }}>
              n
              <input type="number" min="100" max="5000" step="100" value={n} onChange={e => setN(+e.target.value)}
                     style={{ width: 70, padding: "3px 6px", border: "1px solid var(--rule-strong)", background: "var(--surface)", fontFamily: "var(--mono)", fontSize: 12 }} />
            </label>
            <label style={{ fontSize: 12, color: "var(--muted)", display: "inline-flex", gap: 6, alignItems: "center" }}>
              seed
              <input type="number" value={seed} onChange={e => setSeed(+e.target.value)}
                     style={{ width: 70, padding: "3px 6px", border: "1px solid var(--rule-strong)", background: "var(--surface)", fontFamily: "var(--mono)", fontSize: 12 }} />
            </label>
            <button className="btn-ghost" onClick={() => setParams({ n, seed })} disabled={loading}
                    style={{ background: "var(--ink)", color: "var(--surface)", borderColor: "var(--ink)" }}>
              {loading ? "A simular…" : "Re-executar"}
            </button>
          </div>
        }
      >
        <div className="legend" style={{ fontSize: 12 }}>
          <div className="legend-row"><span className="swatch" style={{ background: "var(--accent)" }} /><span>Distribuição estocástica · histograma sobre {mc.n_simulations} saídas</span></div>
          <div className="legend-row"><span className="swatch" style={{ background: "var(--neg)" }} /><span>VAL determinístico (hubViability) — linha tracejada</span></div>
        </div>
      </Panel>

      <div className="grid-4">
        <KPI label="VAL médio"      value={fmt.eurC(v.mean)}                       sub={"σ " + fmt.eurC(v.std) + " · base " + fmt.eurC(base.val_base)} />
        <KPI label="P(VAL > 0)"     value={fmt.pct(v.prob_positivo, 1)}            tone="pos" sub="probabilidade de criação de valor" />
        <KPI label="TIR média"      value={fmt.pct(t.mean, 1)}                     sub={"σ " + fmt.pct(t.std, 1) + " · base " + fmt.pct(base.tir_base, 1)} />
        <KPI label="P(TIR > WACC)"  value={fmt.pct(t.prob_supera_wacc_base, 1)}   tone="pos" sub={"WACC base " + fmt.pct(base.wacc_base, 0)} />
      </div>

      <div className="grid-2-3">
        <Panel
          title="Distribuição estocástica do VAL"
          sub={`${mc.n_simulations} simulações · linha tracejada vermelha = VAL determinístico (${fmt.eurC(base.val_base)})`}
        >
          <HistogramChart
            bins={v.histogram.bins}
            counts={v.histogram.counts}
            edges={v.histogram.edges}
            baselineMark={base.val_base}
            baselineLabel={"VAL base · " + fmt.eurC(base.val_base)}
            percentiles={[
              { p: "P5",  value: v.p5  },
              { p: "P50", value: v.p50 },
              { p: "P95", value: v.p95 },
            ]}
            height={300}
          />
        </Panel>
        <Panel title="Percentis" sub="VAL e TIR · 7 pontos">
          <table className="ftable ftable--dense">
            <thead>
              <tr><th>Percentil</th><th className="mono num">VAL</th><th className="mono num">TIR</th></tr>
            </thead>
            <tbody>
              {["p5", "p10", "p25", "p50", "p75", "p90", "p95"].map(k => (
                <tr key={k} className={k === "p50" ? "is-subtotal" : ""}>
                  <td>{k.toUpperCase()}</td>
                  <td className="mono num">{fmt.eurC(v[k])}</td>
                  <td className="mono num">{fmt.pct(t[k], 1)}</td>
                </tr>
              ))}
              <tr>
                <td className="muted">mín / máx</td>
                <td className="mono num muted" colSpan={2}>{fmt.eurC(v.min)} — {fmt.eurC(v.max)}</td>
              </tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <Panel
        title="Correlação driver → VAL"
        sub="Pearson r · magnitude indica importância do risco, sinal indica direção"
        right={
          <Legend items={[
            { label: "correlação positiva", color: "var(--pos)" },
            { label: "correlação negativa", color: "var(--neg)" },
          ]} />
        }
      >
        <HBarChart items={corr.map(([k, val]) => ({ label: driverLabels[k] || k, value: val }))} />
      </Panel>

      <Panel title="Distribuições amostradas" sub="parâmetros usados pelo Monte Carlo para cada driver">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Driver</th>
              <th>Tipo</th>
              <th className="mono num">Mín</th>
              <th className="mono num">Modo / Média</th>
              <th className="mono num">Máx</th>
              <th>Unidade</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(mc.distribuicoes_usadas).map(([k, d]) => {
              const isPct  = (k === "wacc" || k === "pt2030_taxa" || k === "crescimento_logistico");
              const isMult = (k === "b2c");
              const isKwh  = (k === "preco_eletricidade");
              const isFx   = (k === "eur_usd");
              const f = isPct  ? (val => fmt.pct(val, 1))
                      : isMult ? (val => val.toFixed(2) + "×")
                      : isKwh  ? (val => val.toFixed(3) + " €/kWh")
                      : isFx   ? (val => val.toFixed(3))
                               : fmt.eurC;
              const unidade = isPct ? "taxa" : isMult ? "× base" : isKwh ? "€/kWh" : isFx ? "EUR/USD" : "EUR";
              return (
                <tr key={k}>
                  <td>{driverLabels[k] || k}</td>
                  <td><span className="chip-static" style={{ padding: "2px 8px", fontSize: 10.5 }}>{d.type}</span></td>
                  <td className="mono num">{d.type === "truncnorm" ? f(d.low)  : f(d.min)}</td>
                  <td className="mono num">{d.type === "truncnorm" ? f(d.mean) : f(d.mode)}</td>
                  <td className="mono num">{d.type === "truncnorm" ? f(d.high) : f(d.max)}</td>
                  <td className="muted">{unidade}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- Hub · Plano de Financiamento OE4 ---------------------------------------
// Consome API.hubDebtService() + API.hubInvestmentMap() em paralelo.
function HubOE4View({ ctx }) {
  const [ds, setDs] = React.useState(null);
  const [im, setIm] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([API.hubDebtService(), API.hubInvestmentMap()])
      .then(([d, m]) => { if (!cancelled) { setDs(d); setIm(m); setLoading(false); } })
      .catch(err => { if (!cancelled) { setError(err.message || String(err)); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  if (loading && !ds) return <LoadingShell />;
  if (error && !ds) return <ErrorBanner message={error} onRetry={() => setError(null)} />;
  if (!ds || !im) return null;

  const totalCapex  = im.capex_base;
  const emprestimo  = im.financiamento?.Banco_Hub?.montante  || 2_850_000;
  const pt2030      = im.pt2030_montante;
  const capProprio  = 240_000;
  const fundingTotal = emprestimo + pt2030 + capProprio;
  const nfmTotal    = im.nfm.reduce((a, r) => a + r.delta_nfm, 0);
  const dscrMin     = 1.20;

  const poolColors = [
    "oklch(0.34 0.075 40)", "oklch(0.44 0.105 45)", "oklch(0.54 0.115 45)",
    "oklch(0.66 0.105 55)", "oklch(0.78 0.060 75)",
  ];

  const capexByYear = im.capex_anual.map(({ ano, capex }) => {
    const poolsAno = im.pools.filter(p => p.ano_inicio === ano);
    return { ano, capex, parts: poolsAno.map(p => {
      const i = im.pools.findIndex(x => x.pool === p.pool);
      return { label: p.pool.replace(/_/g, " "), value: p.montante, amount: p.montante, color: poolColors[i % poolColors.length], textColor: i < 2 ? "var(--surface)" : "var(--ink)" };
    }) };
  });

  function dscrChip(r) {
    if (r.periodo_carencia) {
      return <span className="chip-static" style={{ background: "oklch(0.95 0.05 80)", borderColor: "transparent", color: "oklch(0.45 0.10 70)", padding: "2px 8px", fontSize: 10.5 }}>Carência</span>;
    }
    if (r.dscr_hub >= dscrMin) {
      return <span className="chip-static" style={{ background: "var(--pos-soft)", borderColor: "transparent", color: "var(--pos)", padding: "2px 8px", fontSize: 10.5 }}>OK</span>;
    }
    if (r.dscr_hub > 0) {
      return <span className="chip-static" style={{ background: "var(--neg-soft)", borderColor: "transparent", color: "var(--neg)", padding: "2px 8px", fontSize: 10.5 }}>Stress</span>;
    }
    return <span className="muted">—</span>;
  }

  const dscrPostCar = ds.rows.filter(r => !r.periodo_carencia).map(r => r.dscr_hub);
  const dscrMinObs  = dscrPostCar.length ? Math.min(...dscrPostCar) : null;

  return (
    <>
      <div className="grid-4">
        <KPI label="CAPEX total"         value={fmt.eurC(totalCapex)} sub={"2025 " + fmt.eurC(2_280_000) + " · 2026 " + fmt.eurC(1_520_000)} />
        <KPI label="Empréstimo bancário" value={fmt.eurC(emprestimo)} sub="CGD/BPI · 4,15 % · carência 2025–27" />
        <KPI label="Subsídio PT2030"     value={fmt.eurC(pt2030)} tone="pos" sub={"fundo perdido · 45 % CAPEX · " + im.pt2030_ano} />
        <KPI label="Capital próprio"     value={fmt.eurC(capProprio)} sub={"+ NFM acumulada " + fmt.eurC(nfmTotal)} />
      </div>

      <Panel
        title="Mapa de Investimento"
        sub="5 pools de CAPEX · vidas úteis e taxas de depreciação distintas"
        right={<span className="chip-static mono">Σ {fmt.eurC(totalCapex)}</span>}
      >
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Pool</th>
              <th>Descrição</th>
              <th className="mono num">Montante</th>
              <th className="mono num">% CAPEX</th>
              <th className="mono num">Início</th>
              <th className="mono num">Vida útil</th>
              <th className="mono num">Taxa dep.</th>
            </tr>
          </thead>
          <tbody>
            {im.pools.map((p, i) => (
              <tr key={p.pool}>
                <td>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                    <span className="swatch" style={{ background: poolColors[i % poolColors.length] }} />
                    <b style={{ fontWeight: 500 }}>{p.pool.replace(/_/g, " ")}</b>
                  </span>
                </td>
                <td style={{ color: "var(--ink-2)", fontSize: 11.5 }}>{p.descricao}</td>
                <td className="mono num">{fmt.eur(p.montante)}</td>
                <td className="mono num muted">{fmt.pct(p.montante / totalCapex, 1)}</td>
                <td className="mono num">{p.ano_inicio}</td>
                <td className="mono num">{p.vida_util_anos} anos</td>
                <td className="mono num">{fmt.pct(p.taxa_depreciacao, 1)}</td>
              </tr>
            ))}
            <tr className="is-total">
              <td>Total</td><td></td>
              <td className="mono num">{fmt.eur(totalCapex)}</td>
              <td className="mono num">100,0 %</td>
              <td colSpan={3}></td>
            </tr>
          </tbody>
        </table>

        <div className="sub-section">
          <div className="sub-label">CAPEX por ano e pool</div>
          {capexByYear.map(y => (
            <div key={y.ano} style={{ display: "grid", gridTemplateColumns: "56px 1fr 110px", alignItems: "center", gap: 12, marginBottom: 8 }}>
              <div className="mono" style={{ fontWeight: 500 }}>{y.ano}</div>
              <StackedBar items={y.parts} height={28} showLabels={false} />
              <div className="mono num" style={{ textAlign: "right" }}>{fmt.eurC(y.parts.reduce((a, p) => a + p.value, 0))}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Estrutura de Financiamento" sub="empréstimo + subsídio + capital próprio · cobertura do CAPEX">
        <StackedBar
          items={[
            { label: "Empréstimo bancário", value: emprestimo / fundingTotal, amount: emprestimo, color: "oklch(0.34 0.075 40)", textColor: "var(--surface)" },
            { label: "Subsídio PT2030",     value: pt2030    / fundingTotal, amount: pt2030,     color: "oklch(0.54 0.115 45)", textColor: "var(--surface)" },
            { label: "Capital próprio",     value: capProprio/ fundingTotal, amount: capProprio, color: "oklch(0.78 0.060 75)", textColor: "var(--ink)" },
          ]}
          height={40}
        />
        <div className="grid-3" style={{ marginTop: 14 }}>
          <FundingCard
            label="Empréstimo bancário (CGD/BPI)"
            value={fmt.eur(emprestimo)}
            pct={emprestimo / fundingTotal}
            color="oklch(0.34 0.075 40)"
            meta={[
              ["Desembolso", "2025"],
              ["Taxa", "4,15 % a.a."],
              ["Carência", "2025–2027 (só juros)"],
              ["Amortização", fmt.eur(285_000) + " / ano (2028+)"],
              ["Juros 2025 capitalizados", fmt.eur(118_275) + " (NCRF 10)"],
            ]}
          />
          <FundingCard
            label="Subsídio PT2030"
            value={fmt.eur(pt2030)}
            pct={pt2030 / fundingTotal}
            color="oklch(0.54 0.115 45)"
            meta={[
              ["Natureza", "Fundo perdido"],
              ["Cobertura", "45 % do CAPEX"],
              ["Recebimento", im.pt2030_ano + " (após investimento)"],
              ["Reconhecimento", "Linear · alinhado com pools"],
            ]}
          />
          <FundingCard
            label="Capital próprio (Grestel)"
            value={fmt.eur(capProprio)}
            pct={capProprio / fundingTotal}
            color="oklch(0.78 0.060 75)"
            meta={[
              ["Origem", "Cash-flow operacional Grestel"],
              ["Aplicação", "Margem de contingência"],
              ["NFM acumulada (2026–29)", fmt.eur(nfmTotal)],
              ["RFAI gerado", fmt.eur(380_000) + " (CFI art. 22-23)"],
            ]}
          />
        </div>
      </Panel>

      <Panel
        title="Mapa de Serviço da Dívida"
        sub={"calendário de juros, amortização e DSCR · covenant alvo DSCR ≥ " + dscrMin.toFixed(2).replace(".", ",") + "×"}
        right={
          <div className="legend" style={{ fontSize: 11 }}>
            <span className="chip-static" style={{ background: "oklch(0.95 0.05 80)", borderColor: "transparent", color: "oklch(0.45 0.10 70)", padding: "2px 8px", fontSize: 10.5 }}>Carência</span>
            <span className="chip-static" style={{ background: "var(--pos-soft)", borderColor: "transparent", color: "var(--pos)", padding: "2px 8px", fontSize: 10.5 }}>DSCR ≥ 1,20×</span>
            <span className="chip-static" style={{ background: "var(--neg-soft)", borderColor: "transparent", color: "var(--neg)", padding: "2px 8px", fontSize: 10.5 }}>DSCR &lt; 1,20×</span>
          </div>
        }
      >
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Ano</th>
              <th className="mono num">Saldo início</th>
              <th className="mono num">Juros pagos</th>
              <th className="mono num">Capitalizados</th>
              <th className="mono num">Em DR</th>
              <th className="mono num">Amortização</th>
              <th className="mono num">Serviço total</th>
              <th className="mono num">EBITDA Hub</th>
              <th className="mono num">DSCR</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {ds.rows.map(r => {
              const isCar   = r.periodo_carencia;
              const dscrBad = !isCar && r.dscr_hub > 0 && r.dscr_hub < dscrMin;
              return (
                <tr key={r.ano}>
                  <td className="mono"><b style={{ fontWeight: 500 }}>{r.ano}</b></td>
                  <td className="mono num">{fmt.eur(r.saldo_em_divida)}</td>
                  <td className="mono num">{fmt.eur(r.juros_pagos_total)}</td>
                  <td className="mono num muted">{r.juros_capitalizados > 0 ? fmt.eur(r.juros_capitalizados) : "—"}</td>
                  <td className="mono num">{r.juros_expensed_dr > 0 ? fmt.eur(r.juros_expensed_dr) : "—"}</td>
                  <td className="mono num">{r.amortizacao_capital > 0 ? fmt.eur(r.amortizacao_capital) : "—"}</td>
                  <td className="mono num" style={{ fontWeight: 500 }}>{fmt.eur(r.servico_total_divida)}</td>
                  <td className="mono num">{r.ebitda_hub_incremental > 0 ? fmt.eur(r.ebitda_hub_incremental) : "—"}</td>
                  <td className={"mono num " + (dscrBad ? "neg" : (!isCar && r.dscr_hub >= dscrMin ? "pos" : ""))} style={{ fontWeight: 600 }}>
                    {r.dscr_hub > 0 ? r.dscr_hub.toFixed(2).replace(".", ",") + "×" : <span className="muted">n/a</span>}
                  </td>
                  <td>{dscrChip(r)}</td>
                </tr>
              );
            })}
            <tr className="is-total">
              <td>Acumulado</td><td></td>
              <td className="mono num">{fmt.eur(ds.rows.reduce((a, r) => a + r.juros_pagos_total, 0))}</td>
              <td className="mono num">{fmt.eur(ds.rows.reduce((a, r) => a + r.juros_capitalizados, 0))}</td>
              <td className="mono num">{fmt.eur(ds.rows.reduce((a, r) => a + r.juros_expensed_dr, 0))}</td>
              <td className="mono num">{fmt.eur(ds.rows.reduce((a, r) => a + r.amortizacao_capital, 0))}</td>
              <td className="mono num">{fmt.eur(ds.rows.reduce((a, r) => a + r.servico_total_divida, 0))}</td>
              <td colSpan={3}></td>
            </tr>
          </tbody>
        </table>

        <div className="sub-section">
          <div className="sub-label">Saldo em dívida e amortização anual</div>
          <BarChart
            groups={ds.rows.map(r => ({
              label: String(r.ano),
              bars: [
                { key: "Saldo (fim)",        value: r.saldo_fim,           color: "oklch(0.34 0.075 40)" },
                { key: "Amortização anual",  value: r.amortizacao_capital, color: "oklch(0.66 0.105 55)" },
              ],
            }))}
            height={220}
          />
          <div className="legend" style={{ marginTop: 8 }}>
            <div className="legend-row"><span className="swatch" style={{ background: "oklch(0.34 0.075 40)" }} /><span>Saldo em dívida (fim do ano)</span></div>
            <div className="legend-row"><span className="swatch" style={{ background: "oklch(0.66 0.105 55)" }} /><span>Amortização anual</span></div>
          </div>
        </div>
      </Panel>

      <div className="grid-2">
        <Panel title="NFM · Necessidades de Fundo de Maneio" sub={"acumulado · " + fmt.eur(nfmTotal)}>
          <table className="ftable ftable--dense">
            <thead><tr><th>Ano</th><th className="mono num">Δ NFM</th><th>Comentário</th></tr></thead>
            <tbody>
              {im.nfm.map(r => (
                <tr key={r.ano}>
                  <td className="mono"><b style={{ fontWeight: 500 }}>{r.ano}</b></td>
                  <td className="mono num">{r.delta_nfm > 0 ? fmt.eur(r.delta_nfm) : <span className="muted">—</span>}</td>
                  <td className="muted">{
                    r.ano === 2025 ? "Pré-operação" :
                    r.ano === 2026 ? "Arranque operacional" :
                    r.ano === 2027 ? "Estabilização" :
                                     "Serviços logísticos externos"
                  }</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel title="Compatibilidade com covenants" sub="stress-test do DSCR vs covenant bancário típico">
          <dl className="kv">
            <KV k="DSCR mínimo alvo (covenant)" v={dscrMin.toFixed(2).replace(".", ",") + "×"} />
            <KV k="DSCR mínimo observado (pós-carência)" v={dscrMinObs != null ? dscrMinObs.toFixed(2).replace(".", ",") + "×" : "—"} />
            <KV k="Margem sobre covenant" v={dscrMinObs != null ? "+" + ((dscrMinObs / dscrMin - 1) * 100).toFixed(0) + " %" : "—"} />
            <KV k="EBITDA Hub 2029" v={fmt.eur(ds.rows[ds.rows.length - 1].ebitda_hub_incremental)} />
            <KV k="Serviço dívida 2029" v={fmt.eur(ds.rows[ds.rows.length - 1].servico_total_divida)} />
            <KV k="Headroom EBITDA · 2029" v={fmt.eur(ds.rows[ds.rows.length - 1].ebitda_hub_incremental - ds.rows[ds.rows.length - 1].servico_total_divida * dscrMin)} />
          </dl>
          <div style={{ marginTop: 10, fontSize: 11.5, color: "var(--ink-2)", lineHeight: 1.55 }}>
            No primeiro ano sem carência ({ds.rows.find(r => !r.periodo_carencia && r.dscr_hub > 0)?.ano}), o EBITDA incremental do Hub cobre o serviço da dívida com margem confortável acima do covenant tipicamente exigido por CGD/BPI em project finance (DSCR ≥ 1,20×).
          </div>
        </Panel>
      </div>
    </>
  );
}

function FundingCard({ label, value, pct, color, meta }) {
  return (
    <div className="panel" style={{ background: "var(--surface)" }}>
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--rule)" }}>
        <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em", display: "flex", alignItems: "center", gap: 6, fontWeight: 500 }}>
          <span className="swatch" style={{ background: color }} />
          {label}
        </div>
        <div className="mono" style={{ fontSize: 22, fontWeight: 500, marginTop: 6, letterSpacing: "-0.01em" }}>{value}</div>
        <div className="muted mono" style={{ fontSize: 11, marginTop: 2 }}>{fmt.pct(pct, 1)} do funding</div>
      </div>
      <div style={{ padding: "8px 14px 12px" }}>
        <dl className="kv">
          {meta.map(([k, v]) => <KV key={k} k={k} v={v} />)}
        </dl>
      </div>
    </div>
  );
}

// ---- Ecogres ---------------------------------------------------------------
function EcogresView({ ctx }) {
  const eco = useMemo(() => GRESTEL.projectEcogres(ctx.hubOn), [ctx.hubOn]);
  const lines = [
    { labels: eco.map(r => String(r.year)), values: eco.map(r => r.rec_total), color: "var(--ink)" },
    { labels: eco.map(r => String(r.year)), values: eco.map(r => r.ebitda), color: "var(--accent)", fill: true },
    { labels: eco.map(r => String(r.year)), values: eco.map(r => r.rl), color: "var(--pos)" },
  ];

  return (
    <>
      <div className="grid-3">
        <KPI label="Receitas 2025" value={fmt.eurC(eco[1].rec_total)} sub="subcontratação + cedência" />
        <KPI label="EBITDA 2029" value={fmt.eurC(eco[5].ebitda)} tone={eco[5].ebitda >= 0 ? "pos" : "neg"} />
        <KPI label="RL acumulado 2025-29" value={fmt.eurC(eco.slice(1).reduce((a, r) => a + r.rl, 0))} />
      </div>

      <Panel
        title="Ecogres · subsidiária · Demonstração de Resultados"
        sub="modelo independente · IRC 21%"
        right={<Legend items={[{ label: "Receitas", color: "var(--ink)" }, { label: "EBITDA", color: "var(--accent)" }, { label: "RL", color: "var(--pos)" }]} />}
      >
        <LineChart series={lines} height={280} />
      </Panel>

      <Panel title="Detalhe anual" sub="€ · valores anuais">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Rubrica</th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
            </tr>
          </thead>
          <tbody>
            <FRow label="Vendas a Terceiros (externas)" values={eco.map(r => r.vendas_externas)} />
            <FRow label="Subcontratação Grestel" values={eco.map(r => r.subc)} />
            <FRow label="Cedência de Pessoal" values={eco.map(r => r.ced)} />
            {ctx.hubOn && <FRow label="Transferência Hub" values={eco.map(r => r.transfer_hub)} />}
            <tr className="is-subtotal"><td>Receita Total</td>{eco.map((r, i) => <td key={i} className="mono num">{fmt.eur(r.rec_total)}</td>)}</tr>
            <FRow label="Custos Operacionais" values={eco.map(r => -r.custos_op)} />
            <tr className="is-subtotal"><td>EBITDA</td>{eco.map((r, i) => <td key={i} className="mono num">{fmt.eur(r.ebitda)}</td>)}</tr>
            <FRow label="Depreciações" values={eco.map(r => -r.dep)} />
            <tr className="is-subtotal"><td>EBIT</td>{eco.map((r, i) => <td key={i} className="mono num">{fmt.eur(r.ebit)}</td>)}</tr>
            <FRow label="IRC (21%)" values={eco.map(r => -r.irc)} />
            <tr className="is-total"><td>Resultado Líquido</td>{eco.map((r, i) => <td key={i} className="mono num">{fmt.eur(r.rl)}</td>)}</tr>
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- Análise de Vendas -----------------------------------------------------
function VendasView({ ctx }) {
  const [va, setVa] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    API.vendasAnalise({ cenario: ctx.scenario, hub_on: ctx.hubOn, ecogres_on: ctx.ecogresOn })
      .then(data => { if (!cancelled) { setVa(data); setLoading(false); } })
      .catch(err => { if (!cancelled) { setError(err.message || String(err)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [ctx.scenario, ctx.hubOn, ctx.ecogresOn]);

  if (loading && !va) return <LoadingShell />;
  if (error && !va) return <ErrorBanner message={error} onRetry={() => setVa(null)} />;
  if (!va) return null;

  const { full, annual, meses, familiasProd, mercadorias, totais_2025, mercados_2025, canais_2025 } = va;

  const a24 = annual.find(a => a.year === 2024);
  const a25 = annual.find(a => a.year === 2025);
  const a29 = annual.find(a => a.year === 2029);
  const cagr_25_29 = Math.pow(a29.vn / a25.vn, 1 / 4) - 1;

  // Annual stacked bar — produtos / mercadorias (hist 2020-2024 + proj 2025-2029)
  const annualGroups = full.map(r => ({
    label: String(r.year),
    bars: [
      { key: "Produtos",    value: r.produtos,    color: MIX_PALETTE_4[1] },
      { key: "Mercadorias", value: r.mercadorias, color: MIX_PALETTE_4[3] },
    ],
  }));

  // Monthly stacked bar — 2025
  const monthlyGroups = meses.map(m => ({
    label: m.mes,
    bars: [
      { key: "Produtos",    value: m.produtos,    color: MIX_PALETTE_4[1] },
      { key: "Mercadorias", value: m.mercadorias, color: MIX_PALETTE_4[3] },
    ],
  }));

  // Famílias produto donut
  const famDonut = familiasProd.map((f, i) => ({
    label: f.fam, value: f.receita, color: MIX_PALETTE_7[i],
  }));
  const mercDonut = mercadorias.map((m, i) => ({
    label: m.item, value: m.receita, color: MIX_PALETTE_7[i],
  }));

  const mercItems = Object.entries(mercados_2025).map(([k, v], i) => ({
    label: v.label,
    value: v.peso,
    amount: totais_2025.total * v.peso,
    color: MIX_PALETTE_4[i],
    textColor: MIX_PALETTE_4_TEXT[i],
  }));
  const canalItems = Object.entries(canais_2025).map(([k, v], i) => ({
    label: k.replace(/_/g, " "),
    value: v,
    amount: totais_2025.total * v,
    color: MIX_PALETTE_4[i],
    textColor: MIX_PALETTE_4_TEXT[i],
  }));

  // Monthly cumulative line
  let cum = 0;
  const cumSeries = [{
    labels: meses.map(m => m.mes),
    values: meses.map(m => { cum += m.total; return cum; }),
    color: "var(--accent)", fill: true,
  }];

  return (
    <>
      <div className="grid-kpis">
        <KPI
          label="VN 2025"
          value={fmt.eurC(a25.vn)}
          trend={(a25.vn - a24.vn) / a24.vn}
          sub="vs 2024 auditado"
          spark={annual.map(a => a.vn)}
          sparkColor="var(--ink)"
        />
        <KPI
          label="Produtos 2025"
          value={fmt.eurC(totais_2025.produtos)}
          sub={fmt.pct(totais_2025.produtos / totais_2025.total, 0) + " do VN"}
          spark={annual.map(a => a.produtos)}
          sparkColor="var(--accent)"
        />
        <KPI
          label="Mercadorias 2025"
          value={fmt.eurC(totais_2025.mercadorias)}
          sub={fmt.pct(totais_2025.mercadorias / totais_2025.total, 0) + " do VN"}
          spark={annual.map(a => a.mercadorias)}
          sparkColor="var(--pos)"
        />
        <KPI
          label="CAGR 2025-29"
          value={fmt.pctSigned(cagr_25_29)}
          sub={"cenário " + ctx.scenario}
        />
        <KPI
          label="Pico mensal · 2025"
          value={fmt.eurC(Math.max(...meses.map(m => m.total)))}
          sub={"Mês " + meses[meses.map(m => m.total).indexOf(Math.max(...meses.map(m => m.total)))].mes}
        />
        <KPI
          label="Mês mais fraco · 2025"
          value={fmt.eurC(Math.min(...meses.map(m => m.total)))}
          sub={"Mês " + meses[meses.map(m => m.total).indexOf(Math.min(...meses.map(m => m.total)))].mes}
        />
      </div>

      <Panel
        title="Vendas anuais · Produtos vs Mercadorias"
        sub="histórico 2020-2024 (auditado) + projeção 2025-2029 · cenário ativo"
        right={
          <Legend items={[
            { label: "Produtos",    color: MIX_PALETTE_4[1] },
            { label: "Mercadorias", color: MIX_PALETTE_4[3] },
          ]} />
        }
      >
        <BarChart groups={annualGroups} stacked height={280} />
      </Panel>

      <div className="grid-2-3">
        <Panel
          title="Vendas mensais · 2025"
          sub="aplicação da sazonalidade dos mercados · stack Produtos + Mercadorias"
          right={
            <Legend items={[
              { label: "Produtos",    color: MIX_PALETTE_4[1] },
              { label: "Mercadorias", color: MIX_PALETTE_4[3] },
            ]} />
          }
        >
          <BarChart groups={monthlyGroups} stacked height={280} />
        </Panel>
        <Panel title="Acumulado de VN · 2025" sub="€ · ritmo de execução mensal">
          <LineChart series={cumSeries} height={280} />
        </Panel>
      </div>

      <Panel title="Detalhe mensal · 2025" sub="€ · cenário ativo">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Rubrica</th>
              {meses.map(m => <th key={m.mes} className="mono num">{m.mes}</th>)}
              <th className="mono num">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Produtos</td>
              {meses.map((m, i) => <td key={i} className="mono num">{fmt.eur(m.produtos)}</td>)}
              <td className="mono num">{fmt.eur(meses.reduce((a, m) => a + m.produtos, 0))}</td>
            </tr>
            <tr>
              <td>Mercadorias</td>
              {meses.map((m, i) => <td key={i} className="mono num">{fmt.eur(m.mercadorias)}</td>)}
              <td className="mono num">{fmt.eur(meses.reduce((a, m) => a + m.mercadorias, 0))}</td>
            </tr>
            <tr className="is-total">
              <td>Vendas totais</td>
              {meses.map((m, i) => <td key={i} className="mono num">{fmt.eur(m.total)}</td>)}
              <td className="mono num">{fmt.eur(meses.reduce((a, m) => a + m.total, 0))}</td>
            </tr>
            <tr className="row-sep"><td colSpan={14}></td></tr>
            <tr>
              <td className="muted">% do ano</td>
              {meses.map((m, i) => (
                <td key={i} className="mono num muted">
                  {fmt.pct(m.total / meses.reduce((a, x) => a + x.total, 0), 1)}
                </td>
              ))}
              <td className="mono num muted">100,0%</td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <div className="grid-2">
        <Panel title="Mix 2025 · mercados" sub="peso geográfico — share do VN total">
          <div className="donut-row">
            <Donut
              items={Object.entries(mercados_2025).map(([k, v], i) => ({
                label: v.label, value: totais_2025.total * v.peso, color: MIX_PALETTE_4[i],
              }))}
              size={172} thickness={26}
            />
            <div className="legend-col">
              {mercItems.map((it, i) => (
                <div key={i} className="legend-row">
                  <span className="swatch" style={{ background: it.color }} />
                  <span className="legend-label">{it.label}</span>
                  <span className="legend-value mono">{fmt.eurC(it.amount)}</span>
                  <span className="legend-value mono" style={{ minWidth: 48, textAlign: "right" }}>
                    {fmt.pct(it.value, 0)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
        <Panel title="Mix 2025 · canais comerciais" sub="share do VN total">
          <StackedBar items={canalItems} height={34} />
          <div className="legend-col" style={{ marginTop: 14 }}>
            {canalItems.map((it, i) => (
              <div key={i} className="legend-row">
                <span className="swatch" style={{ background: it.color }} />
                <span className="legend-label">{it.label}</span>
                <span className="legend-value mono">{fmt.eurC(it.amount)}</span>
                <span className="legend-value mono" style={{ minWidth: 48, textAlign: "right" }}>
                  {fmt.pct(it.value, 0)}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid-2">
        <Panel title="Mix 2025 · famílias de produtos" sub="share do VN de Produtos">
          <div className="donut-row">
            <Donut items={famDonut} size={172} thickness={26} />
            <div className="legend-col">
              {familiasProd.map((f, i) => (
                <div key={i} className="legend-row">
                  <span className="swatch" style={{ background: MIX_PALETTE_7[i] }} />
                  <span className="legend-label">{f.fam}</span>
                  <span className="legend-value mono">{fmt.pct(f.peso, 0)}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
        <Panel title="Mix 2025 · mercadorias" sub="share do VN de Mercadorias">
          <div className="donut-row">
            <Donut items={mercDonut} size={172} thickness={26} />
            <div className="legend-col">
              {mercadorias.map((m, i) => (
                <div key={i} className="legend-row">
                  <span className="swatch" style={{ background: MIX_PALETTE_7[i] }} />
                  <span className="legend-label">{m.item}</span>
                  <span className="legend-value mono">{fmt.pct(m.peso, 0)}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="PVU 2025 · Produtos" sub="Preço de Venda Unitário · receita / unidades vendidas">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Família</th>
              <th className="num">Receita 2025</th>
              <th className="num">% do total</th>
              <th className="num">Unidades</th>
              <th className="num">PVU 2024</th>
              <th className="num">PVU 2025</th>
              <th className="num">Δ PVU</th>
            </tr>
          </thead>
          <tbody>
            {familiasProd.map((f, i) => (
              <tr key={f.fam}>
                <td>
                  <span className="swatch" style={{ background: MIX_PALETTE_7[i], marginRight: 8, verticalAlign: "middle" }} />
                  {f.fam}
                </td>
                <td className="mono num">{fmt.eur(f.receita)}</td>
                <td className="mono num">{fmt.pct(f.peso, 1)}</td>
                <td className="mono num">{fmt.num(f.unidades)}</td>
                <td className="mono num">€{f.pvu_2024.toFixed(2).replace(".", ",")}</td>
                <td className="mono num">€{f.pvu_25.toFixed(2).replace(".", ",")}</td>
                <td className={"mono num " + (f.delta_pvu >= 0 ? "pos" : "neg")}>{fmt.pctSigned(f.delta_pvu)}</td>
              </tr>
            ))}
            <tr className="is-total">
              <td>Total Produtos</td>
              <td className="mono num">{fmt.eur(totais_2025.produtos)}</td>
              <td className="mono num">100,0%</td>
              <td className="mono num">{fmt.num(familiasProd.reduce((a, f) => a + f.unidades, 0))}</td>
              <td className="mono num muted">—</td>
              <td className="mono num">
                €{(totais_2025.produtos / familiasProd.reduce((a, f) => a + f.unidades, 0)).toFixed(2).replace(".", ",")}
              </td>
              <td className="mono num muted">—</td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel title="PVU 2025 · Mercadorias" sub="Preço de Venda Unitário · receita / unidades vendidas">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Mercadoria</th>
              <th className="num">Receita 2025</th>
              <th className="num">% do total</th>
              <th className="num">Unidades</th>
              <th className="num">PVU 2024</th>
              <th className="num">PVU 2025</th>
              <th className="num">Δ PVU</th>
            </tr>
          </thead>
          <tbody>
            {mercadorias.map((m, i) => (
              <tr key={m.item}>
                <td>
                  <span className="swatch" style={{ background: MIX_PALETTE_7[i], marginRight: 8, verticalAlign: "middle" }} />
                  {m.item}
                </td>
                <td className="mono num">{fmt.eur(m.receita)}</td>
                <td className="mono num">{fmt.pct(m.peso, 1)}</td>
                <td className="mono num">{fmt.num(m.unidades)}</td>
                <td className="mono num">€{m.pvu_2024.toFixed(2).replace(".", ",")}</td>
                <td className="mono num">€{m.pvu_25.toFixed(2).replace(".", ",")}</td>
                <td className={"mono num " + (m.delta_pvu >= 0 ? "pos" : "neg")}>{fmt.pctSigned(m.delta_pvu)}</td>
              </tr>
            ))}
            <tr className="is-total">
              <td>Total Mercadorias</td>
              <td className="mono num">{fmt.eur(totais_2025.mercadorias)}</td>
              <td className="mono num">100,0%</td>
              <td className="mono num">{fmt.num(mercadorias.reduce((a, m) => a + m.unidades, 0))}</td>
              <td className="mono num muted">—</td>
              <td className="mono num">
                €{(totais_2025.mercadorias / mercadorias.reduce((a, m) => a + m.unidades, 0)).toFixed(2).replace(".", ",")}
              </td>
              <td className="mono num muted">—</td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ---- Pressupostos ----------------------------------------------------------
function PressupostosView({ ctx }) {
  const sc = GRESTEL.SCENARIOS;
  return (
    <>
      <Panel title="Cenários · drivers de crescimento" sub="taxas anuais aplicadas a cada rubrica (custom_scenarios.yaml)">
        <table className="ftable">
          <thead>
            <tr>
              <th>Cenário</th>
              <th>Driver</th>
              {GRESTEL.YEARS.slice(1).map(y => <th key={y} className="mono num">{y}</th>)}
            </tr>
          </thead>
          <tbody>
            {Object.entries(sc).map(([k, s]) => (
              <React.Fragment key={k}>
                <tr className="is-section"><td colSpan={GRESTEL.YEARS.length}><strong>{s.label}</strong> — <span className="muted">{s.desc}</span></td></tr>
                {[
                  { key: "vol", label: "Volume" },
                  { key: "preco", label: "Preço" },
                  { key: "fse", label: "FSE" },
                  { key: "pessoal", label: "Pessoal" },
                  { key: "cmvmc", label: "CMVMC" },
                ].map(d => (
                  <tr key={k + d.key} className={k === ctx.scenario ? "is-highlight" : ""}>
                    <td></td>
                    <td>{d.label}</td>
                    {s[d.key].slice(1).map((v, i) => (
                      <td key={i} className={"mono num " + (v < 0 ? "neg" : v > 0.04 ? "pos" : "")}>{fmt.pctSigned(v)}</td>
                    ))}
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </Panel>

      <div className="grid-2">
        <Panel title="Globais · fiscalidade & estrutura" sub="src/engine/data/pressupostos/globais.yaml">
          <dl className="kv">
            <KV k="IRC taxa geral" v="20,0%" />
            <KV k="IRC taxa reduzida" v="17,0%" />
            <KV k="Derrama Municipal" v="1,5%" />
            <KV k="Derrama Estadual" v="1,35% (limiar 1,5 M€)" />
            <KV k="TSU empresa" v="23,75%" />
            <KV k="SAT" v="3,0%" />
            <KV k="SIFIDE" v="32,5%" />
            <KV k="Tributação autónoma" v="10,0%" />
            <KV k="Majoração energia" v="20%" />
            <KV k="IVA Vendas / FSE" v="23%" />
          </dl>
        </Panel>
        <Panel title="Prazos · gestão de fundo de maneio">
          <dl className="kv">
            <KV k="PMR — recebimento" v="45 dias" />
            <KV k="PMP — fornecedores" v="63 dias" />
            <KV k="DMI — produto acabado" v="160 dias" />
            <KV k="DMI — matéria-prima" v="160 dias" />
            <KV k="DMI — mercadorias" v="60 dias" />
            <KV k="Caixa mínima" v="500 k€" />
            <KV k="Caixa máxima" v="1,5 M€" />
            <KV k="Payout ratio" v="20%" />
            <KV k="Reserva legal" v="5%" />
            <KV k="Início distribuição" v="2026" />
          </dl>
        </Panel>
      </div>

      <div className="grid-2">
        <Panel title="Pessoal" sub="custos auditados + elasticidade ao volume">
          <dl className="kv">
            <KV k="Custo total 2024 (auditado)" v={fmt.eurC(14371358)} />
            <KV k="Headcount 2024" v="734" />
            <KV k="Headcount 2025" v="744" />
            <KV k="Cresc. base 2025" v="+3,5% (acordos IRCT)" />
            <KV k="Elasticidade α sem Hub" v="0,40" />
            <KV k="Elasticidade α com Hub" v="0,15" />
            <KV k="TSU empregador" v="23,75%" />
            <KV k="Subsídio férias" v="Junho" />
            <KV k="Subsídio Natal" v="Novembro" />
          </dl>
        </Panel>
        <Panel title="Mercados & Canais" sub="mix global 2024">
          <div className="sub-section">
            <div className="sub-label">Geografia · peso global</div>
            <StackedBar
              items={Object.entries(GRESTEL.MERCADOS).map(([k, v], i) => ({
                label: v.label, value: v.peso, color: MIX_PALETTE_4[i], textColor: MIX_PALETTE_4_TEXT[i],
              }))}
            />
            <div className="legend-h" style={{ marginTop: 8 }}>
              {Object.entries(GRESTEL.MERCADOS).map(([k, v], i) => (
                <div key={k} className="legend-h-item">
                  <span className="swatch" style={{ background: MIX_PALETTE_4[i] }} />
                  <span>{v.label}</span>
                  <span className="mono">{fmt.pct(v.peso, 0)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="sub-section">
            <div className="sub-label">Canais comerciais 2024</div>
            <StackedBar
              items={Object.entries(GRESTEL.CANAIS).map(([k, v], i) => ({
                label: k.replace(/_/g, " "), value: v, color: MIX_PALETTE_4[i], textColor: MIX_PALETTE_4_TEXT[i],
              }))}
            />
            <div className="legend-h" style={{ marginTop: 8 }}>
              {Object.entries(GRESTEL.CANAIS).map(([k, v], i) => (
                <div key={k} className="legend-h-item">
                  <span className="swatch" style={{ background: MIX_PALETTE_4[i] }} />
                  <span>{k.replace(/_/g, " ")}</span>
                  <span className="mono">{fmt.pct(v, 0)}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}

// ---- Objetivos SMART --------------------------------------------------------
function SmartBadge({ status }) {
  const cfg = {
    cumprido:     { label: "Cumprido",     color: "var(--pos)",    bg: "var(--pos-soft)" },
    em_risco:     { label: "Em risco",     color: "var(--accent)", bg: "var(--accent-soft)" },
    nao_cumprido: { label: "Não cumprido", color: "var(--neg)",    bg: "var(--neg-soft)" },
    sem_dados:    { label: "Sem dados",    color: "var(--muted)",  bg: "var(--surface-2)" },
  };
  const c = cfg[status] || cfg.sem_dados;
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 3,
      fontSize: 11, fontWeight: 600, letterSpacing: "0.02em", whiteSpace: "nowrap",
      color: c.color, background: c.bg,
    }}>
      {c.label}
    </span>
  );
}

function SmartView({ ctx }) {
  const [tracker, setTracker] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    API.smartTracker({ cenario: ctx.scenario, hub_on: ctx.hubOn, ecogres_on: ctx.ecogresOn })
      .then(data => { if (!cancelled) { setTracker(data); setLoading(false); } })
      .catch(err => { if (!cancelled) { setError(err.message || String(err)); setLoading(false); } });
    return () => { cancelled = true; };
  }, [ctx.scenario, ctx.hubOn, ctx.ecogresOn]);

  if (loading && !tracker) return <LoadingShell />;
  if (error && !tracker) return <ErrorBanner message={error} onRetry={() => { setError(null); setTracker(null); setLoading(true); }} />;
  if (!tracker) return null;

  const CAT_LABEL = { economica: "Económica", financeira: "Financeira", operacional: "Operacional", esg: "ESG / Sustentabilidade" };
  const CAT_ORDER = ["economica", "financeira", "operacional", "esg"];

  function fmtVal(v, unit) {
    if (v === null || v === undefined) return "—";
    if (unit === "EUR")  return fmt.eurC(v);
    if (unit === "pct")  return fmt.pct(v);
    if (unit === "dias") return Math.round(v) + " d";
    return String(v);
  }

  function fmtAlvo(alvo, unit, operador) {
    return (operador === "gte" ? "≥ " : "≤ ") + fmtVal(alvo, unit);
  }

  const withData = tracker.filter(r => r.status !== "sem_dados");
  const counts = { cumprido: 0, em_risco: 0, nao_cumprido: 0 };
  for (const r of withData) counts[r.status] = (counts[r.status] || 0) + 1;
  const total = withData.length;

  const grouped = {};
  for (const cat of CAT_ORDER) grouped[cat] = tracker.filter(r => r.categoria === cat);

  return (
    <>
      <div className="grid-3">
        <KPI
          label="Cumpridos"
          value={counts.cumprido + " / " + total}
          tone={total > 0 && counts.cumprido === total ? "pos" : undefined}
          sub={total > 0 ? fmt.pct(counts.cumprido / total, 0) + " dos objetivos avaliados" : "—"}
        />
        <KPI
          label="Em risco"
          value={String(counts.em_risco)}
          tone={counts.em_risco > 0 ? undefined : "pos"}
          sub="desvio dentro da margem de 5%"
        />
        <KPI
          label="Não cumpridos"
          value={String(counts.nao_cumprido)}
          tone={counts.nao_cumprido > 0 ? "neg" : "pos"}
          sub="desvio superior a 5% do alvo"
        />
      </div>

      <Panel
        title="Tracker de Objetivos SMART · cenário ativo"
        sub="cumprido · em_risco · nao_cumprido — margem de tolerância 5%"
      >
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th style={{ width: "20%" }}>Objetivo</th>
              <th>Descrição</th>
              <th className="mono num" style={{ width: 46 }}>Ano</th>
              <th className="mono num" style={{ width: 96 }}>Alvo</th>
              <th className="mono num" style={{ width: 96 }}>Projeção</th>
              <th className="mono num" style={{ width: 70 }}>Desvio</th>
              <th style={{ width: 112 }}>Estado</th>
            </tr>
          </thead>
          <tbody>
            {CAT_ORDER.map(cat => (
              grouped[cat].length === 0 ? null : (
                <React.Fragment key={cat}>
                  <tr className="is-section">
                    <td colSpan={7}>{CAT_LABEL[cat]}</td>
                  </tr>
                  {grouped[cat].map((r, i) => {
                    const isFirst = i === 0 || grouped[cat][i - 1].id !== r.id;
                    const desvioColor = r.desvio_pct === null ? "var(--muted)"
                      : r.status === "cumprido" ? "var(--pos)"
                      : r.status === "em_risco" ? "var(--accent)"
                      : "var(--neg)";
                    return (
                      <tr key={r.id + "_" + r.ano}>
                        <td style={{ color: isFirst ? undefined : "var(--muted)", paddingLeft: isFirst ? undefined : 20 }}>
                          {isFirst ? r.nome : ""}
                        </td>
                        <td style={{ fontSize: 11, color: "var(--muted)" }}>
                          {isFirst ? r.descricao : ""}
                        </td>
                        <td className="mono num">{r.ano}</td>
                        <td className="mono num">{fmtAlvo(r.alvo, r.unidade, r.operador)}</td>
                        <td className="mono num">{fmtVal(r.valor, r.unidade)}</td>
                        <td className="mono num" style={{ color: desvioColor }}>
                          {r.desvio_pct !== null ? fmt.pctSigned(r.desvio_pct) : "—"}
                        </td>
                        <td><SmartBadge status={r.status} /></td>
                      </tr>
                    );
                  })}
                </React.Fragment>
              )
            ))}
          </tbody>
        </table>
      </Panel>
    </>
  );
}

// ── YamlEditorView ────────────────────────────────────────────────────────────
function YamlEditorView() {
  const [files, setFiles] = React.useState([]);
  const [selectedKey, setSelectedKey] = React.useState(null);
  const [content, setContent] = React.useState("");
  const [original, setOriginal] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [feedback, setFeedback] = React.useState(null); // {type:"ok"|"err", msg}

  React.useEffect(() => {
    API.listYamlFiles()
      .then(d => setFiles(d.files || []))
      .catch(e => setFeedback({ type: "err", msg: e.message }));
  }, []);

  function loadFile(key) {
    setFeedback(null);
    setSelectedKey(key);
    setContent("");
    setOriginal("");
    API.getYamlContent(key)
      .then(d => { setContent(d.content); setOriginal(d.content); })
      .catch(e => setFeedback({ type: "err", msg: e.message }));
  }

  function handleSave() {
    if (!selectedKey) return;
    setSaving(true);
    setFeedback(null);
    API.putYamlContent(selectedKey, content)
      .then(() => { setOriginal(content); setFeedback({ type: "ok", msg: "Guardado com sucesso." }); })
      .catch(e => setFeedback({ type: "err", msg: e.message }))
      .finally(() => setSaving(false));
  }

  function handleReset() {
    setContent(original);
    setFeedback(null);
  }

  function handleRestore() {
    if (!selectedKey) return;
    if (!window.confirm("Repor o ficheiro ao estado original do git?\nTodas as alterações guardadas serão perdidas.")) return;
    setSaving(true);
    setFeedback(null);
    API.restoreYamlContent(selectedKey)
      .then(d => { setContent(d.content); setOriginal(d.content); setFeedback({ type: "ok", msg: "Ficheiro reposto ao estado original." }); })
      .catch(e => setFeedback({ type: "err", msg: e.message }))
      .finally(() => setSaving(false));
  }

  const dirty = content !== original;

  return (
    <>
      <h2 style={{ margin: "0 0 1rem" }}>Editor de Pressupostos</h2>
      {feedback && (
        <div style={{
          padding: "0.6rem 1rem",
          marginBottom: "1rem",
          borderRadius: "6px",
          background: feedback.type === "ok" ? "#d1fae5" : "#fee2e2",
          color: feedback.type === "ok" ? "#065f46" : "#991b1b",
          fontFamily: "monospace",
          fontSize: "0.85rem",
          whiteSpace: "pre-wrap",
        }}>
          {feedback.type === "ok" ? "✓ " : "✗ "}{feedback.msg}
        </div>
      )}
      <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
        <div style={{
          width: "220px",
          flexShrink: 0,
          background: "var(--clr-surface, #f8f7f4)",
          border: "1px solid var(--clr-border, #e2ddd6)",
          borderRadius: "8px",
          padding: "0.5rem",
        }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--clr-muted, #888)", textTransform: "uppercase", padding: "0.25rem 0.5rem 0.5rem" }}>
            Ficheiros editáveis
          </div>
          {files.map(f => (
            <button
              key={f.key}
              onClick={() => loadFile(f.key)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "0.45rem 0.75rem",
                borderRadius: "5px",
                border: "none",
                cursor: "pointer",
                fontSize: "0.8rem",
                background: selectedKey === f.key ? "var(--clr-accent-muted, #ede8df)" : "transparent",
                fontWeight: selectedKey === f.key ? 600 : 400,
                color: f.exists ? "inherit" : "#999",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {selectedKey && (
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{ fontSize: "0.8rem", color: "var(--clr-muted, #888)", fontFamily: "monospace" }}>
                {files.find(f => f.key === selectedKey)?.path}
              </span>
              {dirty && <span style={{ fontSize: "0.75rem", color: "#b45309" }}>● não guardado</span>}
              <span style={{ flex: 1 }} />
              <button
                onClick={handleRestore}
                disabled={saving}
                title="Repor ao estado original do git (apaga alterações guardadas)"
                style={{
                  padding: "0.35rem 0.9rem",
                  borderRadius: "5px",
                  border: "1px solid #f87171",
                  background: "transparent",
                  color: "#b91c1c",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                }}
              >
                Repor original
              </button>
              <button
                onClick={handleReset}
                disabled={!dirty || saving}
                style={{
                  padding: "0.35rem 0.9rem",
                  borderRadius: "5px",
                  border: "1px solid var(--clr-border, #e2ddd6)",
                  background: "transparent",
                  cursor: dirty ? "pointer" : "default",
                  fontSize: "0.82rem",
                  opacity: dirty ? 1 : 0.4,
                }}
              >
                Repor
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !dirty}
                style={{
                  padding: "0.35rem 1rem",
                  borderRadius: "5px",
                  border: "none",
                  background: dirty ? "var(--clr-accent, #7c6e57)" : "#ccc",
                  color: "#fff",
                  cursor: dirty ? "pointer" : "default",
                  fontSize: "0.82rem",
                  fontWeight: 600,
                }}
              >
                {saving ? "A guardar…" : "Guardar"}
              </button>
            </div>
          )}
          <textarea
            value={content}
            onChange={e => { setContent(e.target.value); setFeedback(null); }}
            placeholder={selectedKey ? "A carregar…" : "Seleccione um ficheiro à esquerda."}
            spellCheck={false}
            style={{
              width: "100%",
              height: "72vh",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: "0.82rem",
              lineHeight: 1.55,
              padding: "0.75rem",
              border: "1px solid var(--clr-border, #e2ddd6)",
              borderRadius: "8px",
              background: "var(--clr-surface, #f8f7f4)",
              resize: "vertical",
              outline: "none",
              boxSizing: "border-box",
            }}
          />
        </div>
      </div>
    </>
  );
}

Object.assign(window, {
  DRView, BalancoView, DFCView, KPIView, FSEView, RollingView,
  HubView, HubViabilidadeView, HubMonteCarloView, HubOE4View, FundingCard,
  HubComparativoDR, HubComparativoKPIs, HubConsolidadoView,
  EcogresView, PressupostosView, VendasView, SmartView, SmartBadge, KV, YamlEditorView,
});
