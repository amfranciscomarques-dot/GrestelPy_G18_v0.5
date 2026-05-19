// charts.jsx — SVG chart primitives for the Grestel dashboard.

const fmt = {
  // €1,234,567 — full
  eur: (v) => {
    if (v == null || isNaN(v)) return "—";
    const sign = v < 0 ? "−" : "";
    const a = Math.abs(v);
    return sign + "€" + a.toLocaleString("pt-PT", { maximumFractionDigits: 0 });
  },
  // €1,2 M — compact for axes/KPIs (non-breaking space keeps unit attached)
  eurC: (v) => {
    if (v == null || isNaN(v)) return "—";
    const sign = v < 0 ? "−" : "";
    const a = Math.abs(v);
    if (a >= 1e6) return sign + "€" + (a / 1e6).toFixed(1).replace(".", ",") + "\u00A0M";
    if (a >= 1e3) return sign + "€" + (a / 1e3).toFixed(0) + "\u00A0k";
    return sign + "€" + a.toFixed(0);
  },
  // 23,5%
  pct: (v, d = 1) => {
    if (v == null || isNaN(v)) return "—";
    return (v * 100).toFixed(d).replace(".", ",") + "%";
  },
  // +3,5% with sign
  pctSigned: (v, d = 1) => {
    if (v == null || isNaN(v)) return "—";
    const s = v > 0 ? "+" : "";
    return s + (v * 100).toFixed(d).replace(".", ",") + "%";
  },
  // 1,5×
  ratio: (v, d = 2) => v.toFixed(d).replace(".", ",") + "×",
  // Numero
  num: (v, d = 0) => v.toLocaleString("pt-PT", { maximumFractionDigits: d }),
};

const COL = {
  bg: "var(--bg)",
  surface: "var(--surface)",
  ink: "var(--ink)",
  muted: "var(--muted)",
  faint: "var(--faint)",
  rule: "var(--rule)",
  accent: "var(--accent)",
  pos: "var(--pos)",
  neg: "var(--neg)",
};

// ---------------------------------------------------------------------------
// Tooltip plumbing — shared by every chart primitive.
// useTooltip() returns:
//   containerRef  → put on the wrapping <div>; tooltip is positioned relative to it
//   tip / setTip  → { x, y, rows: [{label, value, color?, bold?}], anchor? }
//   onMove(e,data)→ helper for mouse-move handlers
//   onLeave       → clears the tooltip
// <ChartTooltip tip={tip}/> draws the floating card.
// ---------------------------------------------------------------------------
function useTooltip() {
  const containerRef = React.useRef(null);
  const [tip, setTip] = React.useState(null);
  const onMove = React.useCallback((e, data) => {
    const r = containerRef.current?.getBoundingClientRect();
    if (!r) return;
    setTip({ x: e.clientX - r.left, y: e.clientY - r.top, ...data });
  }, []);
  const onLeave = React.useCallback(() => setTip(null), []);
  return { containerRef, tip, setTip, onMove, onLeave };
}

function ChartTooltip({ tip, containerWidth }) {
  if (!tip || !tip.rows || tip.rows.length === 0) return null;
  // Flip to the left of cursor if it would overflow right edge.
  const estW = 180;
  const flipX = containerWidth && tip.x + estW + 24 > containerWidth;
  const style = {
    position: "absolute",
    left: flipX ? tip.x - 12 : tip.x + 14,
    top: tip.y + 14,
    transform: flipX ? "translateX(-100%)" : undefined,
    pointerEvents: "none",
    background: "var(--ink)",
    color: "var(--surface)",
    padding: "7px 9px",
    fontSize: 11,
    lineHeight: 1.4,
    fontFamily: "var(--ui)",
    whiteSpace: "nowrap",
    zIndex: 20,
    boxShadow: "0 4px 14px rgba(0,0,0,0.18)",
    minWidth: 0,
  };
  return (
    <div style={style}>
      {tip.title && (
        <div style={{ fontSize: 10, color: "var(--faint-strong)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4, fontWeight: 500 }}>{tip.title}</div>
      )}
      {tip.rows.map((r, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: r.bold ? 600 : 400 }}>
          {r.color && <span style={{ display: "inline-block", width: 8, height: 8, background: r.color, flexShrink: 0 }} />}
          <span style={{ flex: 1 }}>{r.label}</span>
          <span style={{ fontFamily: "var(--mono)", marginLeft: 12 }}>{r.value}</span>
        </div>
      ))}
    </div>
  );
}

