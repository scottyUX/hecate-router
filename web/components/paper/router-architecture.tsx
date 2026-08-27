import type { ReactNode } from "react";

import { ROUTER_V1 } from "@/lib/experiments/router-v1";
import { ROUTER_V2 } from "@/lib/experiments/router-v2";
import { ROUTER_V3 } from "@/lib/experiments/router-v3";
import { cn } from "@/lib/utils";

function Box({
  title,
  subtitle,
  variant = "plain",
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  variant?: "plain" | "score" | "oracle" | "run";
}) {
  return (
    <div
      className={cn(
        "min-w-[7.25rem] flex-1 rounded-sm border px-2.5 py-2",
        variant === "plain" && "border-[var(--paper-line)] bg-white/50",
        variant === "score" &&
          "border-[var(--paper-accent)]/50 bg-[rgba(13,110,110,0.07)]",
        variant === "oracle" &&
          "border-dashed border-[#9a3b2f]/70 bg-[rgba(154,59,47,0.04)]",
        variant === "run" &&
          "border-[var(--paper-accent)]/50 bg-[rgba(13,110,110,0.07)]"
      )}
    >
      <p className="font-sans text-[12px] leading-[1.25] font-medium text-[var(--paper-ink)]">
        {title}
      </p>
      {subtitle ? (
        <p className="mt-0.5 font-sans text-[10px] leading-[1.3] text-[var(--paper-muted)]">
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}

function Arrow({ label }: { label?: string }) {
  return (
    <div
      className="flex w-8 shrink-0 flex-col items-center justify-center self-center text-[9px] leading-none text-[var(--paper-muted)]"
      aria-hidden="true"
    >
      {label ? (
        <span className="mb-1 max-w-[4.5rem] text-center">{label}</span>
      ) : null}
      <span className="block h-px w-5 bg-[var(--paper-ink)]/30" />
      <span className="-mt-[3px] border-y-[3px] border-l-[5px] border-y-transparent border-l-[var(--paper-ink)]/30" />
    </div>
  );
}

function Decision({ label }: { label: string }) {
  return (
    <div className="flex h-full min-h-[4.5rem] shrink-0 items-stretch gap-1 px-1.5">
      <div
        className="w-px self-stretch border-l border-dashed border-[var(--paper-ink)]/45"
        aria-hidden="true"
      />
      <p className="self-center [writing-mode:vertical-rl] rotate-180 text-center font-sans text-[9px] leading-[1.2] text-[var(--paper-muted)]">
        {label}
      </p>
    </div>
  );
}

function ArchFigure({
  id,
  heading,
  note,
  caption,
  children,
}: {
  id: string;
  heading: string;
  note: string;
  caption: ReactNode;
  children: ReactNode;
}) {
  return (
    <figure id={id} className="my-6 scroll-mt-8">
      <p className="font-sans text-[13px] font-medium text-[var(--paper-ink)]">
        {heading}
      </p>
      <div className="mt-3 overflow-x-auto">{children}</div>
      <p className="mt-3 font-sans text-[12px] leading-[1.45] text-[var(--paper-muted)] italic">
        {note}
      </p>
      <figcaption className="mt-2 font-sans text-[13px] leading-[1.45] text-[#555]">
        {caption}
      </figcaption>
    </figure>
  );
}

function PResolve({ suffix }: { suffix?: string }) {
  return (
    <>
      <em>P</em>(resolve){suffix ? suffix : ""}
    </>
  );
}

export function RouterArchitectureV1() {
  return (
    <ArchFigure
      id="fig-arch"
      heading="v1 — frozen text embedding"
      note="no repo, no diffs, no tests, no traces — nothing left of the line has run Qwen yet."
      caption={
        <>
          Figure 1: <strong>Frozen text embedding.</strong> v1 decides purely
          from issue text, entirely before Qwen attempts the task. Django
          holdout: Route-AUC {ROUTER_V1.logistic.django.routeAuc}, chance-level.
        </>
      }
    >
      <div className="flex min-w-[36rem] items-stretch">
        <Box
          title="GitHub issue text"
          subtitle="problem_statement only"
        />
        <Arrow label="encode" />
        <Box
          title="ModernBERT-base"
          subtitle="frozen — no gradient"
        />
        <Arrow label="CLS, 768-d" />
        <Box
          title="logistic / MLP"
          subtitle="headline vs diagnostic"
        />
        <Decision label="routing decision" />
        <Box
          title={<PResolve />}
          subtitle="the score"
          variant="score"
        />
      </div>
    </ArchFigure>
  );
}

export function RouterArchitectureV2() {
  return (
    <ArchFigure
      id="fig-arch"
      heading="v2 — oracle structural fusion (ceiling test)"
      note="best case a structural signal could ever see — a deployed router has strictly less than this."
      caption={
        <>
          Figure 1: <strong>Oracle structural fusion.</strong> Even with the
          gold-patch files known in advance — information no real router has —
          structure adds no lift over text alone. Django holdout: Route-AUC{" "}
          {ROUTER_V2.logistic.django.fusion.routeAuc}, same as v1.
        </>
      }
    >
      <div className="flex min-w-[40rem] items-stretch">
        <div className="flex min-w-0 flex-1 flex-col justify-center gap-5">
          <div className="flex items-stretch">
            <Box
              title="GitHub issue text"
              subtitle="same as v1"
            />
            <Arrow />
            <Box
              title="ModernBERT-base"
              subtitle="frozen, CLS 768-d"
            />
          </div>
          <div className="flex items-stretch">
            <Box
              title="gold-patch file list"
              subtitle="oracle — leaked from the answer"
              variant="oracle"
            />
            <Arrow label="at base_commit" />
            <Box
              title="AST parser"
              subtitle="12-d: LOC, cyclomatic…"
            />
          </div>
        </div>
        <Arrow />
        <Box
          title="concat + head"
          subtitle="logistic / MLP"
        />
        <Decision label="routing decision" />
        <Box
          title={<PResolve />}
          subtitle="the score"
          variant="score"
        />
      </div>
    </ArchFigure>
  );
}

export function RouterArchitectureV3() {
  const k0 = ROUTER_V3.k0.routeAuc.toFixed(3);
  return (
    <ArchFigure
      id="fig-arch"
      heading="v3 — trajectory-conditioned LoRA (K=0 control vs K=3)"
      note="K=0 stays left of the boundary; K=3 crosses it — the decision now costs the weak model’s first three turns."
      caption={
        <>
          Figure 1: <strong>K=0 control vs K=3.</strong> K=0 is a
          trajectory-blind control (separately trained, django Route-AUC {k0},
          one seed). K=3 is the same architecture reading three real turns of
          Qwen’s own attempt. The gate was whether it clearly beats K=0, not
          whether it beats v1’s old floor — it did not (
          {ROUTER_V3.k3.routeAuc.toFixed(3)} vs {k0}, one seed).
        </>
      }
    >
      <div className="grid min-w-[48rem] items-stretch gap-y-5 [grid-template-columns:8.25rem_2rem_8.75rem_auto_minmax(7.5rem,1fr)_2rem_minmax(7.5rem,1fr)_2rem_minmax(7.5rem,1fr)]">
        <div className="row-span-2 flex items-center">
          <Box
            title="GitHub issue text"
            subtitle="shared input"
          />
        </div>
        <div className="row-span-2 flex items-center">
          <Arrow />
        </div>
        <Box
          title="LoRA — K=0"
          subtitle="text only, separately trained"
        />
        <div className="row-span-2">
          <Decision label="routing decision (no shared weights with K=3)" />
        </div>
        <Box
          title={<PResolve suffix=", K=0" />}
          subtitle="control"
          variant="score"
        />
        <div />
        <div />
        <div />
        <div />
        <div />
        <Box
          title="Qwen3-Coder runs"
          subtitle="mini-SWE-agent, K=3 turns — execution happens here"
          variant="run"
        />
        <Arrow />
        <Box
          title="packed trajectory"
          subtitle="tool calls, files, test output"
        />
        <Arrow />
        <Box
          title="LoRA — K=3"
          subtitle="last-token logits @ K=3"
        />
      </div>
    </ArchFigure>
  );
}
