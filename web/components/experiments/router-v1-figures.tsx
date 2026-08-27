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
  tall,
}: {
  id: string
  title: ReactNode
  children: ReactNode
  tall?: boolean
}) {
  return (
    <figure id={id} className="my-8 scroll-mt-8">
      <div className={tall ? "p-0" : "h-[300px] w-full p-1 md:p-2"}>{children}</div>
      <figcaption className="mt-3 text-sm leading-[1.5] text-[#555]">
        {title}
      </figcaption>
    </figure>
  )
}

export function RouterV1RouteAucCurve() {
  const curve = R.chart.routeCurve
  return (
    <RouteAucSweepChart
      id="fig-route-auc-curve"
      heading="How Route-AUC works"
      intro={
        <>
          Left is “send everything to Opus.” Right is “send everything to
          Qwen.” Oracle stays at {(R.djangoAlwaysLarge * 100).toFixed(1)}% until
          the {curve.both} both-win tasks are routed — free savings — then
          briefly rises to {(R.djangoOracle * 100).toFixed(1)}% on the{" "}
          {curve.smallOnly} Qwen-only tasks.
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
          key: "router",
          label: "v1 logistic, seed 0",
          color: "var(--chart-2)",
          points: curve.router,
        },
      ]}
      caption={
        <>
          Figure 2: <strong>Django holdout Route-AUC curve.</strong> Sweeping
          the cheap/expensive threshold traces resolved rate versus the share
          sent to Qwen. Normalized Route-AUC is how much of the band between
          the dashed chance line and the oracle ceiling that curve captures
          (0.5 is chance). Seed 0 sits at 0.445; the 3-seed mean is{" "}
          {R.logistic.django.routeAuc}. The curve wobbles around the no-signal
          diagonal rather than bowing above it.
        </>
      }
    />
  )
}

export function RouterV1Figures() {
  return (
    <div>
      <FigureFrame
        id="fig-v1-route-auc"
        title={
          <>
            Figure 3: <strong>Route-AUC by split.</strong> Dashed line is the
            ship bar (0.55). Django holdout is the real test; grouped 0.589 is
            the trap.
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
            Figure 4: <strong>Grouped 5-fold, logistic, seed 0.</strong> Django
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
