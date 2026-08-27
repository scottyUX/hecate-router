"use client"

import type { ReactNode } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts"

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

export type RouteAucPoint = { cheap: number; rate: number }

export type RouteAucSeries = {
  key: string
  label: string
  color: string
  strokeDasharray?: string
  points: readonly RouteAucPoint[]
}

type Xy = { cheap: number; rate: number }

function interp(x: number, pts: readonly Xy[]): number {
  if (pts.length === 0) return 0
  if (x <= pts[0].cheap) return pts[0].rate
  const last = pts[pts.length - 1]
  if (x >= last.cheap) return last.rate
  for (let i = 1; i < pts.length; i += 1) {
    const a = pts[i - 1]
    const b = pts[i]
    if (x <= b.cheap) {
      const w = b.cheap - a.cheap
      if (w <= 0) return b.rate
      return a.rate + ((x - a.cheap) / w) * (b.rate - a.rate)
    }
  }
  return last.rate
}

function sorted(pts: readonly RouteAucPoint[]): RouteAucPoint[] {
  return [...pts].sort((a, b) => a.cheap - b.cheap)
}

export function RouteAucSweepChart({
  id,
  heading,
  intro,
  caption,
  n,
  alwaysOpus,
  alwaysQwen,
  oracleCeiling,
  both,
  smallOnly,
  oracle,
  series,
}: {
  id: string
  heading: string
  intro?: ReactNode
  caption: ReactNode
  n: number
  alwaysOpus: number
  alwaysQwen: number
  oracleCeiling: number
  both: number
  smallOnly: number
  oracle: readonly RouteAucPoint[]
  series: readonly RouteAucSeries[]
}) {
  const oraclePts = sorted(oracle)
  const seriesPts = series.map((item) => ({
    ...item,
    points: sorted(item.points),
  }))
  const xs = [
    ...new Set(
      [
        ...oraclePts.map((p) => p.cheap),
        ...seriesPts.flatMap((item) => item.points.map((p) => p.cheap)),
      ].map((v) => Math.round(v * 1e6) / 1e6)
    ),
  ].sort((a, b) => a - b)
  const data = xs.map((cheap) => {
    const row: Record<string, number> = {
      cheap,
      oracle: interp(cheap, oraclePts),
      chance: alwaysOpus + cheap * (alwaysQwen - alwaysOpus),
    }
    for (const item of seriesPts) {
      row[item.key] = interp(cheap, item.points)
    }
    return row
  })
  const config = {
    oracle: { label: "Oracle (perfect ranking)", color: "#128f8b" },
    chance: { label: "No signal (random ranking)", color: "#7a8494" },
    ...Object.fromEntries(
      seriesPts.map((item) => [item.key, { label: item.label, color: item.color }])
    ),
  } satisfies ChartConfig
  const freeSave = both / n

  return (
    <figure id={id} className="my-8 scroll-mt-8">
      <p className="mb-2 font-sans text-[13px] font-medium text-[var(--paper-ink)]">
        {heading}
      </p>
      {intro ? (
        <p className="mb-3 font-sans text-[12px] leading-[1.45] text-[var(--paper-muted)]">
          {intro}
        </p>
      ) : null}
      <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 font-sans text-[11px] text-[var(--paper-muted)]">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-[#128f8b]" />
          Oracle (perfect ranking)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-px w-4 border-t border-dashed border-[#7a8494]" />
          No signal (random ranking)
        </span>
        {seriesPts.map((item) => (
          <span key={item.key} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-0.5 w-4"
              style={{
                background: item.strokeDasharray ? "transparent" : item.color,
                borderTop: item.strokeDasharray
                  ? `1.5px dashed ${item.color}`
                  : undefined,
              }}
            />
            {item.label}
          </span>
        ))}
      </div>
      <ChartContainer config={config} className="h-[320px] w-full aspect-auto">
        <LineChart
          data={data}
          accessibilityLayer
          margin={{ top: 8, right: 16, left: 8, bottom: 28 }}
        >
          <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
          <XAxis
            type="number"
            dataKey="cheap"
            domain={[0, 1]}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
            label={{
              value: "Share of tasks routed to the cheap model (Qwen)",
              position: "insideBottom",
              offset: -4,
              style: { fill: "var(--paper-muted)", fontSize: 11 },
            }}
          />
          <YAxis
            domain={[0.54, 0.76]}
            ticks={[0.54, 0.58, 0.62, 0.66, 0.7, 0.74]}
            tickLine={false}
            axisLine={false}
            width={40}
            tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
            label={{
              value: "Overall resolved rate",
              angle: -90,
              position: "insideLeft",
              offset: 8,
              style: { fill: "var(--paper-muted)", fontSize: 11 },
            }}
          />
          <ReferenceLine
            x={freeSave}
            stroke="rgba(26,36,51,0.25)"
            strokeDasharray="3 3"
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(value) =>
                  `${Math.round(Number(value) * 100)}% cheap`
                }
              />
            }
          />
          <Line
            type="linear"
            dataKey="oracle"
            stroke="var(--color-oracle)"
            strokeWidth={2}
            dot={false}
            name="oracle"
          />
          <Line
            type="linear"
            dataKey="chance"
            stroke="var(--color-chance)"
            strokeWidth={1.5}
            strokeDasharray="5 4"
            dot={false}
            name="chance"
          />
          {seriesPts.map((item) => (
            <Line
              key={item.key}
              type="linear"
              dataKey={item.key}
              stroke={`var(--color-${item.key})`}
              strokeWidth={2}
              strokeDasharray={item.strokeDasharray}
              dot={false}
              name={item.key}
            />
          ))}
          <ReferenceDot
            x={0}
            y={alwaysOpus}
            r={3}
            fill="var(--paper-ink)"
            stroke="none"
          />
          <ReferenceDot
            x={1}
            y={alwaysQwen}
            r={3}
            fill="var(--paper-ink)"
            stroke="none"
          />
        </LineChart>
      </ChartContainer>
      <p className="mt-1 font-sans text-[11px] leading-[1.4] text-[var(--paper-muted)]">
        Always-Opus (0% cheap): {(alwaysOpus * 100).toFixed(1)}%. Always-Qwen
        (100% cheap): {(alwaysQwen * 100).toFixed(1)}%. Oracle ceiling:{" "}
        {(oracleCeiling * 100).toFixed(1)}% after the {smallOnly} Qwen-only
        tasks. Vertical mark: free savings end at {(freeSave * 100).toFixed(0)}%
        cheap ({both} both-win tasks).
      </p>
      <figcaption className="mt-3 text-sm leading-[1.5] text-[#555]">
        {caption}
      </figcaption>
    </figure>
  )
}
