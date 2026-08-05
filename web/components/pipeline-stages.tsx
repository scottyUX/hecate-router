import { Badge } from "@/components/ui/badge";

const milestones = [
  {
    index: "01",
    date: "October 2026",
    title: "SWE tasks benchmark review",
    body: "Review software-engineering task benchmarks — coverage, evaluation protocols, and gaps for near–real-world SWE work.",
    current: true,
  },
  {
    index: "02",
    date: "January 2027",
    title: "Hecate Benchmark release",
    body: "Release the lab’s SWE task benchmark from near–real-world task bundles, with correctness and quality evaluation via ts-repo-metrics.",
    current: false,
  },
  {
    index: "03",
    date: "February 2027",
    title: "LLM task router literature review",
    body: "Publish a literature review of LLM task routing methods for software engineering — separate from the Hecate system release.",
    current: false,
  },
  {
    index: "04",
    date: "May 2027",
    title: "Hecate Router V1 release",
    body: "Release Hecate Router V1: semantic and structural gates, tiered MoM routing, execution verification, and cost–quality results.",
    current: false,
  },
] as const;

/** Vertical roadmap timeline adapted from @shadcn-studio/timeline-component-05. */
export function RoadmapMilestones() {
  return (
    <div className="mt-12">
      {milestones.map((milestone, index) => (
        <div
          key={milestone.index}
          id={`milestone-${milestone.index}`}
          className="relative flex scroll-mt-24 justify-end gap-2"
        >
          <div className="sticky top-24 flex w-36 flex-col items-end gap-1.5 self-start pb-4 max-md:hidden">
            <span className="text-sm font-medium text-primary">
              {milestone.index}
            </span>
            <div className="text-right text-sm text-muted-foreground">
              {milestone.date}
            </div>
          </div>
          <div className="flex flex-col items-center">
            <div className="sticky top-24 flex size-6 items-center justify-center max-sm:top-5">
              <span
                className={
                  milestone.current
                    ? "size-3 rounded-full bg-primary"
                    : "size-3 rounded-full border-2 border-border bg-background"
                }
              />
            </div>
            {index < milestones.length - 1 ? (
              <span className="-mt-1 w-px flex-1 bg-border" />
            ) : null}
          </div>
          <div className="flex flex-1 flex-col gap-3 pb-12 pl-3 md:pl-6 lg:pl-9">
            <div className="flex flex-col gap-1 md:hidden">
              <span className="text-sm font-medium text-primary">
                {milestone.index}
              </span>
              <div className="text-sm text-muted-foreground">
                {milestone.date}
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="text-2xl font-medium tracking-tight text-foreground">
                  {milestone.title}
                </h3>
                {milestone.current ? (
                  <Badge className="rounded-full bg-primary px-2.5 text-primary-foreground">
                    Current
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="rounded-full border-border bg-background px-2.5 text-muted-foreground"
                  >
                    Upcoming
                  </Badge>
                )}
              </div>
              <p className="max-w-2xl text-base leading-relaxed text-muted-foreground">
                {milestone.body}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
