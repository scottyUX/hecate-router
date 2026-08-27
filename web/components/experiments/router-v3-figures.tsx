"use client"

import type { ReactNode } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  LabelList,
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
import { ROUTER_V3 as R } from "@/lib/experiments/router-v3"

const config = {
  text: { label: "v1 text", color: "var(--chart-1)" },
  fusion: { label: "v2 fusion", color: "#7a8494" },
  k0: { label: "K=0 LoRA", color: "#128f8b" },
  k3: { label: "K=3 LoRA", color: "var(--chart-2)" },
} satisfies ChartConfig

type GroupedRow = {
  split: string
  text: number
  textCi: number
  fusion: number
  fusionCi: number
  k0: number
  k3: number
}

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
      <div className="p-0">
        {children}
      </div>
      <figcaption className="mt-3 text-sm leading-[1.5] text-[#555]">
        {title}
      </figcaption>
    </figure>
  )
}

function fmt3(value: unknown) {
  return typeof value === "number" ? value.toFixed(3) : ""
}

function DjangoCluster({
  title,
  subtitle,
  data,
  domain,
  ticks,
  refs,
  labelK0,
  labelK3,
}: {
  title: string
  subtitle: string
  data: readonly GroupedRow[]
  domain: [number, number]
  ticks: number[]
  refs: { y: number; label: string }[]
  labelK0?: boolean
  labelK3?: boolean
}) {
  return (
    <div>
      <p className="text-[13px] font-medium text-[var(--paper-ink)]">{title}</p>
      <p className="mb-1 text-[11px] text-[var(--paper-muted)]">{subtitle}</p>
      <ChartContainer
        config={config}
        className="mx-auto h-[240px] w-full max-w-[340px] aspect-auto"
      >
        <BarChart
          data={[...data]}
          accessibilityLayer
          barGap={4}
          barCategoryGap="22%"
          maxBarSize={48}
          margin={{ top: 24, right: 8, left: 0, bottom: 4 }}
        >
          <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
          <XAxis dataKey="split" hide />
          <YAxis
            domain={domain}
            ticks={ticks}
            tickLine={false}
            axisLine={false}
            width={32}
            tickFormatter={(value: number) => value.toFixed(2)}
          />
          {refs.map((line) => (
            <ReferenceLine
              key={line.label}
              y={line.y}
              stroke="rgba(26,36,51,0.35)"
              strokeDasharray="4 4"
              label={{
                value: line.label,
                position: "insideTopRight",
                fill: "var(--paper-muted)",
                fontSize: 10,
              }}
            />
          ))}
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="text" fill="var(--color-text)" radius={2}>
            <ErrorBar dataKey="textCi" width={6} stroke="#c4c9d1" />
          </Bar>
          <Bar dataKey="fusion" fill="var(--color-fusion)" radius={2}>
            <ErrorBar dataKey="fusionCi" width={6} stroke="#c4c9d1" />
          </Bar>
          <Bar dataKey="k0" fill="var(--color-k0)" radius={2}>
            {labelK0 ? (
              <LabelList
                dataKey="k0"
                position="top"
                formatter={fmt3}
                className="fill-[var(--paper-ink)] text-[10px] font-medium"
              />
            ) : null}
          </Bar>
          <Bar dataKey="k3" fill="var(--color-k3)" radius={2}>
            {labelK3 ? (
              <LabelList
                dataKey="k3"
                position="top"
                formatter={fmt3}
                className="fill-[var(--paper-ink)] text-[10px] font-medium"
              />
            ) : null}
          </Bar>
        </BarChart>
      </ChartContainer>
    </div>
  )
}

function deltaLabel(start: number, end: number) {
  const d = end - start
  const sign = d > 0 ? "+" : ""
  return `${sign}${d.toFixed(3)}`
}

