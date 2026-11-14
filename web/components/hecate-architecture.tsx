import { HecateMark } from "@/components/hecate-mark";

function Box({
  title,
  body,
  index,
  dark = false,
  planned = false,
  className = "",
}: {
  title: React.ReactNode;
  body: string;
  index?: string;
  dark?: boolean;
  planned?: boolean;
  className?: string;
}) {
  const tone = dark
    ? "border-[var(--hc-ink)] bg-[var(--hc-ink)] text-white"
    : planned
      ? "border-dashed border-[var(--hc-faint)] bg-transparent"
      : "border-[var(--hc-ink)]/70 bg-[var(--hc-bg)]";
  return (
    <div className={`rounded-sm border px-4 py-3 ${tone} ${className}`}>
      {index ? (
        <p className={`text-[11px] ${dark ? "text-white/60" : "text-[var(--hc-muted)]"}`}>
          {index}
        </p>
      ) : null}
      <p className="text-sm font-bold tracking-[-0.01em]">{title}</p>
      <p
        className={`mt-1 text-xs leading-relaxed ${
          dark ? "text-white/75" : "text-[var(--hc-body)]"
        }`}
      >
        {body}
      </p>
    </div>
  );
}

/** Horizontal on wide screens, vertical when stacked. */
function Arrow() {
  return (
    <div className="flex items-center justify-center text-[var(--hc-muted)]" aria-hidden="true">
      <span className="md:hidden">↓</span>
      <span className="hidden md:flex md:items-center">
        <span className="h-px w-6 bg-[var(--hc-muted)]" />
        <span className="-ml-px border-y-[4px] border-l-[6px] border-y-transparent border-l-[var(--hc-muted)]" />
      </span>
    </div>
  );
}

const loop = [
  {
    title: "Run",
    body: "The cheap and frontier agents attempt the same real software-engineering tasks.",
  },
  {
    title: "Score",
    body: "Hidden tests decide whether each patch resolves the issue. That pass/fail is the label; no LLM judge.",
    dark: true,
  },
  {
    title: "Train",
    body: "The router learns P(cheap agent resolves). The advisor learns from resolve reward with GRPO; PPO is next.",
  },
  {
    title: "Price",
    body: "Sweep the escalation threshold λ. Report Route-AUC and the dollars it takes to match always-frontier quality.",
  },
] as const;

export function HecateArchitecture() {
  return (
    <figure className="mt-12" aria-labelledby="architecture-diagram-caption">
      <figcaption id="architecture-diagram-caption" className="sr-only">
        Hecate flow: an SWE task, optionally with the cheap agent’s first few
        turns, goes to the Hecate router, which keeps it on the cheap agent
        (optionally coached by a trained advisor) or escalates it to the
        frontier model. Mid-run hand-off and a four-way route-or-advise
        decision are planned. Below, the research loop: run both agents, score
        patches with hidden tests, train the router and advisor on those
        labels, and price the result.
      </figcaption>

      <div className="grid items-center gap-3 md:grid-cols-[1fr_auto_1fr_auto_1.15fr]">
        <Box
          title="SWE task"
          body="Issue text and the repository. Some router variants also read the cheap agent’s first few turns."
        />
        <Arrow />
        <Box
          dark
          title={
            <span className="flex items-center gap-2">
              <HecateMark className="size-4 text-white" />
              hecate router
            </span>
          }
          body="A small fine-tuned model scores the chance the cheap agent resolves the task."
        />
        <Arrow />
        <div className="grid gap-3">
          <Box
            title="Stay cheap"
            body="A low-cost model, optionally coached by a small trained advisor."
          />
          <Box title="Escalate" body="Hand the task to a frontier model." />
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Box
          planned
          title="Hand off mid-run"
          body="Escalate partway through, passing full text, a summary or the KV cache."
        />
        <Box
          planned
          title="Route or advise"
          body="One decision over four options: cheap, cheap + advisor, mid or premium."
        />
      </div>

      <ol className="mt-12 grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
        {loop.map((step, i) => (
          <li key={step.title} className="contents">
            <Box
              index={String(i + 1)}
              title={step.title}
              body={step.body}
              dark={"dark" in step && step.dark}
              className="h-full"
            />
            {i < loop.length - 1 ? <Arrow /> : null}
          </li>
        ))}
      </ol>

      <p className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-xs text-[var(--hc-muted)]">
        <span className="flex items-center gap-2">
          <span className="inline-block h-3 w-5 rounded-[2px] border border-[var(--hc-ink)]/70" />
          Built and tested
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-3 w-5 rounded-[2px] border border-dashed border-[var(--hc-faint)]" />
          Planned, not run
        </span>
      </p>
    </figure>
  );
}
