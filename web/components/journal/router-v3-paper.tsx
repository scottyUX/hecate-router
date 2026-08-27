import { RouterV3Figures } from "@/components/experiments/router-v3-figures";
import {
  PaperAbstract,
  PaperCallout,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V3 as R } from "@/lib/experiments/router-v3";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = "2026-08-26-v3-trajectory-router-spec";

const toc: PaperTocItem[] = [
  { href: "#introduction", label: "Introduction" },
  { href: "#rq", label: "Research question" },
  { href: "#hypothesis", label: "Hypothesis" },
  { href: "#setup", label: "Setup" },
  {
    href: "#results",
    label: "Results",
    children: [
      { href: "#prior", label: "Prior numbers" },
      { href: "#k0", label: "K=0 result" },
      { href: "#k3", label: "K=3 training" },
    ],
  },
  { href: "#next", label: "Future work" },
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
    href: "https://arxiv.org/abs/2607.00053",
    text: "Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., and Bogunovic, I. (2026). SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks. arXiv:2607.00053.",
  },
] as const;

export async function RouterV3Paper() {
  await requireJournalPage(`/journal/${SLUG}`);
  const k0 = R.k0.routeAuc.toFixed(3);
  const k3pct = ((R.k3.stepsDone / R.k3.stepsTotal) * 100).toFixed(0);

  return (
    <PaperShell
      title="K-turn trajectory-conditioned router (LoRA value head)"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations={`SWE-bench Verified (${R.n}) · rev ${R.rev} · IN PROGRESS — K=0 done, K=3 training`}
      date="August 27, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-27"
      tags="router · trajectory-conditioning · lora · k-turn · in-progress"
      toc={toc}
      glossary={glossaryEntries(
        "Route-AUC",
        "AUROC",
        "LoRA",
        "value head",
        "AST",
        "Brier",
        "K-turn",
        "QLoRA"
      )}
    >
      <PaperAbstract>
        <p>
          v1 frozen issue text and v2 oracle AST fusion (code-structure
          metrics from an abstract syntax tree) are chance on django holdout
          (n={R.djangoN}): Route-AUC {R.v1v2.djangoRouteAuc.text} /{" "}
          {R.v1v2.djangoRouteAuc.fusion} — routing quality as the
          cheap/expensive threshold is swept; 0.5 is chance. Static
          pre-execution signal is closed. The remaining candidate is what the
          cheap model discovers in its first few turns.
        </p>
        <p>
          K=0 — a separately trained 7B LoRA value head (Low-Rank Adaptation
          classifier on the last token that scores P(Qwen resolves); K=0 means
          issue text only, no agent turns) — is now measured: django Route-AUC{" "}
          {k0} (one seed, no CI), AUROC {R.k0.auroc.toFixed(3)} (pairwise
          ranking of successes vs failures; 0.5 is a coin flip). That is a
          large jump over the frozen-encoder floor on Route-AUC specifically,
          but AUROC barely moves, Brier is worse than v1/v2 (
          {R.k0.brier.toFixed(3)} vs 0.250; mean squared error of the raw
          probabilities, lower is better), and accuracy (
          {R.k0.accuracy.toFixed(2)}) sits below the always-Qwen baseline (
          {(R.djangoAlwaysSmall * 100).toFixed(1)}%). Treat {k0} as a
          promising, unconfirmed control value, not a settled number — Results
          discusses why those metrics can diverge and why one seed on a
          231-task holdout is not enough to trust it yet.
        </p>
        <p>
          K=3 (packed trajectory, same architecture) has not finished training.
          H1 and H2 are untested until its django-holdout eval runs. The
          practical effect of the K=0 result: the bar K=3 has to clear is no
          longer the old ~0.48 floor, it is {k0}.
        </p>
      </PaperAbstract>

      <PaperSection id="introduction" number="1" title="Introduction">
        <p>
          Related:{" "}
          <a href={R.related[0]}>text-only v1</a>
          {" · "}
          <a href={R.related[1]}>oracle fusion v2</a>
          . Both failed the django ship bar. SWE-Router argues that the missing
          signal is in the partial trajectory, not the prompt.<PaperCite n={4} />
        </p>
      </PaperSection>

      <PaperSection id="rq" number="2" title="Research question">
        <PaperCallout label="RQ1">
          <p>
            On the same 500-task Qwen3-Coder vs Claude 4 Opus pair, does a LoRA
            value head reading K=3 turns of Qwen’s own mini-SWE-agent trace
            improve django-holdout Route-AUC over a K=0 LoRA that sees only
            issue text?
          </p>
        </PaperCallout>
        <p>
          The control is a separately trained 7B LoRA on issue text, not frozen
          ModernBERT. Route-AUC is the only gate; AUROC is diagnostic. Grouped
          5-fold is reported after a django smoke, not instead of it.
        </p>
      </PaperSection>

      <PaperSection id="hypothesis" number="3" title="Hypothesis">
        <PaperCallout label="H1 — trajectory lift">
          <p>
            Packed K=3 django Route-AUC is clearly above the matched K=0 LoRA
            on the same split. With K=0 now measured at {k0}, this is the
            concrete bar — “clearly above” means outside K=0’s eventual seed
            variance, not a tick above a single point estimate. A null of
            “grouped looks alive, django still chance relative to K=0” would
            replicate SWE-Router’s repository-shift finding, not bury a
            failure.<PaperCite n={4} />
          </p>
        </PaperCallout>
        <PaperCallout label="H2 — stretch bar">
          <p>
            K=3 django Route-AUC ≥ {R.stretch.djangoRouteAuc.toFixed(2)}. This
            was written as a stretch goal before K=0 was measured. It is now a
            lower bar than K=0 itself ({k0}) — worth flagging explicitly: H2
            could be satisfied by K=3 while H1 is rejected, if K=3 clears{" "}
            {R.stretch.djangoRouteAuc.toFixed(2)} but sits below K=0’s {k0}.
            That outcome would mean trajectory conditioning still underperforms
            a trajectory-blind control, and should be reported as an H1
            rejection regardless of H2.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="setup" number="4" title="Setup">
        <p>
          Weak/strong pair unchanged: Qwen3-Coder-480B vs Claude 4 Opus,
          mini-SWE-agent v1.0.0, same 500 labels.<PaperCite n={[2, 3]} /> Value
          head: Qwen2.5-Coder-7B-Instruct, LoRA r=32 α=64, last-token logits,
          8192 context, QLoRA (4-bit LoRA) on L4. A turn is a user/observation
          boundary.
          Packing is only inside the K=3 arm. {R.paperDeviation} Trained on{" "}
          <code>{R.gpu.instance}</code>, not <code>hecate-exec</code>.
        </p>
      </PaperSection>

      <PaperSection id="results" number="5" title="Results">
        <PaperCallout label="H1 / H2: K=0 measured, K=3 untested">
          <p>
            RQ1 cannot be answered yet — one arm of the comparison is missing.
          </p>
        </PaperCallout>

        <PaperSubsection id="prior" number="5.1" title="Prior numbers">
          <PaperTable
            id="tab-v3-hypotheses"
            caption="Table 1: Pre-registered claims. Confirmatory split is django holdout."
            headers={["Claim", "Test", "Observed", "Decision"]}
            rows={[
              [
                "H1 — K=3 beats K=0 LoRA",
                "django Route-AUC, one seed then 5-fold",
                `K=0 done (${k0}); K=3 not yet scored`,
                "Untested",
              ],
              [
                "H2 — stretch bar",
                `django Route-AUC ≥ ${R.stretch.djangoRouteAuc.toFixed(2)}`,
                "K=0 already clears this on its own; K=3 unmeasured",
                "Untested",
              ],
              [
                "RQ1 — traces beat issue text",
                "H1 accepted",
                "Cannot evaluate without K=3",
                "Open",
              ],
            ]}
          />
          <PaperTable
            id="tab-v3-swerouter-k"
            caption="Table 2: SWE-Router Route-AUC by K, both pairs, SWE-Bench Verified mix-1 (Son et al., 2026, Table 2). Mix-1 is not a repo holdout — shown for calibration, not as the expected transfer number."
            headers={["Pair", "K=0", "K=1", "K=2", "K=3", "K=4"]}
            rows={[
              [
                "gpt-5-mini → gemini-3-pro",
                R.sweRouter.mix1.gpt5mini.k0.toFixed(3),
                R.sweRouter.mix1.gpt5mini.k1.toFixed(3),
                R.sweRouter.mix1.gpt5mini.k2.toFixed(3),
                R.sweRouter.mix1.gpt5mini.k3.toFixed(3),
                R.sweRouter.mix1.gpt5mini.k4.toFixed(3),
              ],
              [
                "deepseek-v3.2 → gemini-3-pro",
                R.sweRouter.mix1.deepseek.k0.toFixed(3),
                R.sweRouter.mix1.deepseek.k1.toFixed(3),
                R.sweRouter.mix1.deepseek.k2.toFixed(3),
                R.sweRouter.mix1.deepseek.k3.toFixed(3),
                R.sweRouter.mix1.deepseek.k4.toFixed(3),
              ],
            ]}
          />
          <PaperTable
            id="tab-v3-smith"
            caption="Table 3: SWE-Router Route-AUC, SWE-Smith repo-disjoint test — the closer analogue to django holdout, on a different dataset."
            headers={["Pair", "K=0", "K=3"]}
            rows={[
              [
                "gpt-5-mini → gemini-3-pro",
                R.sweRouter.smithRepoDisjoint.gpt5mini.k0.toFixed(3),
                R.sweRouter.smithRepoDisjoint.gpt5mini.k3.toFixed(3),
              ],
              [
                "deepseek-v3.2 → gemini-3-pro",
                R.sweRouter.smithRepoDisjoint.deepseek.k0.toFixed(3),
                R.sweRouter.smithRepoDisjoint.deepseek.k3.toFixed(3),
              ],
            ]}
          />
          <PaperTable
            id="tab-v3-floor"
            caption="Table 4: Hecate v1/v2 floor on this pair, plus K=0. Grouped 5-fold is the django-weighted trap; do not headline it."
            highlight={(row) => row[0].includes("Route-AUC") && row[0].includes("Django")}
            headers={[
              "Metric",
              "v1 text",
              "v2 fusion",
              "K=0 LoRA (1 seed, no CI)",
              "Role",
            ]}
            rows={[
              [
                "Django holdout Route-AUC",
                R.v1v2.djangoRouteAuc.text,
                R.v1v2.djangoRouteAuc.fusion,
                k0,
                "Primary gate for H1/H2",
              ],
              [
                "Django holdout AUROC",
                R.v1v2.djangoAuroc.text,
                R.v1v2.djangoAuroc.fusion,
                R.k0.auroc.toFixed(3),
                "Diagnostic only — do not gate",
              ],
              [
                "Django holdout accuracy",
                R.v1v2.djangoAcc.text,
                R.v1v2.djangoAcc.fusion,
                R.k0.accuracy.toFixed(3),
                `Below always-Qwen (${R.djangoAlwaysSmall.toFixed(3)})`,
              ],
              [
                "Django holdout Brier",
                R.v1v2.djangoBrier.text,
                R.v1v2.djangoBrier.fusion,
                R.k0.brier.toFixed(3),
                "Lower is better — K=0 is worse than either prior arm",
              ],
              [
                "Grouped 5-fold Route-AUC",
                R.v1v2.groupedRouteAuc.text,
                R.v1v2.groupedRouteAuc.fusion,
                "not yet run",
                "Report, do not headline",
              ],
            ]}
          />
        </PaperSubsection>

        <PaperSubsection
          id="k0"
          number="5.2"
          title="K=0 result — read carefully before trusting it"
        >
          <p>
            K=0’s Route-AUC ({k0}) moved far more than its AUROC (
            {R.k0.auroc.toFixed(3)}), and its Brier and accuracy both got worse
            relative to v1/v2 rather than better. This is not necessarily
            contradictory. Route-AUC integrates a threshold-swept
            cost-vs-resolved-rate curve and is disproportionately sensitive to
            whether the model correctly orders the extremes of the distribution
            — the clearly Opus-only tasks versus the clearly safe-to-route-cheap
            ones — while AUROC averages ranking quality uniformly across every
            pair, muddled middle included. Both metrics are threshold-free, so
            neither depends on the raw calibrated probability being right, which
            is why a model can have a low F1 ({R.k0.f1.toFixed(2)}) and
            below-base-rate accuracy at the 0.5 cutoff while still producing a
            Route-AUC-relevant ordering. That combination is a plausible,
            internally consistent story — a model that reliably identifies a
            distinctive subset of pivotal tasks while being poorly calibrated
            everywhere else — but it is also exactly the fingerprint of a
            statistic that can swing a lot between seeds on a 231-task holdout,
            since a curve-integral metric this sensitive to a handful of
            pivotal cases has real variance that has not been measured yet. K=0
            is one seed. No std is reported because none exists yet.
          </p>
          <RouterV3Figures />
        </PaperSubsection>

        <PaperSubsection id="k3" number="5.3" title="K=3 — training, not yet scored">
          <p>
            Epoch 0 complete (mean loss {R.k3.epoch0MeanLoss.toFixed(2)}, above
            the ln(2) ≈ {R.k3.ln2.toFixed(3)} trivial-classifier baseline — not
            unusual for a fresh LoRA at epoch 0, but worth confirming it drops
            below that baseline by the final epoch rather than assuming it
            does). Currently in epoch 1 of {R.k3.epochs}, roughly {k3pct}% of
            total steps ({R.k3.stepsDone.toLocaleString()} of{" "}
            {R.k3.stepsTotal.toLocaleString()}). K=3 truncation at 8192 tokens
            measured at {(R.traces.k3TruncationRate * 100).toFixed(1)}% (
            {R.traces.k3TruncatedN} of 500; median{" "}
            {R.traces.medianTokens.toLocaleString()} tokens, max{" "}
            {R.traces.maxTokens.toLocaleString()}) — low enough that truncation
            is not expected to be a confound. No django-holdout Route-AUC yet;
            the gate has not run.
          </p>
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="next" number="6" title="Future work">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Let K=3 finish training and run the django-holdout eval — nothing
            in Table 1 changes until that number exists.
          </li>
          <li>
            Apply the gate as specified in H1: compare K=3’s django Route-AUC
            against K=0’s {k0}, not against the old v1/v2 floor.
          </li>
          <li>
            If K=3 clearly beats K=0: proceed to the 5-fold × 3-seed protocol
            plus the second holdout (<code>{R.secondHoldout}</code>, n=75)
            before any external claim, per the original protocol. K=0 also
            needs re-running across seeds at that point — a single-seed {k0}{" "}
            is not the number that goes in a final table.
          </li>
          <li>
            If K=3 does not clearly beat K=0: write that up as a genuine
            finding, not a failure — it would replicate SWE-Router’s own
            repository-shift result (Table 3) on an independent dataset and
            model pair, which is itself worth reporting.
          </li>
          <li>
            Stop <code>{R.gpu.instance}</code> once the gate decision is logged
            — idle L4 time is the one way this experiment’s cost stops being
            small.
          </li>
        </ol>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
