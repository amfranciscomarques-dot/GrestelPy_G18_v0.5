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
    { label: "Resultado Líquido", value: r.rl, type: "delta" },
    { label: "Dep. & Amort.", value: r.dep_amort, type: "delta" },
    { label: "Juros pagos (ajust.)", value: r.juros_pagos, type: "delta" },
    { label: "Variação NFM", value: r.var_nfm, type: "delta" },
    { label: "IRC pago", value: r.irc_pago, type: "delta" },
    { label: "Fluxo operacional", value: r.fluxo_operacional, type: "total" },
    { label: "CAPEX AFT", value: r.pag_aft, type: "delta" },
    { label: "Dividendos recebidos", value: r.div_recebidos, type: "delta" },
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
        sub="método indirecto"
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

      <Panel title="Fluxos por ano" sub="€ · valores anuais · método indirecto">
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>Rubrica</th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
            </tr>
          </thead>
          <tbody>
            <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Atividades Operacionais</td></tr>
            <FRow label="Resultado Líquido" values={dfc.map(d => d.rl)} />
            <FRow label="Depreciações & Amortizações" values={dfc.map(d => d.dep_amort)} />
            <FRow label="Imparidades" values={dfc.map(d => d.imparidades)} />
            <FRow label="Juros pagos (ajust.)" values={dfc.map(d => d.juros_pagos)} />
            <FRow label="Variação do Fundo de Maneio" values={dfc.map(d => d.var_nfm)} />
            <FRow label="IRC pago" values={dfc.map(d => d.irc_pago)} />
            <tr className="is-subtotal"><td>Fluxo operacional</td>{dfc.map((d, i) => <td key={i} className="mono num">{fmt.eur(d.fluxo_operacional)}</td>)}</tr>
            <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Atividades de Investimento</td></tr>
            <FRow label="CAPEX — Ativos Fixos Tangíveis" values={dfc.map(d => d.pag_aft)} />
            <FRow label="CAPEX — Intangíveis" values={dfc.map(d => d.pag_intang)} />
            <FRow label="Dividendos recebidos" values={dfc.map(d => d.div_recebidos)} />
            <tr className="is-subtotal"><td>Fluxo investimento</td>{dfc.map((d, i) => <td key={i} className="mono num">{fmt.eur(d.fluxo_investimento)}</td>)}</tr>
            <tr className="is-section"><td colSpan={GRESTEL.YEARS.length + 1}>Atividades de Financiamento</td></tr>
            <FRow label="Recebimentos de empréstimos" values={dfc.map(d => d.rec_emprestimos)} />
            <FRow label="Pagamentos de empréstimos" values={dfc.map(d => d.pag_emprestimos)} />
            <FRow label="Juros pagos" values={dfc.map(d => d.juros_pagos_fin)} />
            <FRow label="Dividendos distribuídos" values={dfc.map(d => d.pag_dividendos)} />
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
        <Panel title="FSE" sub="€">
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

