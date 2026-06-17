"use client";

import { type SmcData } from "../lib/api";

const N = 120; // visible candles
const W = 1000;
const H = 440;
const PADL = 8;
const PADR = 64;
const PADT = 12;
const PADB = 12;

export default function SMCChart({ data }: { data: SmcData }) {
  const candles = data.candles.slice(-N);
  if (candles.length < 2) return null;

  const times = candles.map((c) => c.t);
  const min = Math.min(...candles.map((c) => c.l));
  const max = Math.max(...candles.map((c) => c.h));
  const range = max - min || 1;

  const plotW = W - PADL - PADR;
  const plotH = H - PADT - PADB;
  const step = plotW / candles.length;
  const bodyW = Math.max(1.5, step * 0.6);

  const x = (i: number) => PADL + i * step + step / 2;
  const y = (p: number) => PADT + ((max - p) / range) * plotH;
  const idx = (t: string) => {
    const i = times.indexOf(t);
    if (i >= 0) return i;
    return t < times[0] ? 0 : null; // anchor older zones to left edge
  };

  const fg = "var(--color-forest)";
  const br = "var(--color-brick)";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: "auto" }}>
      {/* price gridlines */}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => {
        const p = max - f * range;
        return (
          <g key={f}>
            <line
              x1={PADL} x2={W - PADR} y1={y(p)} y2={y(p)}
              stroke="var(--color-line)" strokeWidth="1"
            />
            <text x={W - PADR + 4} y={y(p) + 3} fontSize="10" fill="var(--color-sage)">
              {p.toFixed(p > 1000 ? 0 : 2)}
            </text>
          </g>
        );
      })}

      {/* order blocks — two-layer zone to the right edge */}
      {data.order_blocks.map((ob, n) => {
        const i = idx(ob.t);
        if (i === null) return null;
        const col = ob.type === "bull" ? fg : br;
        const yt = y(ob.top), yb = y(ob.bottom);
        const x0 = x(i) - bodyW / 2;
        return (
          <g key={`ob${n}`}>
            <rect x={x0} y={yt} width={W - PADR - x0} height={yb - yt} fill={col} opacity="0.07" />
            <rect x={x0} y={yt} width={W - PADR - x0} height={yb - yt} fill="none" stroke={col} strokeWidth="1" opacity="0.4" strokeDasharray="2 2" />
            <text x={W - PADR - 2} y={yt + 9} fontSize="8" textAnchor="end" fill={col} opacity="0.8">
              {ob.type === "bull" ? "Bull OB" : "Bear OB"}
            </text>
          </g>
        );
      })}

      {/* fair value gaps — short tinted bands */}
      {data.fvgs.map((f, n) => {
        const i = idx(f.t);
        if (i === null) return null;
        const col = f.type === "bull" ? fg : br;
        const yt = y(f.top), yb = y(f.bottom);
        const x0 = x(i) - bodyW / 2;
        const w = Math.min(step * 5, W - PADR - x0);
        return <rect key={`fvg${n}`} x={x0} y={yt} width={w} height={Math.max(1, yb - yt)} fill={col} opacity="0.16" />;
      })}

      {/* candles */}
      {candles.map((c, i) => {
        const up = c.c >= c.o;
        const col = up ? fg : br;
        const cx = x(i);
        const yo = y(c.o), yc = y(c.c);
        const top = Math.min(yo, yc);
        const hgt = Math.max(1, Math.abs(yc - yo));
        return (
          <g key={i}>
            <line x1={cx} x2={cx} y1={y(c.h)} y2={y(c.l)} stroke={col} strokeWidth="1" />
            <rect x={cx - bodyW / 2} y={top} width={bodyW} height={hgt} fill={col} />
          </g>
        );
      })}

      {/* buy/sell signals */}
      {data.signals.map((s, n) => {
        const i = idx(s.t);
        if (i === null) return null;
        const cx = x(i);
        const buy = s.side === "BUY";
        const py = buy ? y(s.price) + 14 : y(s.price) - 14;
        const tri = buy
          ? `${cx},${py - 7} ${cx - 5},${py + 3} ${cx + 5},${py + 3}`
          : `${cx},${py + 7} ${cx - 5},${py - 3} ${cx + 5},${py - 3}`;
        return (
          <g key={`sig${n}`}>
            <polygon points={tri} fill={buy ? fg : br} />
            <text x={cx} y={buy ? py + 14 : py - 9} fontSize="8" textAnchor="middle" fill={buy ? fg : br}>
              {s.side}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
