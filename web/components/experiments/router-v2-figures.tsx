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
  title: string
  children: ReactNode
}) {
  return (
    <figure id={id} className="scroll-mt-24 rounded-2xl border border-border bg-card p-4 md:p-5">
      <div className="h-[280px] w-full">{children}</div>
      <figcaption className="mt-4 text-sm leading-relaxed text-muted-foreground">
        {title}
      </figcaption>
    </figure>
  )
}

export function RouterV2Figures() {
  return (
    <div className="space-y-6">
      <FigureFrame
        id="fig-route-auc"
        title="Figure 1. Logistic Route-AUC by arm and split. Dashed line is the django target (0.55). Grouped fusion looks like a win; django holdout does not move."
      >
        <ChartContainer config={config} className="h-full w-full aspect-auto">
          <BarChart data={[...R.chart.routeAuc]} accessibilityLayer>
            <CartesianGrid vertical={false} />
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
              stroke="var(--destructive)"
              strokeDasharray="4 4"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="text" fill="var(--color-text)" radius={4} />
            <Bar dataKey="fusion" fill="var(--color-fusion)" radius={4} />
            <Bar dataKey="metrics" fill="var(--color-metrics)" radius={4} />
          </BarChart>
        </ChartContainer>
      </FigureFrame>

      <FigureFrame
        id="fig-auroc"
        title="Figure 2. Logistic AUROC by arm and split. Dashed line is the django target (0.60). All arms sit at chance on holdout (~0.52)."
      >
        <ChartContainer config={config} className="h-full w-full aspect-auto">
          <BarChart data={[...R.chart.auroc]} accessibilityLayer>
            <CartesianGrid vertical={false} />
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
              stroke="var(--destructive)"
              strokeDasharray="4 4"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <ChartLegend content={<ChartLegendContent />} />
            <Bar dataKey="text" fill="var(--color-text)" radius={4} />
            <Bar dataKey="fusion" fill="var(--color-fusion)" radius={4} />
            <Bar dataKey="metrics" fill="var(--color-metrics)" radius={4} />
          </BarChart>
        </ChartContainer>
      </FigureFrame>
    </div>
  )
}
