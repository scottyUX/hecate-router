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
import { ROUTER_V2 as R } from "@/lib/experiments/router-v2"

const config = {
  text: { label: "v1 text", color: "var(--chart-1)" },
  fusion: { label: "v2 fusion", color: "var(--chart-2)" },
  metrics: { label: "v2 metrics-only", color: "var(--chart-5)" },
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

export function RouterV2Figures() {
  return (
    <div>
      <FigureFrame
        id="fig-route-auc"
        title={
          <>
            Figure 1: <strong>Logistic Route-AUC by arm and split.</strong> The
            dashed line is the django-holdout target (0.55). Grouped fusion
            looks like a win; django holdout does not move.
          </>
        }
      >
        <ChartContainer config={config} className="h-full w-full aspect-auto">
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
              y={R.target.djangoRouteAuc}
              stroke="var(--paper-accent)"
              strokeDasharray="4 4"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="text" fill="var(--color-text)" radius={2} />
            <Bar dataKey="fusion" fill="var(--color-fusion)" radius={2} />
            <Bar dataKey="metrics" fill="var(--color-metrics)" radius={2} />
          </BarChart>
        </ChartContainer>
      </FigureFrame>

      <FigureFrame
        id="fig-auroc"
        title={
          <>
            Figure 2: <strong>Logistic AUROC by arm and split.</strong> The
            dashed line is the django-holdout target (0.60). All arms sit at
            chance on holdout (~0.52).
          </>
        }
      >
        <ChartContainer config={config} className="h-full w-full aspect-auto">
          <BarChart data={[...R.chart.auroc]} accessibilityLayer>
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
              y={R.target.djangoAuroc}
              stroke="var(--paper-accent)"
              strokeDasharray="4 4"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="text" fill="var(--color-text)" radius={2} />
            <Bar dataKey="fusion" fill="var(--color-fusion)" radius={2} />
            <Bar dataKey="metrics" fill="var(--color-metrics)" radius={2} />
          </BarChart>
        </ChartContainer>
      </FigureFrame>
    </div>
  )
}
