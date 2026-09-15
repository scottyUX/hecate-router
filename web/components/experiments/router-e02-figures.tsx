"use client"

import type { ReactNode } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  ReferenceLine,
  Scatter,
  ScatterChart,
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
import { ROUTER_E02 as R } from "@/lib/experiments/router-e02"

const metricConfig = {
  routeAuc: { label: "Route-AUC (primary)", color: "var(--chart-2)" },
  auroc: { label: "AUROC (diagnostic)", color: "var(--chart-1)" },
} satisfies ChartConfig

const valConfig = {
  k0: { label: "B K=0", color: "var(--chart-1)" },
  k1: { label: "D K=1", color: "#2a6f97" },
  k3: { label: "C K=3", color: "#b4532a" },
} satisfies ChartConfig

const holdConfig = {
  both: { label: "Both solve it", color: "#2a6f97" },
  opusOnly: { label: "Opus-only", color: "#c45c26" },
  neither: { label: "Neither", color: "#b0892e" },
  qwenOnly: { label: "Qwen-only", color: "#2f7d4a" },
} satisfies ChartConfig

const routeConfig = {
  opus: { label: "Sent to Opus", color: "#c45c26" },
  qwen: { label: "Sent to Qwen", color: "#2f7d4a" },
} satisfies ChartConfig

const paretoConfig = {
  k0: { label: "B K=0", color: "var(--chart-1)" },
  k1: { label: "D K=1", color: "#2a6f97" },
  k3: { label: "C K=3", color: "#b4532a" },
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
      <div className="p-0">{children}</div>
      <figcaption className="mt-3 font-sans text-sm leading-[1.5] text-[var(--paper-muted)]">
        {title}
      </figcaption>
    </figure>
  )
}

function Panel({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <div className="mb-3">
      <p className="font-sans text-[13px] font-medium text-[var(--paper-ink)]">
        {title}
      </p>
      {children}
    </div>
  )
}

export function RouterE02HoldoutBar() {
  const data = [
    {
      name: "holdout",
      both: R.hold.both,
      opusOnly: R.hold.largeOnly,
      neither: R.hold.neither,
      qwenOnly: R.hold.smallOnly,
    },
  ]
  return (
    <FigureFrame
      id="fig-holdout"
      title={
        <>
          Figure 1: <strong>What the 46 holdout tasks look like.</strong> Opus
          already resolves 33/46 — that is the quality bar below. A router can
          only save calls on the 23 both-win tasks; the 10 Opus-only tasks must
          still go to Opus to keep that bar.
        </>
      }
    >
      <Panel title="Holdout complementarity (n=46)">
        <ChartContainer
          config={holdConfig}
          className="mx-auto h-[120px] w-full aspect-auto"
        >
          <BarChart
            data={data}
            layout="vertical"
            accessibilityLayer
            margin={{ top: 8, right: 12, left: 4, bottom: 8 }}
          >
            <XAxis type="number" domain={[0, 46]} ticks={[0, 23, 33, 46]} />
            <YAxis type="category" dataKey="name" hide />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="both" stackId="h" fill="var(--color-both)" maxBarSize={28}>
              <LabelList dataKey="both" position="inside" fill="#fff" fontSize={11} />
            </Bar>
            <Bar dataKey="opusOnly" stackId="h" fill="var(--color-opusOnly)" maxBarSize={28}>
              <LabelList dataKey="opusOnly" position="inside" fill="#fff" fontSize={11} />
            </Bar>
            <Bar dataKey="neither" stackId="h" fill="var(--color-neither)" maxBarSize={28}>
              <LabelList dataKey="neither" position="inside" fill="#fff" fontSize={11} />
            </Bar>
            <Bar dataKey="qwenOnly" stackId="h" fill="var(--color-qwenOnly)" maxBarSize={28}>
              <LabelList dataKey="qwenOnly" position="inside" fill="#fff" fontSize={11} />
            </Bar>
          </BarChart>
        </ChartContainer>
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-sans text-[12px] text-[var(--paper-muted)]">
          <li>
            <span className="mr-1 inline-block size-2 rounded-sm bg-[#2a6f97]" />
            Both — {R.hold.both}
          </li>
          <li>
            <span className="mr-1 inline-block size-2 rounded-sm bg-[#c45c26]" />
            Opus-only — {R.hold.largeOnly}
          </li>
          <li>
            <span className="mr-1 inline-block size-2 rounded-sm bg-[#b0892e]" />
            Neither — {R.hold.neither}
          </li>
          <li>
            <span className="mr-1 inline-block size-2 rounded-sm bg-[#2f7d4a]" />
            Qwen-only — {R.hold.smallOnly}
          </li>
        </ul>
      </Panel>
    </FigureFrame>
  )
}

