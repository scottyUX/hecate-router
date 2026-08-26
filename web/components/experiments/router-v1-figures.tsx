"use client"

import type { ReactNode } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts"

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { ROUTER_V1 as R } from "@/lib/experiments/router-v1"

const headConfig = {
  logistic: { label: "logistic", color: "var(--chart-2)" },
  mlp: { label: "MLP", color: "var(--chart-1)" },
} satisfies ChartConfig

const foldConfig = {
  routeAuc: { label: "Route-AUC", color: "var(--chart-2)" },
} satisfies ChartConfig

function FigureFrame({
  id,
  title,
  children,
}: {
  id: string
  title: ReactNode
  children: ReactNode
}) {
  return (
    <figure id={id} className="my-8 scroll-mt-8">
      <div className="h-[300px] w-full rounded-xl border border-[var(--paper-line)] bg-white/70 p-3 md:p-4">
        {children}
      </div>
      <figcaption className="mt-3 text-sm leading-[1.5] text-[#555]">
        {title}
      </figcaption>
    </figure>
  )
}

export function RouterV1Figures() {
  return (
    <div>
      <FigureFrame
        id="fig-v1-route-auc"
        title={
          <>
            Figure 1: <strong>H1 test, Route-AUC by split.</strong> Dashed line
            is the ship bar (0.55). Django holdout is confirmatory; grouped
            0.589 is the trap.
          </>
        }
      >
        <ChartContainer config={headConfig} className="h-full w-full aspect-auto">
          <BarChart data={[...R.chart.routeAuc]} accessibilityLayer>
            <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
            <XAxis dataKey="split" tickLine={false} axisLine={false} />
            <YAxis
              domain={[0.4, 0.8]}
              tickLine={false}
              axisLine={false}
              width={36}
              tickFormatter={(value: number) => value.toFixed(2)}
            />
            <ReferenceLine
              y={R.target.routeAuc}
              stroke="var(--paper-accent)"
              strokeDasharray="4 4"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="logistic" fill="var(--color-logistic)" radius={2} />
            <Bar dataKey="mlp" fill="var(--color-mlp)" radius={2} />
          </BarChart>
        </ChartContainer>
      </FigureFrame>

      <FigureFrame
        id="fig-v1-folds"
        title={
          <>
            Figure 2: <strong>Grouped 5-fold, logistic, seed 0.</strong> Django
            is 46% of the data and sits at chance. The 0.589 mean is that fold
            averaged against small noisy ones.
          </>
        }
      >
        <ChartContainer config={foldConfig} className="h-full w-full aspect-auto">
          <BarChart data={[...R.chart.folds]} accessibilityLayer>
            <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
            <XAxis dataKey="fold" tickLine={false} axisLine={false} interval={0} />
            <YAxis
              domain={[0.2, 1.0]}
              tickLine={false}
              axisLine={false}
              width={36}
              tickFormatter={(value: number) => value.toFixed(2)}
            />
            <ReferenceLine y={0.5} stroke="rgba(26,36,51,0.35)" strokeDasharray="3 3" />
            <ReferenceLine
              y={R.target.routeAuc}
              stroke="var(--paper-accent)"
              strokeDasharray="4 4"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="routeAuc" fill="var(--color-routeAuc)" radius={2} />
          </BarChart>
        </ChartContainer>
      </FigureFrame>
    </div>
  )
}