// ---- Pessoal ---------------------------------------------------------------
function PessoalView({ ctx }) {
  const { pessoal_contab, pessoal_depart, dr } = ctx;
  const [vista, setVista] = useState("contab");

  // Ordem canónica das rubricas/departamentos
  const CONTAB_ORDER  = ["Remuneracoes", "Encargos_TSU", "Seguros_AT", "Outros_Encargos"];
  const CONTAB_LABELS = {
    Remuneracoes:    "Remunerações",
    Encargos_TSU:    "Encargos TSU (23,75%)",
    Seguros_AT:      "Seguros AT (~1,3%)",
    Outros_Encargos: "Outros Encargos",
  };
  const DEPART_ORDER  = ["Producao", "RD", "Comercial", "Financeira", "Marketing"];
  const DEPART_LABELS = {
    Producao:   "Produção",
    RD:         "I&D (R&D)",
    Comercial:  "Comercial",
    Financeira: "Financeira / Admin.",
    Marketing:  "Marketing",
  };

  // Palettes — família terracota para contab (4), escalonada para depart (5)
  const CONTAB_PAL = [
    "oklch(0.34 0.075 40)",
    "oklch(0.54 0.115 45)",
    "oklch(0.68 0.105 65)",
    "oklch(0.83 0.035 75)",
  ];
  const DEPART_PAL = [
    "oklch(0.30 0.070 35)",
    "oklch(0.42 0.100 40)",
    "oklch(0.54 0.115 45)",
    "oklch(0.68 0.105 65)",
    "oklch(0.80 0.050 80)",
  ];

  // Total pessoal por ano (soma das rubricas contab)
  const total = GRESTEL.YEARS.map((_, i) =>
    CONTAB_ORDER.reduce((a, k) => a + (pessoal_contab[k]?.[i] || 0), 0)
  );

  const dr2025 = dr.find(r => r.year === 2025) || { vn: 1 };
  const hc     = ctx.eff?.hc_2025 || 744;

  // ---- Gráfico contabilístico ----
  const stackContab = GRESTEL.YEARS.map((y, i) => ({
    label: String(y),
    bars: CONTAB_ORDER.map((k, ki) => ({
      key: k, value: pessoal_contab[k]?.[i] || 0, color: CONTAB_PAL[ki],
    })),
  }));
  const donutContab = CONTAB_ORDER.map((k, ki) => ({
    label: CONTAB_LABELS[k], value: pessoal_contab[k]?.[0] || 0, color: CONTAB_PAL[ki],
  }));

  // ---- Gráfico departamental ----
  const stackDepart = GRESTEL.YEARS.map((y, i) => ({
    label: String(y),
    bars: DEPART_ORDER.map((k, ki) => ({
      key: k, value: pessoal_depart[k]?.[i] || 0, color: DEPART_PAL[ki],
    })),
  }));
  const donutDepart = DEPART_ORDER.map((k, ki) => ({
    label: DEPART_LABELS[k], value: pessoal_depart[k]?.[0] || 0, color: DEPART_PAL[ki],
  }));

  // helpers
  const isContab = vista === "contab";
  const order    = isContab ? CONTAB_ORDER  : DEPART_ORDER;
  const labels   = isContab ? CONTAB_LABELS : DEPART_LABELS;
  const stack    = isContab ? stackContab   : stackDepart;
  const donut    = isContab ? donutContab   : donutDepart;
  const data     = isContab ? pessoal_contab : pessoal_depart;

  return (
    <>
      <div className="grid-4">
        <KPI label="Pessoal 2024"        value={fmt.eurC(total[0])}                   sub="auditado · R&C 2024" />
        <KPI label="Pessoal 2025"        value={fmt.eurC(total[1])}                   trend={(total[1] - total[0]) / total[0]} />
        <KPI label="% do VN 2025"        value={fmt.pct(total[1] / dr2025.vn)}        sub="peso no volume de negócios" />
        <KPI label="Custo médio / FTE"   value={fmt.eurC(hc ? total[1] / hc : 0)}    sub={hc + " FTE · 2025"} />
      </div>

      <div className="grid-2-3">
        <Panel
          title={isContab ? "Pessoal · Natureza" : "Pessoal · Departamento"}
          sub="€ · barras empilhadas"
          right={
            <div className="seg seg--sm">
              <button className={"seg-btn " + (isContab ? "is-on" : "")} onClick={() => setVista("contab")}>Natureza</button>
              <button className={"seg-btn " + (!isContab ? "is-on" : "")} onClick={() => setVista("depart")}>Departamento</button>
            </div>
          }
        >
          <BarChart groups={stack} stacked height={300} />
        </Panel>

        <Panel
          title={isContab ? "Mix 2024 · Nota 28 / IAS 19" : "Mix 2024 · Imputação funcional"}
          sub={isContab ? "4 rubricas contabilísticas" : "5 departamentos · " + hc + " FTE"}
        >
          <Donut items={donut} />
          <div className="legend-col" style={{ marginTop: 10 }}>
            {donut.map((it, i) => (
              <div key={i} className="legend-row">
                <span className="swatch" style={{ background: it.color }} />
                <span className="legend-label">{it.label}</span>
                <span className="legend-value mono">{fmt.eurC(it.value)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel
        title={isContab ? "Pessoal · Detalhe contabilístico" : "Pessoal · Detalhe departamental"}
        sub={isContab
          ? "Remunerações + encargos patronais · IAS 19"
          : "Imputação funcional sobre custo total projetado"}
      >
        <table className="ftable ftable--dense">
          <thead>
            <tr>
              <th>{isContab ? "Rubrica" : "Departamento"}</th>
              {GRESTEL.YEARS.map(y => <th key={y} className="mono num">{y}</th>)}
              <th className="mono num">% 2024</th>
            </tr>
          </thead>
          <tbody>
            {order.map((k, ki) => (
              <tr key={k}>
                <td>{labels[k]}</td>
                {GRESTEL.YEARS.map((_, i) => (
                  <td key={i} className="mono num">{fmt.eur(data[k]?.[i] || 0)}</td>
                ))}
                <td className="mono num">{fmt.pct((data[k]?.[0] || 0) / (total[0] || 1))}</td>
              </tr>
            ))}
            <tr className="is-total">
              <td>Total Pessoal</td>
              {total.map((v, i) => <td key={i} className="mono num">{fmt.eur(v)}</td>)}
              <td></td>
            </tr>
            <tr className="row-sep"><td colSpan={GRESTEL.YEARS.length + 2}></td></tr>
            <tr>
              <td className="muted">% do VN</td>
              {GRESTEL.YEARS.map((_, i) => {
                const vn = dr.find(r => r.year === GRESTEL.YEARS[i])?.vn || 1;
                return <td key={i} className="mono num muted">{fmt.pct(total[i] / vn)}</td>;
              })}
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
  const [apiRf, setApiRf] = useState(null);

  useEffect(() => {
    setApiRf(null);
    fetch(`/api/rolling-forecast/mensal?scenario=${encodeURIComponent(ctx.scenario)}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        const dr = data.dr_mensal || [];
        const teso = data.tesouraria || [];
        const combined = dr.map((row, i) => {
          const t = teso[i] || {};
          return {
            mes: row.mes || row.month || Object.keys(row)[0],
            vn: row.vn || row.receitas_vendas || 0,
            cmvmc: row.cmvmc || row.custo_merc || 0,
            fse: row.fse || 0,
            pessoal: row.gastos_pessoal || row.pessoal || 0,
            ebitda: row.ebitda || 0,
            recebimentos: t.recebimentos_clientes || t.recebimentos || t.entradas || 0,
            pagamentos: t.pagamentos_fornecedores || t.pagamentos || t.saidas || 0,
            investimento: t.capex_pagamento || t.investimento || t.fluxo_investimento || 0,
            financiamento: t.fluxo_financiamento || t.financiamento || 0,
            caixa_fim: t.caixa_fecho || t.caixa_fim || t.saldo_fim || t.caixa || 0,
          };
        });
        if (combined.length > 0) setApiRf(combined);
      })
      .catch(() => setApiRf(null));
  }, [ctx.scenario, ctx.hubOn]);

  const rf = apiRf || GRESTEL.rollingForecast(ctx.scenario, { hubOn: ctx.hubOn, ecogresOn: ctx.ecogresOn });

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
function HubView({ ctx }) {
  const [irc, setIrc] = useState(0.225);
  const [viab, setViab] = useState(null);
  const [torn, setTorn] = useState(null);

  useEffect(() => {
    fetch(`/api/hub/viability?irc_taxa=${irc}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        const fcf = data.fcf || [];
        const fcf_cumulativo = fcf.reduce((acc, v) => {
          acc.push((acc[acc.length - 1] || 0) + v);
          return acc;
        }, []);
        const anos = Array.from({ length: fcf.length }, (_, i) => 2024 + i);
        setViab({ ...data, fcf, fcf_cumulativo, anos });
      })
      .catch(() => setViab(GRESTEL.hubViability(irc)));
  }, [irc]);

  useEffect(() => {
    fetch("/api/hub/tornado")
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => setTorn(data.rows || []))
      .catch(() => setTorn(GRESTEL.hubTornado()));
  }, []);

  const viabData = viab || GRESTEL.hubViability(irc);
  const tornData = torn || GRESTEL.hubTornado();

  const fcfSeries = [
    { labels: viabData.anos.map(String), values: viabData.fcf, color: "var(--ink)" },
    { labels: viabData.anos.map(String), values: viabData.fcf_cumulativo, color: "var(--accent)", fill: true },
  ];

  return (
    <>
      <div className="grid-4">
        <KPI label="VAN @ 8%" value={fmt.eurC(viabData.vpl)} tone={viabData.vpl >= 0 ? "pos" : "neg"} sub="horizonte 10 anos + valor terminal" />
        <KPI label="TIR" value={fmt.pct(viabData.tir, 1)} tone={viabData.tir >= 0.08 ? "pos" : "neg"} sub={"vs WACC " + fmt.pct(0.08, 0)} />
        <KPI label="Payback simples" value={viabData.payback_simples ? String(viabData.payback_simples) : "—"} sub={"em anos · ref. 2024"} />
        <KPI label="Payback actualizado" value={viabData.payback_atualizado ? String(viabData.payback_atualizado) : "—"} sub={"descontado a 8%"} />
      </div>

      <Panel
        title="Fluxos de caixa livres · projeto Hub Logístico (M6)"
        sub={"CAPEX € 5,5 M (2025-26) · benefício líquido base 255 k€/ano · IRC " + fmt.pct(irc)}
        right={
          <div className="seg seg--sm">
            {[0.17, 0.20, 0.21, 0.225, 0.24].map(t => (
              <button key={t} className={"seg-btn " + (Math.abs(irc - t) < 0.001 ? "is-on" : "")} onClick={() => setIrc(t)}>{fmt.pct(t, 1)}</button>
            ))}
          </div>
        }
      >
        <LineChart series={fcfSeries} height={300} />
        <div className="legend" style={{ marginTop: 8 }}>
          <div className="legend-row"><span className="swatch" style={{ background: "var(--ink)" }} /><span>FCF anual</span></div>
          <div className="legend-row"><span className="swatch" style={{ background: "var(--accent)" }} /><span>FCF acumulado</span></div>
        </div>
      </Panel>

      <div className="grid-2">
        <Panel title="Análise de sensibilidade · tornado" sub="impacto na VAN em milhões de euros">
          <TornadoChart rows={tornData} height={300} />
        </Panel>
        <Panel title="Parâmetros do projeto" sub="src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml">
          <dl className="kv">
            <KV k="CAPEX base" v={fmt.eurC(5500000)} />
            <KV k="Cronograma 2025" v={fmt.eurC(3300000)} />
            <KV k="Cronograma 2026" v={fmt.eurC(2200000)} />
            <KV k="Vida útil" v="10 anos · taxa depr. 10%" />
            <KV k="WACC" v="8,0%" />
            <KV k="Crescimento terminal" v="1,5%" />
            <KV k="Poupança operacional" v={fmt.eurC(300000) + " / ano"} />
            <KV k="Redução quebras" v={fmt.eurC(75000) + " / ano"} />
            <KV k="OPEX incremental" v={"− " + fmt.eurC(120000) + " / ano"} />
            <KV k="Crescimento benefícios" v="+2,0% / ano" />
            <KV k="Libertação inventário 2026" v={fmt.eurC(1500000)} />
            <KV k="Banco Hub" v={fmt.eurC(4125000) + " @ 4,15%"} />
            <KV k="PT2030" v={fmt.eurC(2200000) + " · 2027"} />
            <KV k="Início benefícios" v="2026" />
          </dl>
        </Panel>
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

// ---- Ecogres ---------------------------------------------------------------
function EcogresView({ ctx }) {
  const [apiEco, setApiEco] = useState(null);

  useEffect(() => {
    setApiEco(null);
    fetch(`/api/ecogres?hub_on=${ctx.hubOn}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        const rows = (data.rows || []).map(r => ({
          year: r.ano,
          subc: r.receita_subcontratacao || 0,
          ced: r.cedencia_pessoal || 0,
          transfer_hub: r.receita_hub || 0,
          vendas_externas: 0,
          rec_total: r.receita_total || 0,
          custos_op: r.custo_total_operacional || 0,
          dep: r.depreciacao || 0,
          ebitda: r.ebitda || 0,
          ebit: r.ebit || 0,
          rai: r.rai || 0,
          irc: r.irc || 0,
          rl: r.rl || 0,
        }));
        if (rows.length > 0) setApiEco(rows);
      })
      .catch(() => setApiEco(null));
  }, [ctx.hubOn]);

  const eco = apiEco || GRESTEL.projectEcogres(ctx.hubOn);
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
        title="Ecogres"
        sub="Demonstração dos Resultados"
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

// ---- Pressupostos ----------------------------------------------------------
function PressupostosView({ ctx }) {
  const e = ctx.eff || {};
  const p = (v, d = 1) => v != null ? fmt.pct(v / 100, d) : "—";
  const dias = (v) => v != null ? v + " dias" : "—";
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
        <Panel title="Globais · Fiscalidade & Estrutura" sub="src/engine/data/pressupostos/globais.yaml">
          <dl className="kv">
            <KV k="IRC taxa geral" v={p(e.irc_taxa_geral)} />
            <KV k="IRC taxa reduzida" v={p(e.irc_taxa_reduzida)} />
            <KV k="Derrama Municipal" v={p(e.derrama_municipal)} />
            <KV k="Derrama Estadual" v={e.derrama_estadual != null ? p(e.derrama_estadual, 2) + " (limiar " + fmt.eurC(e.derrama_estadual_limiar) + ")" : "—"} />
            <KV k="TSU empresa" v={p(e.tsu_empresa, 2)} />
            <KV k="SAT" v={p(e.sat)} />
            <KV k="SIFIDE" v={p(e.sifide_taxa)} />
            <KV k="Tributação autónoma" v={p(e.tributacao_autonoma)} />
            <KV k="Majoração energia" v={p(e.majoracao_energia, 0)} />
            <KV k="IVA Vendas / FSE" v={p(e.iva_vendas, 0)} />
          </dl>
        </Panel>
        <Panel title="Prazos · Gestão do fundo de maneio">
          <dl className="kv">
            <KV k="PMR — recebimento" v={dias(e.pmr_dias)} />
            <KV k="PMP — fornecedores" v={dias(e.pmp_dias)} />
            <KV k="DMI — produto acabado" v={dias(e.dmi_pa_dias)} />
            <KV k="DMI — matéria-prima" v={dias(e.dmi_mp_dias)} />
            <KV k="DMI — mercadorias" v={dias(e.dmi_merc_dias)} />
            <KV k="Caixa mínima" v={e.caixa_minima != null ? fmt.eurC(e.caixa_minima) : "—"} />
            <KV k="Caixa máxima" v={e.caixa_maxima != null ? fmt.eurC(e.caixa_maxima) : "—"} />
            <KV k="Payout ratio" v={p(e.payout_ratio, 0)} />
            <KV k="Reserva legal" v={p(e.reserva_legal_pct, 0)} />
            <KV k="Início distribuição" v={e.inicio_distribuicao ?? "—"} />
          </dl>
        </Panel>
      </div>

      <div className="grid-2">
        <Panel title="Pessoal" sub="Custos Historicos + Elasticidade Crescimento Vendas">
          <dl className="kv">
            <KV k="Gastos com Pessoal 2024" v={e.custo_total_2024 != null ? fmt.eurC(e.custo_total_2024) : "—"} />
            <KV k="Headcount 2024" v={e.hc_2024 ?? "—"} />
            <KV k="Headcount 2025" v={e.hc_2025 ?? "—"} />
            <KV k="Crescimento base 2025" v={e.taxa_cresc_custo_2025 != null ? "+" + p(e.taxa_cresc_custo_2025) + " (IRCT)" : "—"} />
            <KV k="Elasticidade α sem Hub" v={e.alpha_sem_hub != null ? (e.alpha_sem_hub / 100).toFixed(2).replace(".", ",") : "—"} />
            <KV k="Elasticidade α com Hub" v={e.alpha_com_hub != null ? (e.alpha_com_hub / 100).toFixed(2).replace(".", ",") : "—"} />
            <KV k="TSU" v={p(e.tsu_empregador, 2)} />
            <KV k="Subsídio Férias" v={e.subsidio_ferias_mes ?? "—"} />
            <KV k="Subsídio Natal" v={e.subsidio_natal_mes ?? "—"} />
          </dl>
        </Panel>
        <Panel title="Mercados & Canais" sub="Mix Global 2024">
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
            <div className="sub-label">Canais Comerciais 2024</div>
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

Object.assign(window, {
  DRView, BalancoView, DFCView, KPIView, FSEView, PessoalView, RollingView, HubView, EcogresView, PressupostosView, KV,
});
