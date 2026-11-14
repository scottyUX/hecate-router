import Link from "next/link";

import { AuthRedirectHandler } from "@/components/auth-redirect-handler";
import { HecateArchitecture } from "@/components/hecate-architecture";
import { HecateMark } from "@/components/hecate-mark";
import { CostHeadroomChart } from "@/components/landing/cost-headroom-chart";
import { RoadmapMilestones } from "@/components/pipeline-stages";
import { SiteHeader } from "@/components/site-header";

const questions = [
  {
    index: "1",
    title: "Route",
    body: "From the issue, and maybe the cheap agent’s first few turns, can a model predict whether the cheap agent will fix it?",
    chip: "issue → P(cheap agent resolves)",
  },
  {
    index: "2",
    title: "Advise",
    body: "Can a small trained advisor coach a cheap agent well enough that the task never needs to escalate?",
    chip: "advisor + cheap agent",
  },
  {
    index: "3",
    title: "Train",
    body: "Which objective trains the router and the advisor best: cross-entropy, GRPO or PPO?",
    chip: "cross-entropy · GRPO · PPO",
  },
] as const;

const practices = [
  {
    title: "Pre-register",
    body: "Each experiment’s spec and decision rules are written and reviewed before any number is seen.",
  },
  {
    title: "Ground in execution",
    body: "Labels come from hidden tests passing, not from a model’s opinion of the patch.",
    dark: true,
  },
  {
    title: "Persist every run",
    body: "Adapter, per-task holdout scores and an off-machine copy, or the run doesn’t count.",
  },
  {
    title: "Keep the nulls",
    body: "Rejected hypotheses and failed checks stay on the record and constrain what we claim.",
  },
] as const;

function SectionTitle({ children, dark = false }: { children: React.ReactNode; dark?: boolean }) {
  return (
    <h2
      className={`max-w-3xl text-3xl leading-[1.1] font-bold tracking-[-0.03em] md:text-[2.75rem] ${
        dark ? "text-white" : "text-[var(--hc-ink)]"
      }`}
    >
      {children}
    </h2>
  );
}

