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

import { RouteAucSweepChart } from "@/components/experiments/route-auc-curve"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { ROUTER_V1 } from "@/lib/experiments/router-v1"
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
      <div className="h-[300px] w-full p-1 md:p-2">
        {children}
      </div>
      <figcaption className="mt-3 text-sm leading-[1.5] text-[#555]">
        {title}
      </figcaption>
    </figure>
  )
}

export function RouterV2RouteAucCurve() {
  const curve = R.chart.routeCurve
  return (
    <RouteAucSweepChart
      id="fig-route-auc-curve"
      heading="How Route-AUC works"
      intro={
        <>
          Same django holdout as v1 (n={R.djangoN}). Left is “send everything
          to Opus.” Right is “send everything to Qwen.” A working router would
          bow above the dashed chance line; fusion does not.
        </>
      }
      n={R.djangoN}
      alwaysOpus={R.djangoAlwaysLarge}
      alwaysQwen={curve.router[curve.router.length - 1].rate}
      oracleCeiling={R.djangoOracle}
      both={curve.both}
      smallOnly={curve.smallOnly}
      oracle={curve.oracle}
      series={[
        {
          key: "v1",
          label: "v1 text, seed 0",
          color: "#7a8494",
          strokeDasharray: "4 3",
          points: ROUTER_V1.chart.routeCurve.router,
        },
        {
          key: "fusion",
          label: "v2 fusion, seed 0",
          color: "var(--chart-2)",
          points: curve.router,
        },
      ]}
      caption={
        <>
          Figure 2: <strong>Django holdout Route-AUC curve.</strong> Oracle AST
          fusion (seed 0 = 0.469; 3-seed mean {R.logistic.django.fusion.routeAuc}
          ) sits on the same chance line as v1 text (seed 0 = 0.445). Ranking
          quality only changes the path between always-Opus and always-Qwen —
          the endpoints are identical because they depend on labels, not the
          router.
        </>
      }
    />
  )
}

export function RouterV2Figures() {
  return (
    <div>
      <FigureFrame
        id="fig-route-auc"
        title={
          <>
            Figure 3: <strong>Logistic Route-AUC by split.</strong> Dashed line
            is the django ship bar (0.55). Fusion does not clear it; grouped
            fusion is the same 0.589 trap as v1.
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
            Figure 4: <strong>Logistic AUROC by split.</strong> Dashed line is
            the django ship bar (0.60). Fusion stays at chance; metrics-only
            is at or below chance.
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