// Lightweight wrapper that gives the chart a positioned container + width tracking.
function ChartFrame({ children, onContainer }) {
  return null; // not used directly; pattern is inlined below for clarity
}

// Simple line chart with optional area fill.
function LineChart({ series, height = 220, padding = { top: 16, right: 16, bottom: 28, left: 56 }, yFormat = fmt.eurC, showGrid = true, showDots = true, tooltipFormat }) {
  const [w, setW] = React.useState(640);
  const { containerRef, tip, onMove, onLeave, setTip } = useTooltip();
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setW(e.contentRect.width);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);
  const allVals = series.flatMap(s => s.values);
  let yMin = Math.min(0, ...allVals);
  let yMax = Math.max(...allVals);
  const pad = (yMax - yMin) * 0.1;
  yMax += pad;
  if (yMin < 0) yMin -= pad;
  const labels = series[0].labels;
  const innerW = w - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const x = (i) => padding.left + (i * innerW / Math.max(1, labels.length - 1));
  const y = (v) => padding.top + innerH * (1 - (v - yMin) / (yMax - yMin || 1));

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (i * (yMax - yMin) / ticks));

  const tipFmt = tooltipFormat || yFormat;
  const handleMove = (e) => {
    const svg = e.currentTarget;
    const pt = svg.getBoundingClientRect();
    const mx = e.clientX - pt.left;
    // find nearest label index
    let bestI = 0, bestD = Infinity;
    for (let i = 0; i < labels.length; i++) {
      const d = Math.abs(x(i) - mx);
      if (d < bestD) { bestD = d; bestI = i; }
    }
    onMove(e, {
      title: labels[bestI],
      anchorX: x(bestI),
      rows: series.map(s => ({
        label: s.label || s.key || "Série",
        value: tipFmt(s.values[bestI]),
        color: s.color,
      })),
    });
  };

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} style={{ display: "block" }} onMouseMove={handleMove} onMouseLeave={onLeave}>
        {showGrid && yTicks.map((t, i) => (
          <line key={i} x1={padding.left} x2={w - padding.right} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth="1" />
        ))}
        {yTicks.map((t, i) => (
          <text key={"yt" + i} x={padding.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{yFormat(t)}</text>
        ))}
        {labels.map((l, i) => (
          <text key={"xt" + i} x={x(i)} y={height - 8} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{l}</text>
        ))}
        {series.map((s, si) => {
          const path = s.values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`).join(" ");
          const area = s.fill ? `${path} L${x(s.values.length - 1)},${y(0)} L${x(0)},${y(0)} Z` : null;
          return (
            <g key={si}>
              {area && <path d={area} fill={s.color} opacity="0.08" />}
              <path d={path} fill="none" stroke={s.color} strokeWidth={s.width || 2} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={s.dash || undefined} />
              {showDots && s.values.map((v, i) => (
                <circle key={i} cx={x(i)} cy={y(v)} r="3" fill="var(--surface)" stroke={s.color} strokeWidth="1.5" />
              ))}
            </g>
          );
        })}
        {tip && tip.anchorX != null && (
          <g pointerEvents="none">
            <line x1={tip.anchorX} x2={tip.anchorX} y1={padding.top} y2={height - padding.bottom} stroke="var(--ink)" strokeWidth="1" strokeDasharray="2 3" opacity="0.4" />
            {series.map((s, si) => {
              // re-find index from anchorX
              const idx = labels.findIndex((_, i) => x(i) === tip.anchorX);
              if (idx < 0) return null;
              return <circle key={si} cx={tip.anchorX} cy={y(s.values[idx])} r="4" fill={s.color} stroke="var(--surface)" strokeWidth="1.5" />;
            })}
          </g>
        )}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

// Vertical bar chart (grouped or single).
function BarChart({ groups, height = 220, padding = { top: 16, right: 16, bottom: 28, left: 56 }, yFormat = fmt.eurC, stacked = false }) {
  const [w, setW] = React.useState(640);
  const { containerRef, tip, onMove, onLeave } = useTooltip();
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) setW(e.contentRect.width); });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // groups: [{label, bars: [{key, value, color}]}]
  const labels = groups.map(g => g.label);
  let yMin, yMax;
  if (stacked) {
    yMin = 0;
    yMax = Math.max(...groups.map(g => g.bars.reduce((a, b) => a + Math.max(0, b.value), 0)));
  } else {
    const all = groups.flatMap(g => g.bars.map(b => b.value));
    yMin = Math.min(0, ...all);
    yMax = Math.max(0, ...all);
  }
  const pad = (yMax - yMin) * 0.1;
  yMax += pad;
  if (yMin < 0) yMin -= pad;
  const innerW = w - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const groupW = innerW / Math.max(1, labels.length);
  const y = (v) => padding.top + innerH * (1 - (v - yMin) / (yMax - yMin || 1));

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (i * (yMax - yMin) / ticks));

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} style={{ display: "block" }} onMouseLeave={onLeave}>
        {yTicks.map((t, i) => (
          <line key={i} x1={padding.left} x2={w - padding.right} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth="1" />
        ))}
        {yTicks.map((t, i) => (
          <text key={"yt" + i} x={padding.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{yFormat(t)}</text>
        ))}
        {groups.map((g, gi) => {
          const cx = padding.left + groupW * (gi + 0.5);
          const nBars = g.bars.length;
          const barW = stacked ? Math.min(36, groupW * 0.6) : Math.min(28, (groupW * 0.7) / nBars);
          let stackTop = 0;
          return (
            <g key={gi}>
              <text x={cx} y={height - 8} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{g.label}</text>
              {g.bars.map((b, bi) => {
                const groupTotal = g.bars.reduce((a, x) => a + Math.max(0, x.value), 0);
                const tipRows = stacked
                  ? g.bars.map(x => ({ label: x.key, value: yFormat(x.value), color: x.color, bold: x.key === b.key }))
                  : [{ label: b.key, value: yFormat(b.value), color: b.color }];
                const handle = (e) => onMove(e, { title: g.label, rows: tipRows });
                if (stacked) {
                  const top = y(stackTop + b.value);
                  const bot = y(stackTop);
                  stackTop += b.value;
                  return (
                    <rect
                      key={bi}
                      x={cx - barW / 2}
                      y={top}
                      width={barW}
                      height={Math.max(0, bot - top)}
                      fill={b.color}
                      onMouseMove={handle}
                      onMouseEnter={handle}
                      style={{ cursor: "default" }}
                    />
                  );
                } else {
                  const x0 = cx - (barW * nBars) / 2 + bi * barW;
                  const top = b.value >= 0 ? y(b.value) : y(0);
                  const h = Math.abs(y(b.value) - y(0));
                  return (
                    <rect
                      key={bi}
                      x={x0}
                      y={top}
                      width={barW - 2}
                      height={h}
                      fill={b.color}
                      onMouseMove={handle}
                      onMouseEnter={handle}
                      style={{ cursor: "default" }}
                    />
                  );
                }
              })}
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

// Waterfall — for DFC.
function WaterfallChart({ items, height = 220, padding, yFormat = fmt.eurC, labelRotate = "auto" }) {
  const rotate = labelRotate === "auto" ? (items.length > 6 ? -28 : 0) : labelRotate;
  padding = padding || { top: 16, right: 16, bottom: rotate ? 64 : 40, left: 70 };
  // items: [{label, value, type: "delta" | "total"}]
  const [w, setW] = React.useState(640);
  const { containerRef, tip, onMove, onLeave } = useTooltip();
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) setW(e.contentRect.width); });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Compute cumulative for delta items, totals are absolute.
  const cum = [];
  let running = 0;
  for (const it of items) {
    if (it.type === "total") {
      cum.push({ from: 0, to: it.value, val: it.value, total: true, label: it.label });
      running = it.value;
    } else {
      cum.push({ from: running, to: running + it.value, val: it.value, total: false, label: it.label });
      running += it.value;
    }
  }
  const all = cum.flatMap(c => [c.from, c.to]);
  let yMin = Math.min(0, ...all);
  let yMax = Math.max(0, ...all);
  const pad = (yMax - yMin) * 0.1;
  yMax += pad; if (yMin < 0) yMin -= pad;

  const innerW = w - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const barW = Math.min(40, (innerW / items.length) * 0.6);
  const y = (v) => padding.top + innerH * (1 - (v - yMin) / (yMax - yMin || 1));
  const x = (i) => padding.left + (innerW / items.length) * (i + 0.5);

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (i * (yMax - yMin) / ticks));

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} style={{ display: "block" }} onMouseLeave={onLeave}>
        {yTicks.map((t, i) => (
          <line key={i} x1={padding.left} x2={w - padding.right} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth="1" />
        ))}
        {yTicks.map((t, i) => (
          <text key={"yt" + i} x={padding.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{yFormat(t)}</text>
        ))}
        {cum.map((c, i) => {
          const top = y(Math.max(c.from, c.to));
          const bot = y(Math.min(c.from, c.to));
          const color = c.total ? "var(--ink)" : c.val >= 0 ? "var(--pos)" : "var(--neg)";
          const handle = (e) => onMove(e, {
            title: c.label,
            rows: c.total
              ? [{ label: "Total", value: yFormat(c.val), color, bold: true }]
              : [
                  { label: c.val >= 0 ? "Contributo" : "Subtração", value: yFormat(c.val), color },
                  { label: "Acumulado", value: yFormat(c.to), color: "var(--muted)" },
                ],
          });
          return (
            <g key={i}>
              <rect
                x={x(i) - barW / 2}
                y={top}
                width={barW}
                height={Math.max(2, bot - top)}
                fill={color}
                opacity={c.total ? 1 : 0.85}
                onMouseMove={handle}
                onMouseEnter={handle}
                style={{ cursor: "default" }}
              />
              <text x={x(i)} y={top - 6} textAnchor="middle" fontSize="10" fill="var(--ink)" fontFamily="var(--mono)" fontWeight="500" pointerEvents="none">{yFormat(c.val)}</text>
              {rotate ? (
                <text
                  x={x(i)}
                  y={height - padding.bottom + 14}
                  textAnchor="end"
                  fontSize="11"
                  fill={c.total ? "var(--ink)" : "var(--ink-2)"}
                  fontFamily="var(--ui)"
                  fontWeight={c.total ? 500 : 400}
                  transform={`rotate(${rotate} ${x(i)} ${height - padding.bottom + 14})`}
                  pointerEvents="none"
                >{c.label}</text>
              ) : (
                <>
                  <text x={x(i)} y={height - 22} textAnchor="middle" fontSize="11" fill="var(--ink)" fontFamily="var(--ui)" pointerEvents="none">{c.label.split(" ").slice(0, 2).join(" ")}</text>
                  {c.label.split(" ").length > 2 && (
                    <text x={x(i)} y={height - 8} textAnchor="middle" fontSize="11" fill="var(--ink)" fontFamily="var(--ui)" pointerEvents="none">{c.label.split(" ").slice(2).join(" ")}</text>
                  )}
                </>
              )}
              {i < cum.length - 1 && !cum[i + 1].total && (
                <line x1={x(i) + barW / 2} x2={x(i + 1) - barW / 2} y1={y(c.to)} y2={y(c.to)} stroke="var(--muted)" strokeDasharray="2 2" strokeWidth="1" />
              )}
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

// Tornado chart for sensitivity analysis.
function TornadoChart({ rows, height = 280, padding = { top: 16, right: 24, bottom: 28, left: 180 } }) {
  const [w, setW] = React.useState(640);
  const { containerRef, tip, onMove, onLeave } = useTooltip();
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) setW(e.contentRect.width); });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const all = rows.flatMap(r => [r.low, r.high]);
  const max = Math.max(...all.map(Math.abs));
  const xMin = -max * 1.1, xMax = max * 1.1;
  const innerW = w - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const rowH = innerH / rows.length;
  const x = (v) => padding.left + innerW * ((v - xMin) / (xMax - xMin));

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} style={{ display: "block" }} onMouseLeave={onLeave}>
        <line x1={x(0)} x2={x(0)} y1={padding.top} y2={height - padding.bottom} stroke="var(--ink)" strokeWidth="1" />
        {[-max, -max / 2, 0, max / 2, max].map((t, i) => (
          <g key={i}>
            <text x={x(t)} y={height - 10} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{(t >= 0 ? "+" : "") + t.toFixed(1) + " M"}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const cy = padding.top + rowH * (i + 0.5);
          const xLo = Math.min(x(0), x(r.low));
          const xHi = Math.max(x(0), x(r.high));
          const onLo = (e) => onMove(e, { title: r.variavel, rows: [{ label: "Downside", value: r.low.toFixed(1) + " M", color: "var(--neg)" }] });
          const onHi = (e) => onMove(e, { title: r.variavel, rows: [{ label: "Upside", value: "+" + r.high.toFixed(1) + " M", color: "var(--pos)" }] });
          return (
            <g key={i}>
              <text x={padding.left - 12} y={cy + 4} textAnchor="end" fontSize="12" fill="var(--ink)" fontFamily="var(--ui)">{r.variavel}</text>
              <rect x={xLo} y={cy - 9} width={x(0) - xLo} height="18" fill="var(--neg)" opacity="0.85" onMouseMove={onLo} onMouseEnter={onLo} style={{ cursor: "default" }} />
              <rect x={x(0)} y={cy - 9} width={xHi - x(0)} height="18" fill="var(--pos)" opacity="0.85" onMouseMove={onHi} onMouseEnter={onHi} style={{ cursor: "default" }} />
              <text x={xLo - 6} y={cy + 4} textAnchor="end" fontSize="10" fill="var(--muted)" fontFamily="var(--mono)" pointerEvents="none">{r.low.toFixed(1)}M</text>
              <text x={xHi + 6} y={cy + 4} fontSize="10" fill="var(--muted)" fontFamily="var(--mono)" pointerEvents="none">+{r.high.toFixed(1)}M</text>
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

// Sparkline (compact, no axes).
function Sparkline({ values, width = 100, height = 32, color = "var(--ink)", showDot = true }) {
  const yMin = Math.min(...values);
  const yMax = Math.max(...values);
  const pad = (yMax - yMin) * 0.1 || 1;
  const x = (i) => (i / Math.max(1, values.length - 1)) * width;
  const y = (v) => height - ((v - yMin + pad / 2) / (yMax - yMin + pad)) * height;
  const path = values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(v)}`).join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      {showDot && <circle cx={x(values.length - 1)} cy={y(values[values.length - 1])} r="2.5" fill={color} />}
    </svg>
  );
}

// Donut for mix breakdowns.
function Donut({ items, size = 180, thickness = 28, valueFormat = fmt.eurC, centerLabel = "Total", centerValue = null, gap = 0.012 }) {
  const total = items.reduce((a, b) => a + b.value, 0);
  const r = size / 2 - 4;
  const ri = r - thickness;
  const cx = size / 2, cy = size / 2;
  const { containerRef, tip, onMove, onLeave, setTip } = useTooltip();
  const [hoverIdx, setHoverIdx] = React.useState(null);

  // Pre-compute angles
  let angle = -Math.PI / 2;
  const arcs = items.map((it) => {
    const frac = it.value / total;
    const fullSpan = frac * Math.PI * 2;
    // Apply a small angular gap between slices (only if more than 1 slice and slice is wide enough)
    const trimmedSpan = items.length > 1 ? Math.max(0, fullSpan - gap) : fullSpan;
    const a0 = angle;
    const a1 = angle + trimmedSpan;
    angle += fullSpan;
    return { a0, a1, frac, it };
  });

  return (
    <div ref={containerRef} style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ display: "block", overflow: "visible" }} onMouseLeave={() => { onLeave(); setHoverIdx(null); }}>
        {arcs.map(({ a0, a1, frac, it }, i) => {
          const isHover = hoverIdx === i;
          // Slight outward translation on hover
          const midA = (a0 + a1) / 2;
          const dx = isHover ? Math.cos(midA) * 3 : 0;
          const dy = isHover ? Math.sin(midA) * 3 : 0;
          const large = (a1 - a0) > Math.PI ? 1 : 0;
          const p0 = [cx + r * Math.cos(a0), cy + r * Math.sin(a0)];
          const p1 = [cx + r * Math.cos(a1), cy + r * Math.sin(a1)];
          const q0 = [cx + ri * Math.cos(a1), cy + ri * Math.sin(a1)];
          const q1 = [cx + ri * Math.cos(a0), cy + ri * Math.sin(a0)];
          const d = `M${p0[0]},${p0[1]} A${r},${r} 0 ${large} 1 ${p1[0]},${p1[1]} L${q0[0]},${q0[1]} A${ri},${ri} 0 ${large} 0 ${q1[0]},${q1[1]} Z`;
          const handle = (e) => {
            setHoverIdx(i);
            onMove(e, {
              title: it.label,
              rows: [
                { label: "Valor", value: valueFormat(it.value), color: it.color },
                { label: "Quota", value: (frac * 100).toFixed(1).replace(".", ",") + "%", color: "var(--muted)" },
              ],
            });
          };
          return (
            <path
              key={i}
              d={d}
              fill={it.color}
              transform={`translate(${dx} ${dy})`}
              style={{ transition: "transform 120ms ease-out, opacity 120ms", cursor: "default", opacity: hoverIdx == null || isHover ? 1 : 0.55 }}
              onMouseMove={handle}
              onMouseEnter={handle}
            />
          );
        })}
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize="10" fill="var(--muted)" fontFamily="var(--ui)" style={{ textTransform: "uppercase", letterSpacing: "0.06em" }} pointerEvents="none">{centerLabel}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="15" fill="var(--ink)" fontFamily="var(--mono)" fontWeight="500" pointerEvents="none">{centerValue != null ? centerValue : valueFormat(total)}</text>
      </svg>
      <ChartTooltip tip={tip} containerWidth={size} />
    </div>
  );
}

