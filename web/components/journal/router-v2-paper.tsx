import { redirect } from "next/navigation";

import { RouterV2Figures } from "@/components/experiments/router-v2-figures";
import {
  PaperAbstract,
  PaperSection,
  PaperShell,
  PaperSubsection,
  PaperToc,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireLabMember } from "@/lib/auth";
import { ROUTER_V2 as R } from "@/lib/experiments/router-v2";
import { createClient } from "@/lib/supabase/server";

const SLUG = "2026-08-26-oracle-metrics-fusion-v2";

const toc: PaperTocItem[] = [
  { href: "#introduction", label: "Introduction" },
  { href: "#setup", label: "Setup" },
  {
    href: "#results",
    label: "Results",
    children: [
      { href: "#figures", label: "Figures" },
      { href: "#tables", label: "Tables" },
    ],
  },
  { href: "#discussion", label: "Discussion" },
  { href: "#next", label: "Next" },
];

export async function RouterV2Paper() {
  const { user, authorized } = await requireLabMember();
  if (!user) redirect(`/login?next=/journal/${SLUG}`);
  if (!authorized) {
    const supabase = await createClient();
    await supabase.auth.signOut();
    redirect(`/login?next=/journal/${SLUG}`);
  }

  return (
    <PaperShell
      title="Structural fusion v2: oracle AST metrics on gold-patch files still don't beat the text floor"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations="SWE-bench Verified (500) · frozen ModernBERT-base"
      date="August 26, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-26"
      tags="router · structural-fusion · ast · oracle-ceiling · verified"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          If the router is told which files the gold patch touches, do Python
          AST counts plus frozen issue-text CLS beat text-only? No. Logistic
          fusion is {R.logistic.django.fusion.routeAuc.split(" ")[0]} Route-AUC
          / {R.logistic.django.fusion.auroc.split(" ")[0]} AUROC on django
          holdout (n={R.djangoN}) versus v1{" "}
          {R.logistic.django.text.routeAuc.split(" ")[0]} /{" "}
          {R.logistic.django.text.auroc.split(" ")[0]}. Target was ≥{" "}
          {R.target.djangoRouteAuc.toFixed(2)} / ≥{" "}
          {R.target.djangoAuroc.toFixed(2)}. Grouped{" "}
          {R.logistic.grouped.fusion.routeAuc.split(" ")[0]} is the same 0.589
          trap. Static structure is closed.
        </p>
      </PaperAbstract>

      <PaperToc items={toc} />

      <PaperSection id="introduction" number="1" title="Introduction">
        <p>
          v1 established that a frozen ModernBERT embedding of issue text alone
          ranks “will Qwen3-Coder resolve this task” barely above chance on
          held-out repos. Django holdout AUROC is{" "}
          {R.logistic.django.text.auroc} and Route-AUC is{" "}
          {R.logistic.django.text.routeAuc}. The grouped 5-fold headline
          (Route-AUC {R.logistic.grouped.text.routeAuc}) looked better but is
          mostly the django fold behaving near-chance averaged against a couple
          of small noisy folds — not a stable estimate.
        </p>
        <p>
          The open question from v1 was whether the router needs some structural
          view of the repo, or whether text is already the ceiling for a frozen
          encoder. This note answers a stronger version of that question: give
          the router the gold-patch file list, compute Python AST counts on
          those files at <code>base_commit</code>, and fuse the 12-d vector with
          frozen CLS. If that still fails, a leak-free file guesser has
          strictly less information and is not worth pursuing.
        </p>
      </PaperSection>

      <PaperSection id="setup" number="2" title="Setup">
        <p>
          Frozen CLS (768) plus a 12-d Python AST vector on gold-patch files:
          n_files, n_functions, n_imports, loc, mean/max cyclomatic, mean/max
          nesting, mean/max function LOC, mean arity, parse_errors. No fan-out.
          Metrics scaled on the train fold only. Weighted BCE. Fail-closed{" "}
          {R.n}/{R.n} cache ({R.cacheFiles} oracle files, {R.parseErrors} parse
          error). Prompt char caps were not applied. Encoder stayed frozen. Spec
          015 <code>run_train.py</code> unchanged.
        </p>
        <p>
          Headline head is logistic. MLP is a diagnostic for extra capacity.
          Django holdout (n={R.djangoN}) is the target split; grouped 5-fold is
          reported but not used as a ship criterion.
        </p>
      </PaperSection>

      <PaperSection id="results" number="3" title="Results">
        <p>
          Fusion does not beat the text floor on the split that matters.
          Metrics-only is a dead end. Grouped fusion {R.logistic.grouped.fusion.routeAuc}{" "}
          is the same trap as v1 grouped {R.logistic.grouped.text.routeAuc}.
        </p>

        <PaperSubsection id="figures" number="3.1" title="Figures">
          <RouterV2Figures />
        </PaperSubsection>

        <PaperSubsection id="tables" number="3.2" title="Tables">
          <PaperTable
            id="tab-target"
            caption="Table 1: Where we are versus the django holdout target. Logistic head, frozen encoder."
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
          <PaperTable
            id="tab-logistic"
            caption="Table 2: Logistic headline. Highlighted rows are django holdout (n=231). Accuracy stays under always-Qwen on django (58.0%)."
            highlight={(row) => row[1].includes("leave-django-out")}
            headers={["Arm", "Split", "Route-AUC", "AUROC", "Accuracy", "Brier"]}
            rows={[
              [
                "v1 text",
                "grouped 5-fold",
                R.logistic.grouped.text.routeAuc,
                R.logistic.grouped.text.auroc,
                R.logistic.grouped.text.acc,
                R.logistic.grouped.text.brier,
              ],
              [
                "v2 fusion",
                "grouped 5-fold",
                R.logistic.grouped.fusion.routeAuc,
                R.logistic.grouped.fusion.auroc,
                R.logistic.grouped.fusion.acc,
                R.logistic.grouped.fusion.brier,
              ],
              [
                "v2 metrics-only",
                "grouped 5-fold",
                R.logistic.grouped.metrics.routeAuc,
                R.logistic.grouped.metrics.auroc,
                R.logistic.grouped.metrics.acc,
                R.logistic.grouped.metrics.brier,
              ],
              [
                "v1 text",
                "leave-django-out n=231",
                R.logistic.django.text.routeAuc,
                R.logistic.django.text.auroc,
                R.logistic.django.text.acc,
                R.logistic.django.text.brier,
              ],
              [
                "v2 fusion",
                "leave-django-out n=231",
                R.logistic.django.fusion.routeAuc,
                R.logistic.django.fusion.auroc,
                R.logistic.django.fusion.acc,
                R.logistic.django.fusion.brier,
              ],
              [
                "v2 metrics-only",
                "leave-django-out n=231",
                R.logistic.django.metrics.routeAuc,
                R.logistic.django.metrics.auroc,
                R.logistic.django.metrics.acc,
                R.logistic.django.metrics.brier,
              ],
            ]}
          />
          <PaperTable
            id="tab-rest"
            caption="Table 3: Leave-repo reverse (hold n=269). Not averaged with django."
            headers={["Arm", "Route-AUC", "AUROC", "Accuracy"]}
            rows={[
              [
                "v1 text",
                R.logistic.rest.text.routeAuc,
                R.logistic.rest.text.auroc,
                R.logistic.rest.text.acc,
              ],
              [
                "v2 fusion",
                R.logistic.rest.fusion.routeAuc,
                R.logistic.rest.fusion.auroc,
                R.logistic.rest.fusion.acc,
              ],
              [
                "v2 metrics-only",
                R.logistic.rest.metrics.routeAuc,
                R.logistic.rest.metrics.auroc,
                R.logistic.rest.metrics.acc,
              ],
            ]}
          />
          <PaperTable
            id="tab-mlp"
            caption="Table 4: MLP diagnostic. Extra capacity fits noise. Metrics-only django Route-AUC 0.546 is a noisy cell (AUROC 0.521)."
            headers={[
              "Arm",
              "Grouped Route-AUC",
              "Grouped AUROC",
              "Django Route-AUC",
              "Django AUROC",
            ]}
            rows={[
              [
                "v1 text",
                R.mlp.grouped.text.routeAuc,
                R.mlp.grouped.text.auroc,
                R.mlp.django.text.routeAuc,
                R.mlp.django.text.auroc,
              ],
              [
                "v2 fusion",
                R.mlp.grouped.fusion.routeAuc,
                R.mlp.grouped.fusion.auroc,
                R.mlp.django.fusion.routeAuc,
                R.mlp.django.fusion.auroc,
              ],
              [
                "v2 metrics-only",
                R.mlp.grouped.metrics.routeAuc,
                R.mlp.grouped.metrics.auroc,
                R.mlp.django.metrics.routeAuc,
                R.mlp.django.metrics.auroc,
              ],
            ]}
          />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="discussion" number="4" title="Discussion">
        <p>
          Even with oracle file paths, AST counts add no lift over frozen issue
          text. A leak-free structural pipeline has strictly less information.
          SWE-Router prompt-only embeddings sit in the same place; their lift is
          K-turn trajectories (gpt-5-mini K=3 Route-AUC 0.694; deepseek K=2
          0.780 vs K=0 0.627). Next signal is that class. On escalation, restart
          the strong model from the original issue text.
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <ol className="list-decimal space-y-2 pl-6">
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
      </PaperSection>
    </PaperShell>
  );
}
