import {
  Brain,
  CheckCircle2,
  Cuboid,
  Filter,
  MessageSquareText,
  ShieldCheck,
  BarChart3,
} from "lucide-react";

function Node({
  title,
  subtitle,
  accent = "neutral",
  icon,
  className = "",
}: {
  title: string;
  subtitle?: string;
  accent?: "neutral" | "blue" | "green" | "violet" | "orange" | "success";
  icon?: React.ReactNode;
  className?: string;
}) {
  const accents = {
    neutral: "border-border bg-background",
    blue: "border-[#c2d7f8] bg-[#e8f0fe]",
    green: "border-[#c4e0c8] bg-[#e6f4ea]",
    violet: "border-[#ddd0ef] bg-[#f3e8fd]",
    orange: "border-[#fdddb3] bg-[#fef7e0]",
    success: "border-[#c4e0c8] bg-[#e6f4ea]",
  } as const;

  const titleColor = {
    neutral: "text-foreground",
    blue: "text-[#174ea6]",
    green: "text-[#137333]",
    violet: "text-[#681da8]",
    orange: "text-[#b06000]",
    success: "text-[#137333]",
  } as const;

  return (
    <div
      className={`rounded-2xl border px-4 py-3 text-left shadow-[0_1px_0_rgba(60,64,67,0.06)] ${accents[accent]} ${className}`}
    >
      <div className="flex items-start gap-2.5">
        {icon ? (
          <span className={`mt-0.5 shrink-0 ${titleColor[accent]}`}>{icon}</span>
        ) : null}
        <div className="min-w-0">
          <p className={`text-sm font-medium tracking-tight ${titleColor[accent]}`}>
            {title}
          </p>
          {subtitle ? (
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function ArrowDown({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center py-2" aria-hidden="true">
      {label ? (
        <span className="mb-1 rounded-full bg-[#f1f3f4] px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
          {label}
        </span>
      ) : null}
      <span className="h-4 w-px bg-border" />
      <span className="-mt-px border-x-[4px] border-t-[6px] border-x-transparent border-t-border" />
    </div>
  );
}

export function HecateArchitecture() {
  return (
    <figure
      className="mt-10 overflow-hidden rounded-[1.75rem] border border-border bg-background"
      aria-labelledby="architecture-diagram-caption"
    >
      <figcaption id="architecture-diagram-caption" className="sr-only">
        Hecate architecture diagram: user prompt through semantic and structural
        gates into a joint decision gate, then Tier 1 early-selection MoM, Tier 2
        mid model, or Tier 3 frontier model, with execution verification,
        fail-escalation, and final patch output.
      </figcaption>

      <div className="border-b border-border px-5 py-4 md:px-8">
        <p className="text-sm font-medium text-foreground">Hecate architecture</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Semantic + structural gating → tiered routing → verify or escalate
        </p>
      </div>

      <div className="space-y-1 px-4 py-8 md:px-10 md:py-10">
        {/* Prompt */}
        <div className="mx-auto max-w-sm">
          <Node
            title="User prompt"
            subtitle="Prompt text + code context"
            icon={<MessageSquareText className="size-4" />}
          />
        </div>
        <ArrowDown />

        {/* Dual gates */}
        <div className="mx-auto grid max-w-2xl gap-3 sm:grid-cols-2">
          <Node
            title="Semantic gate"
            subtitle="DistilBERT → S_semantic"
            accent="blue"
            icon={<Brain className="size-4" />}
          />
          <Node
            title="Structural gate"
            subtitle="ts-repo-metrics → W_struct"
            accent="green"
            icon={<BarChart3 className="size-4" />}
          />
        </div>
        <ArrowDown />

        {/* Joint decision */}
        <div className="mx-auto max-w-md">
          <Node
            title="Joint decision gate"
            subtitle="S = α·S_sem + β·W_struct"
            accent="violet"
            icon={<Filter className="size-4" />}
          />
        </div>

        {/* Tier branches */}
        <div className="mt-2 grid gap-4 lg:grid-cols-3">
          {/* Tier 1 */}
          <div className="flex flex-col">
            <ArrowDown label="S < τ_mid" />
            <div className="flex flex-1 flex-col rounded-[1.25rem] border border-[#c2d7f8] bg-[#f8fbff] p-3">
              <p className="px-1 text-sm font-medium text-[#174ea6]">
                Tier 1: Early-selection MoM
              </p>
              <p className="mt-0.5 px-1 text-xs text-muted-foreground">
                Parallel probe decoding
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {["SLM 1", "SLM 2", "SLM 3"].map((slm) => (
                  <div
                    key={slm}
                    className="rounded-xl border border-[#c2d7f8] bg-background px-2 py-2 text-center text-xs font-medium text-[#174ea6]"
                  >
                    {slm}
                  </div>
                ))}
              </div>
              <ArrowDown />
              <Node
                title="Early model-selection gate"
                subtitle="Short probe decode · confidence / divergence / predicted pass"
                accent="blue"
                icon={<Filter className="size-4" />}
              />
              <ArrowDown />
              <Node
                title="Selected SLM completes patch"
                accent="blue"
                icon={<Cuboid className="size-4" />}
              />
            </div>
          </div>

          {/* Tier 2 */}
          <div className="flex flex-col">
            <ArrowDown label="τ_mid ≤ S < τ_prem" />
            <div className="flex flex-1 flex-col gap-3 rounded-[1.25rem] border border-border bg-[#f8f9fa] p-3">
              <div>
                <p className="px-1 text-sm font-medium text-foreground">
                  Tier 2: Intermediate
                </p>
                <p className="mt-0.5 px-1 text-xs text-muted-foreground">
                  1 mid model
                </p>
              </div>
              <div className="mt-auto flex flex-1 items-center justify-center rounded-2xl border border-dashed border-border bg-background py-10">
                <Cuboid className="size-8 text-muted-foreground" />
              </div>
            </div>
          </div>

          {/* Tier 3 */}
          <div className="flex flex-col">
            <ArrowDown label="S ≥ τ_prem" />
            <div className="flex flex-1 flex-col gap-3 rounded-[1.25rem] border border-[#fdddb3] bg-[#fffbf0] p-3">
              <div>
                <p className="px-1 text-sm font-medium text-[#b06000]">
                  Tier 3: Premium
                </p>
                <p className="mt-0.5 px-1 text-xs text-muted-foreground">
                  1 frontier model
                </p>
              </div>
              <div className="mt-auto flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[#fdddb3] bg-background py-10">
                <Cuboid className="size-8 text-[#e37400]" />
              </div>
            </div>
          </div>
        </div>

        {/* Verifier + output */}
        <div className="mx-auto mt-2 max-w-md">
          <div className="flex justify-center gap-8 text-[10px] text-muted-foreground" aria-hidden="true">
            <span className="flex flex-col items-center">
              <span className="h-4 w-px bg-border" />
              <span className="-mt-px border-x-[4px] border-t-[6px] border-x-transparent border-t-border" />
              <span className="mt-1">from Tier 1 / 2</span>
            </span>
          </div>
          <Node
            title="Execution verifier"
            subtitle="compile / test / lint"
            icon={<ShieldCheck className="size-4" />}
          />
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-dashed border-[#fdddb3] bg-[#fef7e0] px-3 py-3 text-center">
              <p className="text-xs font-medium text-[#b06000]">fail → escalate</p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Retry on Tier 3 frontier model
              </p>
            </div>
            <div className="rounded-2xl border border-[#c4e0c8] bg-[#e6f4ea] px-3 py-3 text-center">
              <p className="text-xs font-medium text-[#137333]">pass</p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Accept verified patch
              </p>
            </div>
          </div>
          <ArrowDown />
          <Node
            title="Final patch output"
            accent="success"
            icon={<CheckCircle2 className="size-4" />}
          />
        </div>
      </div>
    </figure>
  );
}
