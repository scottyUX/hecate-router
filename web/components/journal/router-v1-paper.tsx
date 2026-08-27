import { RouterV1Figures, RouterV1RouteAucCurve } from "@/components/experiments/router-v1-figures";
import {
  PaperAbstract,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { RouterArchitectureV1 } from "@/components/paper/router-architecture";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V1 as R } from "@/lib/experiments/router-v1";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = "2026-08-25-text-only-router-v1";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  {
    href: "#method",
    label: "Method",
    children: [{ href: "#fig-arch", label: "Architecture" }],
  },
  {
    href: "#result",
    label: "Result",
    children: [
      { href: "#fig-route-auc-curve", label: "Route-AUC curve" },
      { href: "#figures", label: "More figures" },
      { href: "#tables", label: "Tables" },
    ],
  },
  { href: "#interpretation", label: "Interpretation" },
  { href: "#next", label: "Next" },
  { href: "#notes", label: "Notes" },
  { href: "#references", label: "References" },
];

const references = [
  {
    id: 1,
    href: "https://arxiv.org/abs/2310.06770",
    text: "Jimenez, C. E. et al. (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR. arXiv:2310.06770.",
  },
  {
    id: 2,
    href: "https://openai.com/index/introducing-swe-bench-verified/",
    text: "Chowdhury, N. et al. (2024). Introducing SWE-bench Verified. OpenAI.",
  },
  {
    id: 3,
    href: "https://github.com/SWE-agent/mini-swe-agent",
    text: "Yang, J. et al. (2025). mini-SWE-agent. Princeton NLP / SWE-agent.",
  },
  {
    id: 4,
    href: "https://arxiv.org/abs/2412.13663",
    text: "Warner, B. et al. (2024). Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference. arXiv:2412.13663.",
  },
  {
    id: 5,
    href: "https://arxiv.org/abs/2406.18665",
    text: "Ong, I. et al. (2024). RouteLLM: Learning to Route LLMs with Preference Data. arXiv:2406.18665.",
  },
  {
    id: 6,
    href: "https://arxiv.org/abs/2607.00053",
    text: "Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., and Bogunovic, I. (2026). SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks. arXiv:2607.00053.",
  },
] as const;

