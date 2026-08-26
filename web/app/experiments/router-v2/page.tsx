import Link from "next/link";
import { redirect } from "next/navigation";

import { RouterV2Figures } from "@/components/experiments/router-v2-figures";
import { MetricTable } from "@/components/metric-table";
import { Badge } from "@/components/ui/badge";
import { requireLabMember } from "@/lib/auth";
import { ROUTER_V2 as R } from "@/lib/experiments/router-v2";
import { createClient } from "@/lib/supabase/server";

const toc = [
  { href: "#abstract", label: "Abstract" },
  { href: "#figures", label: "Figures" },
  { href: "#tables", label: "Tables" },
  { href: "#setup", label: "Setup" },
  { href: "#reading", label: "Reading" },
  { href: "#next", label: "Next" },
] as const;

export default async function RouterV2ReportPage() {
  const { user, authorized } = await requireLabMember();
  if (!user) redirect("/login?next=/experiments/router-v2");
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect("/login?next=/experiments/router-v2");
  }

  return (
    <div className="mx-auto w-full max-w-[1120px] px-5 py-10 md:px-8">
      <Link
        href="/experiments"
        className="text-sm text-muted-foreground hover:text-primary"
      >
        ← Experiments
      </Link>

      <header className="mt-6 border-b border-border pb-8">
        <div className="flex flex-wrap gap-2">
          <Badge>static page</Badge>
          <Badge variant="outline">oracle leak</Badge>
          <Badge variant="secondary">missed target</Badge>
        </div>
        <h1 className="mt-4 max-w-4xl font-heading text-4xl font-medium tracking-tight md:text-5xl">
          Structural fusion v2: oracle AST metrics on gold-patch files still
          don&apos;t beat the text floor
        </h1>
        <p className="mt-4 text-sm text-muted-foreground">
          26 August 2026 · SWE-bench Verified (500) · frozen ModernBERT-base ·
          trainer uncommitted
        </p>
      </header>

      <div className="mt-10 grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_220px]">
        <article className="min-w-0 space-y-12">
          <section id="abstract" className="scroll-mt-24 rounded-2xl bg-card p-6 ring-1 ring-foreground/10">
            <h2 className="font-heading text-sm font-medium tracking-wide text-primary uppercase">
              Abstract
            </h2>
            <p className="mt-3 text-base leading-relaxed text-foreground/90">
              If the router is told which files the gold patch touches, do
              Python AST counts plus frozen issue-text CLS beat text-only? No.
              Logistic fusion is 0.482 Route-AUC / 0.518 AUROC on django holdout
              (n=231) versus v1 0.477 / 0.516. Target was ≥ 0.55 / ≥ 0.60.
              Grouped 0.593 is the same 0.589 trap. Static structure is closed.
            </p>
          </section>

          <section id="figures" className="scroll-mt-24 space-y-4">
            <h2 className="font-heading text-2xl font-medium">Figures</h2>
            <RouterV2Figures />
          </section>

          <section id="tables" className="scroll-mt-24 space-y-8">
            <h2 className="font-heading text-2xl font-medium">Tables</h2>
            <MetricTable
              caption="Table 1. Where we are versus the django holdout target. Logistic head, frozen encoder."
              headers={["Metric", "Where we are", "Target"]}
              rows={[
                [
                  "Django holdout Route-AUC",
                  `fusion ${R.logistic.django.fusion.routeAuc}`,
                  "≥ 0.55, tight std (~±0.03)",
                ],
                [
                  "Django holdout AUROC",
                  `fusion ${R.logistic.django.fusion.auroc}`,
                  "≥ 0.60",
                ],
                [
                  "Grouped 5-fold Route-AUC",
                  `fusion ${R.logistic.grouped.fusion.routeAuc}`,
                  "Ignore as headline",
                ],
                [
                  "Metrics-only",
                  `grouped ${R.logistic.grouped.metrics.routeAuc} / django ${R.logistic.django.metrics.routeAuc}`,
                  "Dead end",
                ],
              ]}
            />
            <MetricTable
              caption="Table 2. Logistic headline. Highlighted rows are django holdout (n=231). Accuracy stays under always-Qwen on django (58.0%)."
              highlight={(row) => row[1].includes("leave-django-out")}
              headers={["Arm", "Split", "Route-AUC", "AUROC", "Accuracy", "Brier"]}
              rows={[
                ["v1 text", "grouped 5-fold", R.logistic.grouped.text.routeAuc, R.logistic.grouped.text.auroc, R.logistic.grouped.text.acc, R.logistic.grouped.text.brier],
                ["v2 fusion", "grouped 5-fold", R.logistic.grouped.fusion.routeAuc, R.logistic.grouped.fusion.auroc, R.logistic.grouped.fusion.acc, R.logistic.grouped.fusion.brier],
                ["v2 metrics-only", "grouped 5-fold", R.logistic.grouped.metrics.routeAuc, R.logistic.grouped.metrics.auroc, R.logistic.grouped.metrics.acc, R.logistic.grouped.metrics.brier],
                ["v1 text", "leave-django-out n=231", R.logistic.django.text.routeAuc, R.logistic.django.text.auroc, R.logistic.django.text.acc, R.logistic.django.text.brier],
                ["v2 fusion", "leave-django-out n=231", R.logistic.django.fusion.routeAuc, R.logistic.django.fusion.auroc, R.logistic.django.fusion.acc, R.logistic.django.fusion.brier],
                ["v2 metrics-only", "leave-django-out n=231", R.logistic.django.metrics.routeAuc, R.logistic.django.metrics.auroc, R.logistic.django.metrics.acc, R.logistic.django.metrics.brier],
              ]}
            />
            <MetricTable
              caption="Table 3. Leave-repo reverse (hold n=269). Not averaged with django."
              headers={["Arm", "Route-AUC", "AUROC", "Accuracy"]}
              rows={[
                ["v1 text", R.logistic.rest.text.routeAuc, R.logistic.rest.text.auroc, R.logistic.rest.text.acc],
                ["v2 fusion", R.logistic.rest.fusion.routeAuc, R.logistic.rest.fusion.auroc, R.logistic.rest.fusion.acc],
                ["v2 metrics-only", R.logistic.rest.metrics.routeAuc, R.logistic.rest.metrics.auroc, R.logistic.rest.metrics.acc],
              ]}
            />
            <MetricTable
              caption="Table 4. MLP diagnostic. Extra capacity fits noise. Metrics-only django Route-AUC 0.546 is a noisy cell (AUROC 0.521)."
              headers={["Arm", "Grouped Route-AUC", "Grouped AUROC", "Django Route-AUC", "Django AUROC"]}
              rows={[
                ["v1 text", R.mlp.grouped.text.routeAuc, R.mlp.grouped.text.auroc, R.mlp.django.text.routeAuc, R.mlp.django.text.auroc],
                ["v2 fusion", R.mlp.grouped.fusion.routeAuc, R.mlp.grouped.fusion.auroc, R.mlp.django.fusion.routeAuc, R.mlp.django.fusion.auroc],
                ["v2 metrics-only", R.mlp.grouped.metrics.routeAuc, R.mlp.grouped.metrics.auroc, R.mlp.django.metrics.routeAuc, R.mlp.django.metrics.auroc],
              ]}
            />
          </section>

          <section id="setup" className="scroll-mt-24 space-y-3">
            <h2 className="font-heading text-2xl font-medium">Setup</h2>
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
              Frozen CLS (768) plus a 12-d Python AST vector on gold-patch files
              at <code>base_commit</code>: n_files, n_functions, n_imports, loc,
              mean/max cyclomatic, mean/max nesting, mean/max function LOC, mean
              arity, parse_errors. No fan-out. Metrics scaled on the train fold
              only. Weighted BCE. Fail-closed 500/500 ({R.cacheFiles} oracle
              files, {R.parseErrors} parse error). Prompt char caps were not
              applied. Encoder stayed frozen. Spec 015{" "}
              <code>run_train.py</code> unchanged.
            </p>
          </section>

          <section id="reading" className="scroll-mt-24 space-y-3">
            <h2 className="font-heading text-2xl font-medium">Reading</h2>
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
              Even with oracle file paths, AST counts add no lift over frozen
              issue text. A leak-free structural pipeline has strictly less
              information. SWE-Router prompt-only embeddings sit in the same
              place; their lift is K-turn trajectories (gpt-5-mini K=3 Route-AUC
              0.694; deepseek K=2 0.780 vs K=0 0.627). Next signal is that
              class. On escalation, restart the strong model from the original
              issue text.
            </p>
          </section>

          <section id="next" className="scroll-mt-24 space-y-3">
            <h2 className="font-heading text-2xl font-medium">Next</h2>
            <ol className="max-w-3xl list-decimal space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground">
              <li>
                Do not pursue static structural fusion (BM25 files, whole-repo
                ts-repo-metrics, or other non-oracle file guesses).
              </li>
              <li>
                v3: K-turn trajectory-conditioned router (K=3, LoRA value head
                Qwen2.5-Coder-7B r=32 α=64). Same django-holdout target.
              </li>
              <li>
                Check public mini-swe-agent v1.0.0 logs before paying for new
                Qwen3-Coder turns.
              </li>
            </ol>
          </section>
        </article>

        <aside className="lg:sticky lg:top-24">
          <div className="rounded-2xl bg-card p-5 ring-1 ring-foreground/10">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Contents
            </p>
            <nav className="mt-3 flex flex-col gap-2 text-sm">
              {toc.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="text-foreground/80 hover:text-primary"
                >
                  {item.label}
                </a>
              ))}
            </nav>
          </div>
          <div className="mt-4 rounded-2xl bg-card p-5 ring-1 ring-foreground/10">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Tags
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              router · structural-fusion · ast · oracle-ceiling · verified
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
