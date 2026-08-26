import { AuthRedirectHandler } from "@/components/auth-redirect-handler";
import { HecateArchitecture } from "@/components/hecate-architecture";
import { RoadmapMilestones } from "@/components/pipeline-stages";
import { SiteHeader } from "@/components/site-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const workstreams = [
  {
    title: "Intelligent task routing",
    body: "Hecate combines a semantic gate and a ts-repo-metrics structural gate, then routes SWE tasks across early-selection MoM, mid, and frontier tiers with execution verification and fail-escalation.",
  },
  {
    title: "SWE task benchmarks",
    body: "Review existing SWE task benchmarks, then release the Hecate Benchmark for near–real-world tasks with correctness and objective quality evaluation.",
  },
  {
    title: "Lab milestones",
    body: "SWE tasks benchmark review, Hecate Benchmark release, LLM task router literature review, and Hecate Router V1 release.",
  },
] as const;

export default function Home() {
  return (
    <>
      <AuthRedirectHandler />
      <SiteHeader />

      <main id="top" className="flex-1">
        <section className="relative overflow-hidden px-5 pt-16 pb-20 md:px-8 md:pt-24 md:pb-28">
          <div
            className="pointer-events-none absolute top-24 right-[12%] size-24 rounded-full bg-[#e8f0fe] md:size-36"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute top-[42%] right-[28%] size-3 rounded-full bg-[#f9ab00]"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute bottom-16 left-[8%] size-2 rounded-full bg-primary"
            aria-hidden="true"
          />

          <div className="relative mx-auto w-full max-w-[1120px]">
            <p className="mb-6 text-sm font-medium text-muted-foreground">
              Research lab · UCSC
            </p>
            <h1 className="max-w-4xl text-5xl leading-[1.05] font-medium tracking-tight text-foreground md:text-7xl">
              <span className="block">Hecate Lab</span>
              <span className="mt-2 block max-w-[18ch] text-foreground/90 md:mt-4 md:ml-[8%]">
                Routing research{" "}
                <span className="text-primary">to reality.</span>
              </span>
            </h1>
            <p className="mt-8 max-w-xl text-base leading-relaxed text-muted-foreground md:mt-10">
              We route models on complex, near–real-world software engineering
              tasks — optimizing for cost and quality. A near-real-world task
              pipeline supplies the work;{" "}
              <span className="text-foreground">ts-repo-metrics</span> scores
              objective code quality alongside correctness.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <a
                href="#architecture"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "h-11 rounded-full px-6 text-sm font-medium"
                )}
              >
                View architecture
              </a>
              <a
                href="#roadmap"
                className={cn(
                  buttonVariants({ size: "lg", variant: "outline" }),
                  "h-11 rounded-full border-border px-6 text-sm font-medium"
                )}
              >
                Lab milestones
              </a>
            </div>
          </div>
        </section>

        <section className="px-5 py-16 md:px-8 md:py-24">
          <div className="mx-auto grid w-full max-w-[1120px] gap-10 md:grid-cols-[0.9fr_1.1fr] md:items-center md:gap-16">
            <div>
              <h2 className="text-3xl font-medium tracking-tight text-foreground md:text-4xl">
                Real-world SWE tasks, judged on cost and quality
              </h2>
              <p className="mt-5 text-base leading-relaxed text-muted-foreground">
                Hecate asks which model tier can handle a complex software
                engineering task without wasting spend or sacrificing quality.
                Outcomes come from evaluation — correctness plus objective code
                quality via ts-repo-metrics — on a pipeline of near–real-world
                tasks.
              </p>
            </div>
            <div className="flex min-h-[280px] flex-col justify-between rounded-[1.75rem] bg-[#202124] p-8 text-white md:min-h-[320px] md:p-10">
              <p className="text-sm font-medium text-white/60">Hecate Lab</p>
              <div>
                <p className="max-w-md text-2xl leading-snug font-medium tracking-tight md:text-3xl">
                  Route complex SWE tasks to models that balance cost and
                  quality.
                </p>
                <dl className="mt-8 grid gap-4 sm:grid-cols-3">
                  {[
                    { dt: "Focus", dd: "Task routing" },
                    { dt: "Track", dd: "SWE benchmarks" },
                    { dt: "Horizon", dd: "May 2027" },
                  ].map((stat) => (
                    <div key={stat.dt}>
                      <dt className="text-xs text-white/50">{stat.dt}</dt>
                      <dd className="mt-1 text-sm font-medium">{stat.dd}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          </div>
        </section>

        <section id="program" className="scroll-mt-24 bg-[#f8f9fa] px-5 py-20 md:px-8 md:py-28">
          <div className="mx-auto w-full max-w-[1120px]">
            <p className="text-sm font-medium text-primary">Research program</p>
            <h2 className="mt-3 max-w-2xl text-3xl font-medium tracking-tight text-foreground md:text-5xl">
              Three workstreams, one lab
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
              Routing research, benchmark construction, and lab milestones run in
              parallel so experiments and releases reinforce each other.
            </p>
            <div className="mt-12 grid gap-5 md:grid-cols-3">
              {workstreams.map((stream) => (
                <article
                  key={stream.title}
                  className="rounded-[1.5rem] bg-background p-7"
                >
                  <h3 className="text-xl font-medium tracking-tight text-foreground">
                    {stream.title}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                    {stream.body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="architecture" className="scroll-mt-24 px-5 py-20 md:px-8 md:py-28">
          <div className="mx-auto w-full max-w-[1120px]">
            <p className="text-sm font-medium text-primary">Architecture</p>
            <h2 className="mt-3 max-w-3xl text-3xl font-medium tracking-tight text-foreground md:text-5xl">
              Hecate router
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
              Semantic and structural gates feed a joint score that selects early
              MoM probes, a mid model, or a frontier model. Execution
              verification can escalate failures; only one promising SLM finishes
              generation after a short probe decode.
            </p>
            <HecateArchitecture />
          </div>
        </section>

        <section id="roadmap" className="scroll-mt-24 bg-[#f8f9fa] px-5 py-20 md:px-8 md:py-28">
          <div className="mx-auto w-full max-w-[1120px]">
            <p className="text-sm font-medium text-primary">Research roadmap</p>
            <h2 className="mt-3 text-3xl font-medium tracking-tight text-foreground md:text-5xl">
              Lab milestones through May 2027
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground">
              Month targets for lab members across benchmark and router work.
            </p>
            <RoadmapMilestones />
          </div>
        </section>

        <section className="px-5 py-20 md:px-8 md:pb-28">
          <div className="mx-auto w-full max-w-[1120px]">
            <div className="rounded-[1.75rem] bg-[#202124] px-8 py-12 text-white md:px-14 md:py-16">
              <p className="text-sm font-medium text-white/55">Lab journal</p>
              <h2 className="mt-3 max-w-xl text-3xl font-medium tracking-tight md:text-4xl">
                Follow the research
              </h2>
              <p className="mt-4 max-w-lg text-base leading-relaxed text-white/65">
                Lab members record decisions, runs, and milestones in the journal
                as the work advances.
              </p>
              <a
                href="/journal"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "mt-8 h-11 rounded-full px-6 text-sm font-medium"
                )}
              >
                Open journal
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border px-5 py-10 text-sm text-muted-foreground md:px-8">
        <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p>Hecate Lab · Cost–quality routing for real-world SWE tasks</p>
          <p>MIT License · UCSC research project</p>
        </div>
      </footer>
    </>
  );
}