export function RouterE02CallsScatter() {
  const refs = [
    { calls: 0, hits: R.hold.alwaysSmall, label: "Always-Qwen" },
    { calls: R.hold.oracleOpusCalls, hits: R.hold.oracle, label: "Oracle (max)" },
    {
      calls: R.hold.oracleOpusCalls,
      hits: R.hold.alwaysLarge,
      label: "Oracle (match 33)",
    },
  ]
  const trained = [
    { calls: R.k1.opusCallsAt33, hits: R.k1.successesAtBest, label: "D K=1" },
    {
      calls: R.k0.opusCallsAt33,
      hits: R.k0.successesAtBest,
      label: "A / B / always-Opus",
    },
  ]
  const provisional = [
    {
      calls: R.k3.opusCallsAtMax,
      hits: R.k3.maxSuccesses,
      label: "C K=3",
    },
  ]

  return (
    <FigureFrame
      id="fig-calls"
      title={
        <>
          Figure 2: <strong>Opus calls vs quality.</strong> X is how many of
          the 46 go to Opus; Y is how many resolve. The dashed line is
          always-Opus quality (33). Anything on that line with fewer than 46
          calls is a real cost win. A, B, and always-Opus sit on the same
          point (46, 33). D is the only trained arm on the line that is not
          46. C is below the line (32 successes, 45 calls) and is the overfit
          checkpoint.
        </>
      }
    >
      <ChartContainer
        config={paretoConfig}
        className="mx-auto h-[340px] w-full max-w-[640px] aspect-auto"
      >
        <ScatterChart margin={{ top: 16, right: 88, left: 8, bottom: 28 }}>
          <CartesianGrid stroke="rgba(26,36,51,0.08)" />
          <XAxis
            type="number"
            dataKey="calls"
            name="Opus calls"
            domain={[0, 48]}
            ticks={[0, 10, 20, 26, 33, 46]}
            label={{
              value: "Opus calls (of 46 holdout tasks)",
              position: "bottom",
              offset: 8,
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="hits"
            name="Successes"
            domain={[24, 39]}
            ticks={[27, 33, 37]}
            width={40}
            label={{
              value: "Successes (of 46)",
              angle: -90,
              position: "insideLeft",
              fontSize: 11,
            }}
          />
          <ReferenceLine
            y={R.hold.alwaysLarge}
            stroke="rgba(26,36,51,0.45)"
            strokeDasharray="4 4"
            label={{
              value: "same quality as always-Opus",
              position: "insideTopLeft",
              fontSize: 10,
              fill: "var(--paper-muted)",
            }}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Scatter name="Reference" data={refs} fill="#7a8494">
            <LabelList dataKey="label" position="right" fontSize={10} />
          </Scatter>
          <Scatter name="Trained" data={trained} fill="var(--chart-2)">
            <LabelList dataKey="label" position="top" fontSize={10} />
          </Scatter>
          <Scatter name="C (provisional)" data={provisional} fill="#b4532a">
            <LabelList dataKey="label" position="bottom" fontSize={10} />
          </Scatter>
        </ScatterChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02MetricBars() {
  const data = [
    {
      arm: "A frozen",
      routeAuc: Number(R.frozen.routeAuc.toFixed(3)),
      auroc: Number(R.frozen.auroc.toFixed(3)),
    },
    {
      arm: "B K=0",
      routeAuc: Number(R.k0.routeAuc.toFixed(3)),
      auroc: Number(R.k0.auroc.toFixed(3)),
    },
    {
      arm: "D K=1",
      routeAuc: Number(R.k1.routeAuc.toFixed(3)),
      auroc: Number(R.k1.auroc.toFixed(3)),
    },
    {
      arm: "C K=3",
      routeAuc: Number(R.k3.routeAuc.toFixed(3)),
      auroc: Number(R.k3.auroc.toFixed(3)),
    },
  ]
  return (
    <FigureFrame
      id="fig-metrics"
      title={
        <>
          Figure 3: <strong>Route-AUC by arm, against AUROC.</strong>{" "}
          Route-AUC (teal) is the pre-registered primary — how well scores
          rank tasks for the cheap/expensive sweep. AUROC (grey) is
          diagnostic only; it has already moved independently of routing
          quality on this project. Q2.1 is B vs A (+0.109, not a pass at
          n=46). Q2.2 is C vs B (+0.092) from C’s overfit checkpoint. Q2.3
          is D vs B (+0.143) and cannot headline.
        </>
      }
    >
      <ChartContainer
        config={metricConfig}
        className="mx-auto h-[300px] w-full max-w-[640px] aspect-auto"
      >
        <BarChart
          data={data}
          accessibilityLayer
          barGap={4}
          barCategoryGap="22%"
          margin={{ top: 24, right: 8, left: 0, bottom: 4 }}
        >
          <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
          <XAxis dataKey="arm" tickLine={false} axisLine={false} />
          <YAxis
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <ReferenceLine y={0.5} stroke="rgba(26,36,51,0.25)" strokeDasharray="3 3" />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="routeAuc" fill="var(--color-routeAuc)" radius={3} maxBarSize={36}>
            <LabelList dataKey="routeAuc" position="top" fontSize={11} />
          </Bar>
          <Bar dataKey="auroc" fill="var(--color-auroc)" radius={3} maxBarSize={36}>
            <LabelList dataKey="auroc" position="top" fontSize={11} />
          </Bar>
        </BarChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02ValCe() {
  const data = R.k0.valCe.map((k0, index) => ({
    epoch: index + 1,
    k0,
    k1: R.k1.valCe[index],
    k3: R.k3.valCe[index],
  }))
  return (
    <FigureFrame
      id="fig-valce"
      title={
        <>
          Figure 4: <strong>Why C’s number is provisional.</strong> Validation
          cross-entropy on the 20-task monitor slice, all five epochs. C packs
          K=0..4 so it sees about 5× as many optimizer steps as B in the same
          epoch budget. Early stopping was off, so C trained through its best
          checkpoint (epoch 2, 0.637) to epoch 5 (2.902). The reported
          Route-AUC 0.574 is that final checkpoint. B stays flat; D rises only
          late. This is why the next run turns early stopping on for B, C, and
          D together, not C alone.
        </>
      }
    >
      <ChartContainer
        config={valConfig}
        className="mx-auto h-[300px] w-full max-w-[640px] aspect-auto"
      >
        <LineChart data={data} margin={{ top: 16, right: 16, left: 4, bottom: 8 }}>
          <CartesianGrid stroke="rgba(26,36,51,0.08)" />
          <XAxis dataKey="epoch" ticks={[1, 2, 3, 4, 5]} />
          <YAxis domain={[0, 3.2]} ticks={[0, 0.7, 1.5, 2.9]} width={36} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Line
            type="monotone"
            dataKey="k0"
            stroke="var(--color-k0)"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="k1"
            stroke="var(--color-k1)"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="k3"
            stroke="var(--color-k3)"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02Substitution() {
  const data = [
    {
      bucket: `Both (${R.hold.both})`,
      opus: R.k1.bothToOpus,
      qwen: R.k1.bothToQwen,
    },
    {
      bucket: `Opus-only (${R.hold.largeOnly})`,
      opus: R.k1.largeOnlyToOpus,
      qwen: R.k1.largeOnlyToQwen,
    },
    {
      bucket: `Qwen-only (${R.hold.smallOnly})`,
      opus: R.k1.smallOnlyToOpus,
      qwen: R.k1.smallOnlyToQwen,
    },
    {
      bucket: `Neither (${R.hold.neither})`,
      opus: R.k1.neitherToOpus,
      qwen: R.k1.neitherToQwen,
    },
  ]
  return (
    <FigureFrame
      id="fig-sub"
      title={
        <>
          Figure 5: <strong>What D’s 26 Opus calls actually are.</strong> At
          λ={R.k1.lambda.toFixed(2)} D hits 33 successes. It only catches{" "}
          {R.k1.largeOnlyToOpus}/{R.hold.largeOnly} of the tasks that truly
          need Opus, and still sends {R.k1.bothToOpus}/{R.hold.both} both-win
          tasks to Opus. Cheaper 33, not “learned which tasks need Opus.”
        </>
      }
    >
      <ChartContainer
        config={routeConfig}
        className="mx-auto h-[280px] w-full max-w-[640px] aspect-auto"
      >
        <BarChart
          data={data}
          accessibilityLayer
          margin={{ top: 16, right: 8, left: 8, bottom: 8 }}
        >
          <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
          <XAxis dataKey="bucket" tickLine={false} axisLine={false} interval={0} />
          <YAxis allowDecimals={false} width={28} />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="opus" stackId="s" fill="var(--color-opus)" maxBarSize={48}>
            <LabelList dataKey="opus" position="inside" fill="#fff" fontSize={11} />
          </Bar>
          <Bar dataKey="qwen" stackId="s" fill="var(--color-qwen)" maxBarSize={48}>
            <LabelList dataKey="qwen" position="inside" fill="#fff" fontSize={11} />
          </Bar>
        </BarChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02Pareto() {
  return (
    <FigureFrame
      id="fig-pareto"
      title={
        <>
          Figure 6: <strong>Full λ-sweep, not just the headline point.</strong>{" "}
          Each line is the non-dominated (Opus calls, successes) pairs as the
          threshold moves. The grey dashed line is 33 successes. D walks along
          that line down to 26 calls. B only reaches 33 at 46 calls. C climbs
          cheaply to 31 successes at 9 calls, then jumps to 45 calls for 32 —
          it never gets onto the 33 line. Oracle match-33 is 10 calls.
        </>
      }
    >
      <ChartContainer
        config={paretoConfig}
        className="mx-auto h-[340px] w-full max-w-[640px] aspect-auto"
      >
        <ScatterChart margin={{ top: 16, right: 16, left: 8, bottom: 28 }}>
          <CartesianGrid stroke="rgba(26,36,51,0.08)" />
          <XAxis
            type="number"
            dataKey="calls"
            domain={[0, 46]}
            ticks={[0, 10, 26, 46]}
            label={{
              value: "Opus calls (of 46)",
              position: "bottom",
              offset: 8,
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="hits"
            domain={[26, 38]}
            ticks={[27, 31, 33, 37]}
            width={36}
            label={{
              value: "Successes",
              angle: -90,
              position: "insideLeft",
              fontSize: 11,
            }}
          />
          <ReferenceLine
            y={R.hold.alwaysLarge}
            stroke="rgba(26,36,51,0.45)"
            strokeDasharray="4 4"
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Scatter
            name="k0"
            data={[...R.pareto.k0]}
            fill="var(--color-k0)"
            line={{ stroke: "var(--color-k0)", strokeWidth: 2 }}
          />
          <Scatter
            name="k1"
            data={[...R.pareto.k1]}
            fill="var(--color-k1)"
            line={{ stroke: "var(--color-k1)", strokeWidth: 2 }}
          />
          <Scatter
            name="k3"
            data={[...R.pareto.k3]}
            fill="var(--color-k3)"
            line={{ stroke: "var(--color-k3)", strokeWidth: 2 }}
          />
        </ScatterChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02Dollars() {
  const $ = R.dollars
  const data = [
    {
      policy: "Always-Opus / A / B",
      usd: Number($.alwaysOpusUsd.toFixed(2)),
      hits: R.hold.alwaysLarge,
    },
    {
      policy: "C K=3 (provisional)",
      usd: Number($.cUsd.toFixed(2)),
      hits: $.cHits,
    },
    {
      policy: "D K=1 (diagnostic)",
      usd: Number($.dUsd.toFixed(2)),
      hits: $.dHits,
    },
    {
      policy: "Oracle (Opus-only only)",
      usd: Number($.oracleUsd.toFixed(2)),
      hits: $.oracleHits,
    },
    {
      policy: "Always-Qwen",
      usd: Number($.alwaysQwenUsd.toFixed(2)),
      hits: R.hold.alwaysSmall,
    },
  ]
  const dollarConfig = {
    usd: { label: "Recorded API $", color: "var(--chart-2)" },
  } satisfies ChartConfig
  return (
    <FigureFrame
      id="fig-dollars"
      title={
        <>
          Figure 7: <strong>Same 46 tasks, recorded Aug 2025 API cost.</strong>{" "}
          Not September 2026 list prices. Always-Opus is ${$.alwaysOpusUsd.toFixed(2)}.
          D’s 26-call policy is ${$.dUsd.toFixed(2)} (save $
          {($.alwaysOpusUsd - $.dUsd).toFixed(2)},{" "}
          {(100 * (1 - $.dUsd / $.alwaysOpusUsd)).toFixed(1)}%) at 33
          successes — exact task mix from holdout scores, not a mean-per-call
          estimate. C at its max-success point is ${$.cUsd.toFixed(2)} and
          still only 32/46. Oracle (send only the 10 Opus-only tasks to Opus)
          is ${$.oracleUsd.toFixed(2)} and actually gets 37 successes, not 33.
          Mean cost on this holdout: ${$.meanOpusUsd.toFixed(2)} Opus vs $
          {$.meanQwenUsd.toFixed(3)} Qwen, about {$.ratio.toFixed(1)}×, well
          under the 15–50× per-token sticker gap.
        </>
      }
    >
      <ChartContainer
        config={dollarConfig}
        className="mx-auto h-[280px] w-full max-w-[640px] aspect-auto"
      >
        <BarChart
          data={data}
          layout="vertical"
          accessibilityLayer
          margin={{ top: 8, right: 56, left: 8, bottom: 8 }}
        >
          <CartesianGrid horizontal={false} stroke="rgba(26,36,51,0.08)" />
          <XAxis
            type="number"
            domain={[0, 55]}
            tickFormatter={(v: number) => `$${v}`}
          />
          <YAxis
            type="category"
            dataKey="policy"
            width={168}
            tickLine={false}
            axisLine={false}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <Bar dataKey="usd" fill="var(--color-usd)" maxBarSize={28} radius={3}>
            <LabelList
              dataKey="usd"
              position="right"
              fontSize={11}
              formatter={(v: unknown) => `$${Number(v).toFixed(2)}`}
            />
          </Bar>
        </BarChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02RegimeCompare() {
  const G = R.generalist
  const specK0MinusFrozen = Number(
    (R.k0.routeAuc - R.frozen.routeAuc).toFixed(3),
  )
  const specK3MinusK0 = Number((R.k3.routeAuc - R.k0.routeAuc).toFixed(3))
  const levels = [
    {
      arm: "Frozen",
      generalist: G.frozen,
      specialist: Number(R.frozen.routeAuc.toFixed(3)),
    },
    {
      arm: "K=0 LoRA",
      generalist: G.k0,
      specialist: Number(R.k0.routeAuc.toFixed(3)),
    },
    {
      arm: "K=3 LoRA",
      generalist: G.k3,
      specialist: Number(R.k3.routeAuc.toFixed(3)),
    },
  ]
  const gaps = [
    {
      contrast: "K=0 − frozen",
      generalist: G.k0MinusFrozen,
      specialist: specK0MinusFrozen,
    },
    {
      contrast: "K=3 − K=0",
      generalist: G.k3MinusK0,
      specialist: specK3MinusK0,
    },
  ]
  const regimeConfig = {
    generalist: {
      label: `Generalist (n=${G.nHold})`,
      color: "#7a8494",
    },
    specialist: {
      label: `Specialist (n=${R.nHold})`,
      color: "var(--chart-2)",
    },
  } satisfies ChartConfig
  return (
    <FigureFrame
      id="fig-regime"
      title={
        <>
          Figure 8: <strong>Specialist vs generalist — compare the
          gaps, not the levels.</strong> Left is Route-AUC by arm. Do not
          read specialist 0.482 as “worse than” generalist 0.686: the
          generalist holdout is all {G.nHold} django tasks after training on{" "}
          {G.nTrain} other-repo issues; this smoke is {R.nHold} django
          after training on {R.nTrainGrad} django. Right is the
          pre-registered contrast: fine-tune lift (K=0 − frozen) is present
          in both regimes (+{G.k0MinusFrozen.toFixed(3)} vs +
          {specK0MinusFrozen.toFixed(3)}); the trajectory gap (K=3 − K=0)
          flips from {G.k3MinusK0.toFixed(3)} under repository shift to +
          {specK3MinusK0.toFixed(3)} in-distribution. That sign flip is the
          SWE-Router mix-1 vs repo-disjoint pattern, but specialist K=3 is
          the overfit checkpoint, so it is not a Q2.2 confirmation. K=1 has
          no generalist counterpart and is omitted.
        </>
      }
    >
      <div className="grid gap-6 md:grid-cols-2">
        <Panel title="Route-AUC (levels are not comparable)">
          <ChartContainer
            config={regimeConfig}
            className="mx-auto h-[280px] w-full aspect-auto"
          >
            <BarChart
              data={levels}
              accessibilityLayer
              barGap={4}
              barCategoryGap="28%"
              margin={{ top: 24, right: 8, left: 0, bottom: 4 }}
            >
              <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
              <XAxis dataKey="arm" tickLine={false} axisLine={false} />
              <YAxis
                domain={[0, 0.8]}
                ticks={[0, 0.25, 0.5, 0.75]}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <ReferenceLine
                y={0.5}
                stroke="rgba(26,36,51,0.25)"
                strokeDasharray="3 3"
              />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar
                dataKey="generalist"
                fill="var(--color-generalist)"
                radius={3}
                maxBarSize={32}
              >
                <LabelList dataKey="generalist" position="top" fontSize={10} />
              </Bar>
              <Bar
                dataKey="specialist"
                fill="var(--color-specialist)"
                radius={3}
                maxBarSize={32}
              >
                <LabelList dataKey="specialist" position="top" fontSize={10} />
              </Bar>
            </BarChart>
          </ChartContainer>
        </Panel>
        <Panel title="Signed gaps (these are the comparable quantities)">
          <ChartContainer
            config={regimeConfig}
            className="mx-auto h-[280px] w-full aspect-auto"
          >
            <BarChart
              data={gaps}
              accessibilityLayer
              barGap={4}
              barCategoryGap="28%"
              margin={{ top: 24, right: 8, left: 0, bottom: 4 }}
            >
              <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
              <XAxis dataKey="contrast" tickLine={false} axisLine={false} />
              <YAxis
                domain={[-0.25, 0.3]}
                ticks={[-0.2, -0.1, 0, 0.1, 0.2]}
                tickLine={false}
                axisLine={false}
                width={40}
                tickFormatter={(v: number) =>
                  `${v > 0 ? "+" : ""}${v.toFixed(1)}`
                }
              />
              <ReferenceLine y={0} stroke="rgba(26,36,51,0.45)" />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar
                dataKey="generalist"
                fill="var(--color-generalist)"
                radius={3}
                maxBarSize={32}
              >
                <LabelList
                  dataKey="generalist"
                  position="top"
                  fontSize={10}
                  formatter={(v: unknown) =>
                    typeof v === "number"
                      ? `${v > 0 ? "+" : ""}${v.toFixed(3)}`
                      : ""
                  }
                />
              </Bar>
              <Bar
                dataKey="specialist"
                fill="var(--color-specialist)"
                radius={3}
                maxBarSize={32}
              >
                <LabelList
                  dataKey="specialist"
                  position="top"
                  fontSize={10}
                  formatter={(v: unknown) =>
                    typeof v === "number"
                      ? `${v > 0 ? "+" : ""}${v.toFixed(3)}`
                      : ""
                  }
                />
              </Bar>
            </BarChart>
          </ChartContainer>
        </Panel>
      </div>
    </FigureFrame>
  )
}

export function RouterE02CeilingBars() {
  const G = R.generalist
  const $ = R.dollars
  const dSavePct = Number((100 * (1 - $.dUsd / $.alwaysOpusUsd)).toFixed(1))
  const data = [
    {
      split: "Oracle ceiling",
      generalist: G.oracleSavePct,
      specialist: Number((100 * (1 - $.oracleUsd / $.alwaysOpusUsd)).toFixed(1)),
    },
    {
      split: "Match always-Opus quality",
      generalist: G.matchSavePct,
      specialist: $.matchSavePct,
    },
    {
      split: "Trained (D vs K=3)",
      generalist: null as number | null,
      specialist: dSavePct,
    },
  ]
  const config = {
    generalist: { label: `Generalist n=${G.nHold}`, color: "#7a8494" },
    specialist: { label: `Specialist n=${R.nHold}`, color: "var(--chart-2)" },
  } satisfies ChartConfig
  return (
    <FigureFrame
      id="fig-ceilings"
      title={
        <>
          Figure 9: <strong>Percent saved vs always-Opus, same recorded
          API dollars.</strong> Oracle and matched-quality rows are label
          oracles, not trained routers. The opportunity is the same shape
          under repo shift ({G.oracleSavePct.toFixed(1)}% vs{" "}
          {(100 * (1 - $.oracleUsd / $.alwaysOpusUsd)).toFixed(1)}% at
          oracle). Trained D on this split is {dSavePct.toFixed(1)}% against
          a possible {$.matchSavePct.toFixed(1)}%. Generalist K=3 has no bar
          — those 231 scores were never written, so its dollar % is unknown,
          not zero.
        </>
      }
    >
      <ChartContainer
        config={config}
        className="mx-auto h-[300px] w-full max-w-[640px] aspect-auto"
      >
        <BarChart
          data={data}
          accessibilityLayer
          barGap={4}
          barCategoryGap="22%"
          margin={{ top: 24, right: 8, left: 0, bottom: 4 }}
        >
          <CartesianGrid vertical={false} stroke="rgba(26,36,51,0.08)" />
          <XAxis dataKey="split" tickLine={false} axisLine={false} />
          <YAxis
            domain={[0, 80]}
            ticks={[0, 20, 40, 60, 80]}
            tickFormatter={(v: number) => `${v}%`}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar
            dataKey="generalist"
            fill="var(--color-generalist)"
            radius={3}
            maxBarSize={36}
          >
            <LabelList
              dataKey="generalist"
              position="top"
              fontSize={10}
              formatter={(v: unknown) =>
                typeof v === "number" ? `${v.toFixed(1)}%` : ""
              }
            />
          </Bar>
          <Bar
            dataKey="specialist"
            fill="var(--color-specialist)"
            radius={3}
            maxBarSize={36}
          >
            <LabelList
              dataKey="specialist"
              position="top"
              fontSize={10}
              formatter={(v: unknown) =>
                typeof v === "number" ? `${v.toFixed(1)}%` : ""
              }
            />
          </Bar>
        </BarChart>
      </ChartContainer>
    </FigureFrame>
  )
}

export function RouterE02Figures() {
  return (
    <div>
      <RouterE02HoldoutBar />
      <RouterE02CallsScatter />
      <RouterE02MetricBars />
      <RouterE02ValCe />
      <RouterE02Substitution />
      <RouterE02Pareto />
      <RouterE02Dollars />
      <RouterE02RegimeCompare />
      <RouterE02CeilingBars />
    </div>
  )
}