function SlopeTable({
  rows,
}: {
  rows: {
    run: string
    k0: number
    later: number | null
    laterLabel: string
  }[]
}) {
  return (
    <table className="w-full border-collapse font-sans text-[13px] leading-[1.4]">
      <thead>
        <tr className="border-b border-[var(--paper-ink)]/70">
          <th className="py-1 pr-3 text-left font-medium">Run</th>
          <th className="px-2 py-1 text-right font-medium tabular-nums">K=0</th>
          <th className="px-2 py-1 text-right font-medium">Later K</th>
          <th className="py-1 pl-3 text-right font-medium">Change</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const later = row.later
          const down = later != null && later < row.k0
          const up = later != null && later > row.k0
          return (
            <tr key={row.run} className="border-b border-[var(--paper-line)]">
              <td className="py-1.5 pr-3">{row.run}</td>
              <td className="px-2 py-1.5 text-right tabular-nums">
                {row.k0.toFixed(3)}
              </td>
              <td className="px-2 py-1.5 text-right tabular-nums">
                {later == null ? (
                  <span className="text-[var(--paper-muted)]">
                    {row.laterLabel}
                  </span>
                ) : (
                  later.toFixed(3)
                )}
              </td>
              <td
                className={`py-1.5 pl-3 text-right tabular-nums ${
                  down
                    ? "text-[#9a3b2f]"
                    : up
                      ? "text-[#128f8b]"
                      : "text-[var(--paper-muted)]"
                }`}
              >
                {later == null
                  ? "—"
                  : `${down ? "falls" : "rises"} ${deltaLabel(row.k0, later)}`}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export function RouterV3Figures() {
  const yTicks = [0.4, 0.5, 0.6, 0.7]
  return (
    <div>
      <FigureFrame
        id="fig-k0-django"
        title={
          <>
            Figure 2: <strong>K=0 vs K=3 vs the frozen floor, django holdout.</strong>{" "}
            Compact grouped columns (v1 / v2 fusion / K=0 LoRA / K=3 LoRA). The
            three higher-is-better panels share y ∈ [0.40, 0.75] so Route-AUC’s
            K=0 jump and K=3 drop are readable against AUROC and accuracy. Teal
            is K=0, blue is K=3 (one seed each, no CI); gray bars are
            established 3-seed arms with error bars.
          </>
        }
      >
        <div className="mb-4 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[var(--paper-muted)]">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-3 rounded-sm bg-[var(--chart-1)]" />
            v1 text
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-3 rounded-sm bg-[#7a8494]" />
            v2 fusion
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-3 rounded-sm bg-[#128f8b]" />
            K=0 LoRA (1 seed)
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-3 rounded-sm bg-[var(--chart-2)]" />
            K=3 LoRA (1 seed)
          </span>
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          <DjangoCluster
            title="Route-AUC"
            subtitle="primary gate — 0.5 = chance"
            data={R.chart.routeAuc}
            domain={[0.4, 0.75]}
            ticks={yTicks}
            refs={[
              { y: 0.5, label: "chance" },
              { y: R.stretch.djangoRouteAuc, label: "H2 0.55" },
            ]}
            labelK0
            labelK3
          />
          <DjangoCluster
            title="AUROC"
            subtitle="diagnostic — do not gate"
            data={R.chart.auroc}
            domain={[0.4, 0.75]}
            ticks={yTicks}
            refs={[
              { y: 0.5, label: "chance" },
              { y: R.stretch.djangoAuroc, label: "v1 target" },
            ]}
          />
          <DjangoCluster
            title="Accuracy"
            subtitle="threshold 0.5"
            data={R.chart.accuracy}
            domain={[0.4, 0.75]}
            ticks={yTicks}
            refs={[{ y: R.djangoAlwaysSmall, label: "always-Qwen" }]}
          />
          <DjangoCluster
            title="Brier score"
            subtitle="lower is better"
            data={R.chart.brier}
            domain={[0.22, 0.45]}
            ticks={[0.22, 0.26, 0.3, 0.34, 0.38, 0.42]}
            refs={[{ y: 0.25, label: "const-0.5" }]}
            labelK3
          />
        </div>
      </FigureFrame>

      <FigureFrame
        id="fig-swe-router"
        title={
          <>
            Figure 3: <strong>Does extra trajectory help?</strong> Route-AUC
            from K=0 (issue text only) to a later K. Same LoRA value-head
            idea, different model pairs and datasets — a reference, not a
            replication. Hecate K=3 falls 0.099 vs K=0 on django holdout.
          </>
        }
      >
        <p className="mb-4 font-sans text-[13px] leading-[1.45] text-[var(--paper-ink)]">
          Extra turns help when train and test share the same mix. They do not
          when the test repo is held out.
        </p>
        <div className="space-y-5">
          <div>
            <p className="mb-1.5 font-sans text-[12px] font-medium text-[var(--paper-ink)]">
              Repo held out — extra turns fail
            </p>
            <SlopeTable
              rows={[
                {
                  run: "Hecate django (this pair)",
                  k0: R.k0.routeAuc,
                  later: R.k3.routeAuc,
                  laterLabel: "K=3",
                },
                {
                  run: "SWE-Router gpt-5-mini, SWE-Smith",
                  k0: R.sweRouter.smithRepoDisjoint.gpt5mini.k0,
                  later: R.sweRouter.smithRepoDisjoint.gpt5mini.k3,
                  laterLabel: "K=3",
                },
                {
                  run: "SWE-Router deepseek, SWE-Smith",
                  k0: R.sweRouter.smithRepoDisjoint.deepseek.k0,
                  later: R.sweRouter.smithRepoDisjoint.deepseek.k3,
                  laterLabel: "K=3",
                },
              ]}
            />
          </div>
          <div>
            <p className="mb-1.5 font-sans text-[12px] font-medium text-[var(--paper-ink)]">
              Same mix as training — extra turns help
            </p>
            <SlopeTable
              rows={[
                {
                  run: "SWE-Router gpt-5-mini, mix-1",
                  k0: R.sweRouter.mix1.gpt5mini.k0,
                  later: R.sweRouter.mix1.gpt5mini.k4,
                  laterLabel: "K=4",
                },
                {
                  run: "SWE-Router deepseek, mix-1",
                  k0: R.sweRouter.mix1.deepseek.k0,
                  later: R.sweRouter.mix1.deepseek.k2,
                  laterLabel: "K=2",
                },
              ]}
            />
          </div>
        </div>
      </FigureFrame>
    </div>
  )
}