// Horizontal stacked bar (for mercados/canais)
function StackedBar({ items, height = 36, valueFormat = (v) => (v * 100).toFixed(0).replace(".", ",") + "%", showLabels = true, gap = 2 }) {
  const total = items.reduce((a, b) => a + b.value, 0);
  const { containerRef, tip, onMove, onLeave } = useTooltip();
  const [hoverIdx, setHoverIdx] = React.useState(null);
  const [w, setW] = React.useState(600);
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) setW(e.contentRect.width); });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  let acc = 0;
  const segments = items.map((it, i) => {
    const frac = it.value / total;
    const x = acc;
    acc += frac;
    return { x, w: frac, it, i };
  });

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
      <svg width="100%" height={height} preserveAspectRatio="none" viewBox={`0 0 ${w} ${height}`} style={{ display: "block" }} onMouseLeave={() => { onLeave(); setHoverIdx(null); }}>
        {segments.map(({ x, w: segW, it, i }) => {
          const isHover = hoverIdx === i;
          const x0 = x * w + (i === 0 ? 0 : gap / 2);
          const segWidthPx = segW * w - (i === 0 ? gap / 2 : gap / 2) - (i === segments.length - 1 ? gap / 2 : gap / 2);
          // simpler: equal half-gap on both inner sides
          const leftPad = i === 0 ? 0 : gap / 2;
          const rightPad = i === segments.length - 1 ? 0 : gap / 2;
          const px = x * w + leftPad;
          const pw = Math.max(0, segW * w - leftPad - rightPad);
          const handle = (e) => {
            setHoverIdx(i);
            onMove(e, {
              title: it.label,
              rows: [
                { label: "Quota", value: (segW * 100).toFixed(1).replace(".", ",") + "%", color: it.color },
                ...(it.amount != null ? [{ label: "Valor", value: fmt.eurC(it.amount), color: "var(--muted)" }] : []),
              ],
            });
          };
          return (
            <g key={i}>
              <rect
                x={px}
                y={0}
                width={pw}
                height={height}
                fill={it.color}
                opacity={hoverIdx == null || isHover ? 1 : 0.7}
                style={{ transition: "opacity 120ms" }}
                onMouseMove={handle}
                onMouseEnter={handle}
              />
              {showLabels && pw > 38 && (
                <text
                  x={px + pw / 2}
                  y={height / 2 + 4}
                  textAnchor="middle"
                  fontSize="11"
                  fill={it.textColor || "var(--surface)"}
                  fontFamily="var(--mono)"
                  fontWeight="500"
                  pointerEvents="none"
                >{valueFormat(it.value)}</text>
              )}
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// HistogramChart — distribuição estocástica (Monte Carlo).
// Props: bins (centers), counts (frequência por bin), edges (len = bins+1),
//        baselineMark (valor x para linha tracejada vermelha), baselineLabel,
//        percentiles (opcional, [{p, value}]).
// ---------------------------------------------------------------------------
function HistogramChart({ bins, counts, edges, baselineMark, baselineLabel, percentiles, height = 240, padding = { top: 20, right: 16, bottom: 32, left: 56 }, xFormat = fmt.eurC }) {
  const [w, setW] = React.useState(640);
  const { containerRef, tip, onMove, onLeave } = useTooltip();
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) setW(e.contentRect.width); });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const xMin = edges[0], xMax = edges[edges.length - 1];
  const yMax = Math.max(...counts) * 1.10 || 1;
  const total = counts.reduce((a, b) => a + b, 0);
  const innerW = w - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const x = (v) => padding.left + ((v - xMin) / (xMax - xMin || 1)) * innerW;
  const y = (v) => padding.top + innerH * (1 - v / yMax);

  const xTicks = 6;
  const xTickVals = Array.from({ length: xTicks + 1 }, (_, i) => xMin + (xMax - xMin) * i / xTicks);
  const yTicks = 4;
  const yTickVals = Array.from({ length: yTicks + 1 }, (_, i) => yMax * i / yTicks);

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} style={{ display: "block" }} onMouseLeave={onLeave}>
        {yTickVals.map((t, i) => (
          <g key={"yg" + i}>
            <line x1={padding.left} x2={w - padding.right} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth="1" />
            <text x={padding.left - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{Math.round(t)}</text>
          </g>
        ))}
        {counts.map((c, i) => {
          const x0 = x(edges[i]);
          const x1 = x(edges[i + 1]);
          const yT = y(c);
          const handle = (e) => onMove(e, {
            title: xFormat(edges[i]) + " — " + xFormat(edges[i + 1]),
            rows: [
              { label: "Frequência", value: c + " / " + total, color: "var(--accent)" },
              { label: "% das simulações", value: fmt.pct(c / total, 1), color: "var(--muted)" },
            ],
          });
          return (
            <rect key={i} x={x0 + 0.5} y={yT} width={Math.max(1, x1 - x0 - 1)} height={padding.top + innerH - yT}
              fill="var(--accent)" opacity="0.85" onMouseMove={handle} onMouseEnter={handle} style={{ cursor: "default" }} />
          );
        })}
        {percentiles && percentiles.map((p, i) => (
          <line key={"p" + i} x1={x(p.value)} x2={x(p.value)}
            y1={padding.top + innerH - 10} y2={padding.top + innerH}
            stroke="var(--ink)" strokeWidth="1" opacity="0.45" />
        ))}
        {baselineMark != null && (
          <g pointerEvents="none">
            <line x1={x(baselineMark)} x2={x(baselineMark)} y1={padding.top - 4} y2={padding.top + innerH + 4}
              stroke="var(--neg)" strokeWidth="1.5" strokeDasharray="3 3" />
            <text x={x(baselineMark)} y={padding.top - 8} textAnchor="middle" fontSize="10.5" fontWeight="600"
              fill="var(--neg)" fontFamily="var(--mono)">{baselineLabel || ("base " + xFormat(baselineMark))}</text>
          </g>
        )}
        <line x1={padding.left} x2={w - padding.right} y1={padding.top + innerH} y2={padding.top + innerH} stroke="var(--rule-strong)" strokeWidth="1" />
        {xTickVals.map((t, i) => (
          <text key={"xt" + i} x={x(t)} y={height - 12} textAnchor="middle" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">{xFormat(t)}</text>
        ))}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// HBarChart — barras horizontais (suporta negativos, eixo zero ao centro).
// Usado nas correlações driver→VAL do Monte Carlo.
// ---------------------------------------------------------------------------
function HBarChart({ items, height, padding = { top: 8, right: 64, bottom: 8, left: 180 }, valueFormat = (v) => (v >= 0 ? "+" : "") + v.toFixed(3), barColor }) {
  const [w, setW] = React.useState(640);
  const { containerRef, tip, onMove, onLeave } = useTooltip();
  React.useLayoutEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(es => { for (const e of es) setW(e.contentRect.width); });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const rowH = 26;
  const h = height || (items.length * rowH + padding.top + padding.bottom);
  const innerW = w - padding.left - padding.right;
  const maxAbs = Math.max(...items.map(it => Math.abs(it.value)), 0.1);
  const xZero = padding.left + innerW / 2;
  const sc = (v) => (v / maxAbs) * (innerW / 2);

  return (
    <div ref={containerRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={h} style={{ display: "block" }} onMouseLeave={onLeave}>
        <line x1={xZero} x2={xZero} y1={padding.top - 2} y2={h - padding.bottom + 2} stroke="var(--ink)" strokeWidth="1" />
        {items.map((it, i) => {
          const cy = padding.top + i * rowH + rowH / 2;
          const v = it.value;
          const bw = Math.abs(sc(v));
          const x0 = v >= 0 ? xZero : xZero - bw;
          const col = barColor ? barColor(v) : (v >= 0 ? "var(--pos)" : "var(--neg)");
          const handle = (e) => onMove(e, {
            title: it.label,
            rows: [{ label: "Pearson r", value: valueFormat(v), color: col, bold: true }],
          });
          return (
            <g key={i}>
              <text x={padding.left - 12} y={cy + 4} textAnchor="end" fontSize="12" fill="var(--ink)" fontFamily="var(--ui)">{it.label}</text>
              <rect x={x0} y={cy - 9} width={bw} height="18" fill={col} opacity="0.85"
                onMouseMove={handle} onMouseEnter={handle} style={{ cursor: "default" }} />
              <text x={v >= 0 ? xZero + bw + 6 : xZero - bw - 6} y={cy + 4}
                textAnchor={v >= 0 ? "start" : "end"} fontSize="11" fill="var(--ink)"
                fontFamily="var(--mono)" pointerEvents="none">{valueFormat(v)}</text>
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} containerWidth={w} />
    </div>
  );
}

Object.assign(window, { LineChart, BarChart, WaterfallChart, TornadoChart, Sparkline, Donut, StackedBar, HistogramChart, HBarChart, fmt, COL, useTooltip, ChartTooltip });
