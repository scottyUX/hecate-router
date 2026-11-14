type Status = "done" | "now" | "planned";

const milestones: {
  date: string;
  title: string;
  body: string;
  status: Status;
}[] = [
  {
    date: "Aug 2026",
    title: "First routers",
    body: "Frozen issue text, oracle code structure, then a fine-tuned router with and without the cheap agent’s first turns.",
    status: "done",
  },
  {
    date: "Sep 2026",
    title: "Specialist and generalist routers",
    body: "Train and test on a single repository, then a generalist across repositories. Every adapter and per-task score is now saved.",
    status: "done",
  },
  {
    date: "Oct 2026",
    title: "Route then advise",
    body: "A small advisor model trained with GRPO to coach a cheap student, tested across three students.",
    status: "done",
  },
  {
    date: "Oct 2026",
    title: "SWE tasks benchmark review",
    body: "Review software-engineering task benchmarks: coverage, evaluation protocols, and gaps for near–real-world work.",
    status: "now",
  },
  {
    date: "Nov 2026",
    title: "PPO vs GRPO for the advisor",
    body: "On the lab’s DGX Spark, with every rollout saved. The toolchain check passed: a 3-step GRPO + LoRA run with weight sync to vLLM.",
    status: "now",
  },
  {
    date: "Next",
    title: "Router training, route or advise, hand-off",
    body: "PPO vs GRPO for the router, a four-way route-or-advise decision, and mid-run hand-off by text, summary or KV cache.",
    status: "planned",
  },
  {
    date: "Jan 2027",
    title: "Hecate Benchmark release",
    body: "A contamination-free benchmark of real feature work in evolving web apps, graded by hidden tests and human review.",
    status: "planned",
  },
  {
    date: "Feb 2027",
    title: "LLM task router literature review",
    body: "A survey of task-routing methods for software engineering, separate from the Hecate system release.",
    status: "planned",
  },
  {
    date: "May 2027",
    title: "Hecate Router V1 release",
    body: "Release the router with its cost–quality results.",
    status: "planned",
  },
];

const statusLabel: Record<Status, string> = {
  done: "Done",
  now: "In progress",
  planned: "Planned",
};

function Dot({ status }: { status: Status }) {
  if (status === "done") {
    return <span className="size-3 rounded-full bg-[var(--hc-ink)]" />;
  }
  if (status === "now") {
    return (
      <span className="size-3 rounded-full bg-[var(--hc-accent)] ring-4 ring-[var(--hc-accent)]/20" />
    );
  }
  return <span className="size-3 rounded-full border-2 border-[var(--hc-faint)] bg-[var(--hc-bg)]" />;
}

/** Vertical roadmap timeline adapted from @shadcn-studio/timeline-component-05. */
export function RoadmapMilestones() {
  return (
    <ol className="mt-12">
      {milestones.map((m, index) => (
        <li key={m.title} className="relative flex gap-2">
          <div className="w-24 shrink-0 pt-0.5 text-right font-mono text-xs text-[var(--hc-muted)] max-md:hidden md:w-32">
            {m.date}
          </div>
          <div className="flex flex-col items-center">
            <div className="flex size-6 items-center justify-center">
              <Dot status={m.status} />
            </div>
            {index < milestones.length - 1 ? (
              <span className="-mt-1 w-px flex-1 bg-[var(--hc-rule)]" />
            ) : null}
          </div>
          <div className="flex-1 pb-10 pl-3 md:pl-6">
            <p className="font-mono text-xs text-[var(--hc-muted)] md:hidden">{m.date}</p>
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-xl font-bold tracking-[-0.02em] text-[var(--hc-ink)]">
                {m.title}
              </h3>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold tracking-[0.08em] uppercase ${
                  m.status === "now"
                    ? "bg-[var(--hc-ink)] text-white"
                    : m.status === "done"
                      ? "border border-[var(--hc-ink)]/60 text-[var(--hc-ink)]"
                      : "border border-[var(--hc-rule)] text-[var(--hc-muted)]"
                }`}
              >
                {statusLabel[m.status]}
              </span>
            </div>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--hc-body)]">
              {m.body}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