export default function Home() {
  return (
    <div className="hecate-site flex min-h-full flex-1 flex-col">
      <AuthRedirectHandler />
      <SiteHeader />

      <main id="top" className="flex-1">
        {/* Hero */}
        <section className="px-5 pt-16 pb-16 md:px-8 md:pt-24 md:pb-20">
          <div className="mx-auto w-full max-w-[1120px]">
            <div className="flex items-center gap-4 text-[var(--hc-ink)]">
              <HecateMark className="size-12 md:size-16" />
              <span className="text-6xl leading-none font-bold tracking-[-0.05em] md:text-8xl">
                hecate
              </span>
            </div>
            <h1 className="mt-10 max-w-4xl text-4xl leading-[1.08] font-bold tracking-[-0.035em] text-[var(--hc-ink)] md:text-6xl">
              When should a coding agent call the frontier model?
            </h1>
            <p className="mt-8 max-w-2xl text-lg leading-relaxed text-[var(--hc-body)]">
              Hecate Lab at UC Santa Cruz trains routers and advisors for AI
              coding agents.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <a
                href="#gap"
                className="inline-flex h-11 items-center rounded-full bg-[var(--hc-ink)] px-6 text-sm font-semibold text-white transition-colors hover:bg-[var(--hc-accent)]"
              >
                See the gap
              </a>
              <a
                href="#architecture"
                className="inline-flex h-11 items-center rounded-full border border-[var(--hc-ink)] px-6 text-sm font-semibold text-[var(--hc-ink)] transition-colors hover:bg-[var(--hc-ink)] hover:text-white"
              >
                How it works
              </a>
            </div>
          </div>
        </section>

        {/* Headroom */}
        <section
          id="gap"
          className="scroll-mt-16 bg-[var(--hc-ink)] px-5 py-20 text-white md:px-8 md:py-28"
        >
          <div className="mx-auto w-full max-w-[1120px]">
            <p className="text-7xl leading-none font-bold tracking-[-0.05em] text-[var(--hc-accent)] md:text-[9rem]">
              87%
            </p>
            <p className="mt-6 max-w-3xl text-xl leading-snug font-medium md:text-2xl">
              of the tasks we held out didn’t need the frontier model. Matching
              its 163 fixes took the frontier model on only 29 of 231 tasks.
            </p>
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-white/70">
              That is hindsight. Our best generalist router so far recovers almost
              none of it: to keep the same 163 fixes it still sent 229 tasks to
              the frontier model. The distance between those two bars is the
              research problem.
            </p>
            <CostHeadroomChart />
            <p className="mt-10 text-xs text-[var(--hc-faint)]">
              Source: our analysis of public coding-agent runs on a repository
              held out from training.
            </p>
          </div>
        </section>

        {/* Questions */}
        <section id="program" className="scroll-mt-24 px-5 py-20 md:px-8 md:py-28">
          <div className="mx-auto w-full max-w-[1120px]">
            <SectionTitle>Three questions, one lab</SectionTitle>
            <div className="mt-12 grid gap-10 md:grid-cols-3 md:gap-6">
              {questions.map((q) => (
                <div key={q.title} className="border-t border-[var(--hc-rule)] pt-4">
                  <p className="text-xs text-[var(--hc-muted)]">{q.index}</p>
                  <h3 className="mt-1 text-xl font-bold tracking-[-0.02em]">{q.title}</h3>
                  <p className="mt-3 rounded-sm bg-[var(--hc-ink)] px-3 py-2 font-mono text-xs text-white">
                    {q.chip}
                  </p>
                  <p className="mt-4 text-sm leading-relaxed text-[var(--hc-body)]">{q.body}</p>
                </div>
              ))}
            </div>

            <div className="mt-20">
              <ol className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {practices.map((p, i) => {
                  const dark = "dark" in p && p.dark;
                  return (
                    <li
                      key={p.title}
                      className={`rounded-sm border px-4 py-4 ${
                        dark
                          ? "border-[var(--hc-ink)] bg-[var(--hc-ink)] text-white"
                          : "border-[var(--hc-ink)]/70"
                      }`}
                    >
                      <p className={`text-[11px] ${dark ? "text-white/60" : "text-[var(--hc-muted)]"}`}>
                        {i + 1}
                      </p>
                      <p className="text-sm font-bold">{p.title}</p>
                      <p
                        className={`mt-1 text-xs leading-relaxed ${
                          dark ? "text-white/75" : "text-[var(--hc-body)]"
                        }`}
                      >
                        {p.body}
                      </p>
                    </li>
                  );
                })}
              </ol>
            </div>
          </div>
        </section>

        {/* Architecture */}
        <section
          id="architecture"
          className="scroll-mt-24 border-t border-[var(--hc-rule)] px-5 py-20 md:px-8 md:py-28"
        >
          <div className="mx-auto w-full max-w-[1120px]">
            <SectionTitle>
              A cheap agent starts every task.
              <br />
              Hecate decides when to escalate.
            </SectionTitle>
            <HecateArchitecture />
          </div>
        </section>

        {/* Roadmap */}
        <section
          id="roadmap"
          className="scroll-mt-24 border-t border-[var(--hc-rule)] px-5 py-20 md:px-8 md:py-28"
        >
          <div className="mx-auto w-full max-w-[1120px]">
            <SectionTitle>From first router to V1 release, May 2027</SectionTitle>
            <RoadmapMilestones />
          </div>
        </section>

        {/* Journal */}
        <section className="bg-[var(--hc-ink)] px-5 py-20 text-white md:px-8 md:py-24">
          <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-8 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-3xl font-bold tracking-[-0.03em] text-[var(--hc-accent)] md:text-[2.75rem]">
                Follow the research
              </h2>
              <p className="mt-4 max-w-lg text-base leading-relaxed text-white/70">
                Specs, runs, decisions and full write-ups, recorded as the work
                advances.
              </p>
            </div>
            <Link
              href="/journal"
              className="inline-flex h-11 w-fit items-center rounded-full bg-[var(--hc-bg)] px-6 text-sm font-semibold text-[var(--hc-ink)] transition-colors hover:bg-[var(--hc-accent)] hover:text-white"
            >
              Open journal
            </Link>
          </div>
        </section>
      </main>

      <footer className="bg-[var(--hc-ink)] px-5 pb-10 text-xs text-[var(--hc-faint)] md:px-8">
        <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-2 border-t border-white/15 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2">
            <HecateMark className="size-4 text-white" />
            Hecate Lab · UC Santa Cruz
          </p>
          <p>MIT License</p>
        </div>
      </footer>
    </div>
  );
}