export async function RouterV1Paper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Text-only router v1 (frozen embedding, logistic/MLP head)"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations="SWE-bench Verified (500) · closed — superseded by v2, v3"
      date="August 27, 2026 (entry authored retroactively; original run predates this project's other write-ups)"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-27"
      tags="router · text-only · modernbert · verified · closed"
      toc={toc}
      glossary={glossaryEntries("Route-AUC", "AUROC", "CLS", "MLP", "Brier")}
    >
      <PaperAbstract>
        <p>
          First router experiment on the Qwen3-Coder-480B-A35B-Instruct vs
          Claude 4 Opus pair. Question: does the GitHub issue’s own text,
          encoded by a general-purpose frozen embedding, predict whether the
          cheap model resolves the task — before either model has run? This is
          the strictest version of the router problem: no repo, no diffs, no
          tests, no traces, matching Hecate’s original pre-execution,
          reverse-proxy deployment constraint.<PaperCite n={[1, 2]} />
        </p>
        <p>
          Django holdout (n={R.djangoN}): Route-AUC {R.logistic.django.routeAuc}{" "}
          — chance. Logistic and MLP heads land at the same number, so the
          failure is in the frozen embedding, not the head’s capacity. Grouped
          5-fold {R.logistic.grouped.routeAuc} is a django-weighted trap, not a
          working router.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          Prompt-only LLM routers decide from the query string
          alone.<PaperCite n={5} /> In agentic software engineering that string
          can look the same for a one-line typo and a multi-file refactor,
          which is a Bayes-error floor.<PaperCite n={6} /> v1 measures that
          floor on this lab’s pair: Qwen3-Coder-480B vs Claude 4 Opus,
          mini-SWE-agent v1.0.0, SWE-bench Verified (500).<PaperCite n={[2, 3]} />
        </p>
        <p>
          If a cheap frozen encoder of issue text already ranks “will Qwen
          resolve this” above chance, later work can stay pre-execution. If it
          does not, the lab has to look elsewhere — structure (v2) or the
          cheap model’s own first turns (v3).
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <RouterArchitectureV1 />
        <p>
          Backbone: <code>answerdotai/ModernBERT-base</code>, frozen, no
          fine-tuning.<PaperCite n={4} /> Issue text → CLS embedding (the
          encoder’s 768-d classification-token summary) → a small trained head
          (logistic regression, and separately an MLP) predicting P(resolve).
          Only the head is trained; the encoder never sees a gradient. Recipe:
          4 epochs, batch 8, AdamW, lr 2e-5, binary cross-entropy. 2048-token
          truncation hits {(R.truncation * 100).toFixed(1)}% of examples.
        </p>
        <p>
          Primary split: leave-django-out (train on {R.restN} tasks from the
          other 11 repos, evaluate on the {R.djangoN} django tasks) — the
          genuine repository-shift test. Grouped 5-fold × 3-seed is also
          reported, not headlined (django’s 46% dataset share makes it
          high-variance and unrepresentative — the “0.589 trap”).
        </p>
        <p>
          Primary metric is Route-AUC: routing quality as the cheap/expensive
          threshold is swept (0.5 is chance). AUROC (pairwise ranking of
          Qwen-successes vs failures; 0.5 is a coin flip) and Brier (mean
          squared error of predicted probabilities; 0.25 is an uninformative
          0.5 guess) are secondary.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <p>Django holdout (n={R.djangoN}):</p>
        <PaperTable
          id="tab-v1-django"
          caption="Table 1: Leave-django-out, logistic head, 3 seeds. Confirmatory split."
          headers={["Metric", "Value"]}
          rows={[
            ["Route-AUC", R.logistic.django.routeAuc],
            ["AUROC", R.logistic.django.auroc],
            ["Accuracy", R.logistic.django.acc],
            ["Brier", R.logistic.django.brier],
            [
              "Grouped 5-fold Route-AUC",
              `${R.logistic.grouped.routeAuc} (high-variance, not headlined)`,
            ],
          ]}
        />
        <p>
          Logistic and MLP heads landed at the same chance-level Route-AUC
          (MLP {R.mlp.django.routeAuc}) — the failure is in the frozen
          embedding, not the head’s capacity.
        </p>
        <p>
          Route-AUC endpoints, django holdout (n={R.djangoN}): always-Opus 70.6%
          (163/231), always-Qwen 58.0% (134/231), oracle (either model
          resolves) 74.5% (172/231). Same trio on the full 500-task set: 67.6%
          / 55.4% / 71.4%, with 258 both-win tasks (~52% of the dataset — the
          “free savings” a working router would capture at zero quality cost).
        </p>

        <RouterV1RouteAucCurve />
        <p>
          The reconstructed curve (seed 0, full 101-point sweep) wobbles above
          and below the no-signal diagonal — the straight line between the
          always-Qwen and always-Opus endpoints — rather than consistently
          bowing above it. Visually, this is what a chance-or-slightly-below
          Route-AUC should look like as an actual curve, not just a headline
          number. Separately: the oracle ceiling (74.5%) sits above the
          always-Opus endpoint (70.6%, left of the chart), because a slice of
          django tasks are resolved only by Qwen. Routing everything to the
          strong model still cannot reach the theoretical ceiling.
        </p>

        <PaperSubsection id="figures" number="3.1" title="More figures">
          <RouterV1Figures />
        </PaperSubsection>

        <PaperSubsection id="tables" number="3.2" title="Tables">
          <PaperTable
            id="tab-v1-ceiling"
            caption="Table 2: Label ceiling on the full 500-task set, before any router. Headroom vs always-Opus is only the 19 Qwen-only wins."
            headers={["Policy", "Resolved", "Note"]}
            rows={[
              ["Always Qwen", `${(R.alwaysSmall * 100).toFixed(1)}% (277/500)`, "Cheap default"],
              ["Always Opus", `${(R.alwaysLarge * 100).toFixed(1)}% (338/500)`, "Expensive default"],
              ["Oracle", `${(R.oracle * 100).toFixed(1)}% (357/500)`, `Headroom ${R.headroomPp}pp`],
              [
                "Complementarity",
                `${R.complementarity.smallOnly} / ${R.complementarity.both} / ${R.complementarity.opusOnly} / ${R.complementarity.neither}`,
                "Qwen-only / both / Opus-only / neither",
              ],
            ]}
          />
          <PaperTable
            id="tab-v1-headline"
            caption="Table 3: Frozen-head means. Highlighted row is the confirmatory django holdout."
            highlight={(row) => row[1].includes("leave-django-out")}
            headers={["Head", "Split", "Route-AUC", "AUROC", "Accuracy"]}
            rows={[
              ["logistic", "grouped 5-fold", R.logistic.grouped.routeAuc, R.logistic.grouped.auroc, R.logistic.grouped.acc],
              ["MLP", "grouped 5-fold", R.mlp.grouped.routeAuc, R.mlp.grouped.auroc, R.mlp.grouped.acc],
              ["logistic", "leaky stratified", R.logistic.grouped.leakyRouteAuc, "—", "—"],
              ["logistic", "leave-django-out n=231", R.logistic.django.routeAuc, R.logistic.django.auroc, R.logistic.django.acc],
              ["MLP", "leave-django-out n=231", R.mlp.django.routeAuc, R.mlp.django.auroc, "—"],
              ["logistic", "leave-rest n=269", R.logistic.rest.routeAuc, R.logistic.rest.auroc, R.logistic.rest.acc],
            ]}
          />
          <PaperTable
            id="tab-v1-folds"
            caption="Table 4: Logistic grouped, seed 0. Django is one test fold every seed — 46% of the data, sitting at chance."
            highlight={(row) => row[0].includes("django")}
            headers={["Test fold", "n", "Route-AUC", "AUROC"]}
            rows={[
              ["django only", "231", "0.45", "0.51"],
              ["sympy only", "75", "0.84", "0.57"],
              ["sphinx + pytest + seaborn", "65", "0.51", "0.57"],
              ["matplotlib mix", "65", "0.55", "0.50"],
              ["sklearn + astropy + pylint", "64", "0.35", "0.34"],
            ]}
          />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          Route-AUC ≈ 0.48 (and the reconstructed curve visibly hugging or
          dipping under the no-signal line) means a frozen general-purpose
          text embedding of the issue alone carries no usable pre-execution
          routing signal under a genuine repository shift, regardless of head
          capacity (logistic and MLP agree). Accuracy {R.logistic.django.acc}{" "}
          sits under django always-Qwen (58.0%). Brier {R.logistic.django.brier}{" "}
          is an uninformative 0.5 guess.
        </p>
        <p>
          This is not a join bug: labels matched published 55.4% / 67.6% at
          500/500. Truncation at 2048 tokens is not the failure mode. This
          closed static, unstructured pre-execution signal as a direction and
          motivated{" "}
          <a href="/journal/2026-08-26-oracle-metrics-fusion-v2">
            v2 (oracle AST structural fusion — also chance)
          </a>{" "}
          and, after that also failed,{" "}
          <a href="/journal/2026-08-26-v3-trajectory-router-spec">
            v3’s shift to execution-grounded trajectory signal
          </a>
          .
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <p>
          Already superseded — v2 and v3 are both later, separate experiments.
          No further work planned on v1 itself. Do not unfreeze BERT on issue
          text. Do not treat grouped 0.589 as a working router.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <ul className="list-disc space-y-2 pl-6">
          <li>
            Curve reconstruction (added 2026-08-27). The original
            leave-django-out head was never checkpointed, so the λ-sweep was
            refit from cached CLS embeddings on the 269 non-django tasks only
            and evaluated on the 231-task django holdout. Per-seed Route-AUC
            matched the archived figures bit-for-bit (seed 0 = 0.445, seed 1
            = 0.484, seed 2 = 0.503; mean 0.477). The reconstruction did not
            reuse the all-500 grouped head, which would have leaked django
            into training.
          </li>
          <li>
            The curve figure shows seed 0 only (Route-AUC 0.445), not the
            3-seed mean (0.477) — worth remembering when reading it, since
            seed 0 sits slightly below the mean.
          </li>
          <li>
            v1 is CPU-only. It was never run on the execution or trajectory
            GPU boxes.
          </li>
        </ul>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
