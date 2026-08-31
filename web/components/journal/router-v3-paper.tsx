import {
  RouterV3Figures,
  RouterV3RouteAucCurve,
} from "@/components/experiments/router-v3-figures";
import {
  PaperAbstract,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { RouterArchitectureV3 } from "@/components/paper/router-architecture";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V3 as R } from "@/lib/experiments/router-v3";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = "2026-08-26-v3-trajectory-router-spec";

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
      { href: "#tab-decisions", label: "Decisions" },
      { href: "#k0", label: "K=0" },
      { href: "#k3", label: "K=3" },
      { href: "#fig-route-auc-curve", label: "Route-AUC curve" },
      { href: "#figures", label: "More figures" },
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
    href: "https://arxiv.org/abs/2607.00053",
    text: "Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., and Bogunovic, I. (2026). SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks. arXiv:2607.00053.",
  },
] as const;

export async function RouterV3Paper() {
  await requireJournalPage(`/journal/${SLUG}`);
  const k0 = R.k0.routeAuc.toFixed(3);
  const k3 = R.k3.routeAuc.toFixed(3);
  const drop = Math.abs(R.k3.routeAuc - R.k0.routeAuc).toFixed(3);
  const epochLoss = R.k3.epochMeanLoss.map((x) => x.toFixed(3)).join(" → ");
  const trainTruncPct = (
    (R.k3.trainTruncatedRows / R.k3.nTrainRows) *
    100
  ).toFixed(1);

  return (
    <PaperShell
      title="K-turn trajectory router v3 (LoRA value head)"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations={`SWE-bench Verified (${R.n}) · rev ${R.rev} · COMPLETE — H1 rejected, RQ2 yes`}
      date="August 31, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-31"
      tags="router · trajectory-conditioning · lora · k-turn · h1-rejected · rq2"
      toc={toc}
      glossary={glossaryEntries(
        "Route-AUC",
        "AUROC",
        "LoRA",
        "value head",
        "Brier",
        "K-turn",
        "QLoRA"
      )}
    >
      <PaperAbstract>
        <p>
          Two questions on the same leave-django-out smoke (train {R.restN}{" "}
          non-django / test {R.djangoN} django). RQ1 is whether extra turns
          help. RQ2 is whether a trained 7B LoRA beats the frozen v1/v2 floor
          at all.
        </p>
        <p>
          RQ1: no. Packed K=3 django Route-AUC {k3} sits {drop} below a
          matched K=0 LoRA that sees only issue text ({k0}, one seed). H1 is
          rejected. H2’s stretch bar (≥{R.stretch.djangoRouteAuc.toFixed(2)}) is
          nominally cleared and was pre-registered as a non-outcome. Trajectory
          conditioning does not beat a trajectory-blind control on this
          repository-shift holdout.
        </p>
        <p>
          RQ2: yes, on Route-AUC. v1 frozen issue text and v2 oracle AST fusion
          are chance ({R.v1v2.djangoRouteAuc.text} /{" "}
          {R.v1v2.djangoRouteAuc.fusion}). Both LoRA arms clear that floor: K=0{" "}
          {k0}, K=3 {k3}. The lift is the fine-tune, not the traces. K=0 is the
          clean version of that result. AUROC barely moved; calibration got
          worse. One seed, no CI.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          Related:{" "}
          <a href={R.related[0]}>text-only v1</a>
          {" · "}
          <a href={R.related[1]}>oracle fusion v2</a>
          . Both failed the django ship bar. SWE-Router argues that the missing
          signal is in the partial trajectory, not the prompt.<PaperCite n={4} />
          This experiment tests that claim on the same Qwen3-Coder-480B vs
          Claude 4 Opus pair.
        </p>
        <p>
          RQ1 (pre-registered gate): does a LoRA value head reading K=3 turns
          of Qwen’s own mini-SWE-agent trace improve django-holdout Route-AUC
          over a K=0 LoRA that sees only issue text? Answered: no. The control
          is a separately trained 7B LoRA, not frozen ModernBERT.
        </p>
        <p>
          RQ2 (scored on the same run; not the gate): does that 7B LoRA beat
          frozen v1/v2 on django-holdout Route-AUC? Answered: yes. K=0 {k0} and
          K=3 {k3} both sit well above {R.v1v2.djangoRouteAuc.text} /{" "}
          {R.v1v2.djangoRouteAuc.fusion}. This split is a generalist test —
          train on other repos, route django. Route-AUC is the only gate for
          RQ1; AUROC is diagnostic for both.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <RouterArchitectureV3 />
        <p>
          Weak/strong pair unchanged: Qwen3-Coder-480B vs Claude 4 Opus,
          mini-SWE-agent v1.0.0, same 500 labels.<PaperCite n={[1, 2, 3]} />{" "}
          Value head: Qwen2.5-Coder-7B-Instruct, LoRA r=32 α=64, last-token
          logits scoring P(Qwen resolves), 8192 context, QLoRA on one L4. A
          turn is a user/observation boundary. Packing is only inside the K=3
          arm. {R.paperDeviation} Trained on <code>{R.gpu.instance}</code>, not
          the execution box. The instance is now stopped.
        </p>
        <p>
          Leave-django-out is the generalist protocol: fit on {R.restN}{" "}
          non-django tasks, evaluate on {R.djangoN} django tasks. H1
          (trajectory lift): packed K=3 django Route-AUC is clearly above the
          matched K=0 LoRA on that split. With K=0 measured at {k0}, that is
          the bar. H2 (stretch, written before K=0 was measured): K=3 ≥{" "}
          {R.stretch.djangoRouteAuc.toFixed(2)}. H2 can pass while H1 fails;
          that combination is reported as an H1 rejection. H1 and H2 are left
          as originally pre-registered. RQ2 uses the same numbers against the
          frozen floor; it was not a pre-registered pass/fail gate.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <p>
          H1 rejected. RQ1 answered: no. RQ2 answered: yes on Route-AUC (one
          seed). H2 nominally cleared but reported as an H1 rejection per the
          pre-registered decision rule.
        </p>
        <PaperTable
          id="tab-decisions"
          caption="Table 1: Claims. H1, H2, and RQ1 were pre-registered. RQ2 is scored on the same smoke; it was not the gate. Confirmatory split is django holdout."
          highlight={(row) =>
            row[0].startsWith("H1") || row[0].startsWith("RQ2")
          }
          headers={["Claim", "Test", "Observed", "Decision"]}
          rows={[
            [
              "H1 — K=3 beats K=0 LoRA",
              "django Route-AUC, one seed",
              `K=0 = ${k0}; K=3 = ${k3}`,
              `Rejected — K=3 is ${drop} below K=0`,
            ],
            [
              "H2 — stretch bar",
              `django Route-AUC ≥ ${R.stretch.djangoRouteAuc.toFixed(2)}`,
              `K=3 = ${k3}`,
              "Nominally met; reported as an H1 rejection, not a partial success",
            ],
            [
              "RQ1 — traces beat issue text",
              "H1 accepted",
              "H1 rejected",
              "No — packed K=3 underperforms the trajectory-blind K=0 control",
            ],
            [
              "RQ2 — 7B LoRA beats frozen v1/v2",
              "django Route-AUC vs v1/v2 ~0.48",
              `K=0 = ${k0}; K=3 = ${k3}`,
              "Yes on Route-AUC — the fine-tune lifts; extra turns do not",
            ],
          ]}
        />
        <PaperTable
          id="tab-swe-mix1"
          caption="Table 2: SWE-Router Route-AUC by K on SWE-Bench Verified mix-1 (Son et al., 2026, Table 2). Mix-1 is not a repo holdout — calibration only, not the expected transfer number."
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
          id="tab-swe-smith"
          caption="Table 3: SWE-Router Route-AUC, SWE-Smith repo-disjoint test — the closer analogue to django holdout, on a different dataset. Both pairs also fail to clearly beat K=0 at K=3."
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
          id="tab-v3-gate"
          caption="Table 4: Hecate v1/v2/K=0/K=3 on this pair. Highlighted row is the RQ1 gate and the RQ2 comparison. Grouped 5-fold is the django-weighted trap; do not headline it. K=0 and K=3 are one seed; v1/v2 are 3-seed means."
          highlight={(row) => row[0].includes("Route-AUC") && row[0].includes("Django")}
          headers={[
            "Metric",
            "v1 text",
            "v2 fusion",
            "K=0 LoRA",
            "K=3 LoRA",
          ]}
          rows={[
            [
              "Django holdout Route-AUC",
              R.v1v2.djangoRouteAuc.text,
              R.v1v2.djangoRouteAuc.fusion,
              k0,
              k3,
            ],
            [
              "Django holdout AUROC",
              R.v1v2.djangoAuroc.text,
              R.v1v2.djangoAuroc.fusion,
              R.k0.auroc.toFixed(3),
              R.k3.auroc.toFixed(3),
            ],
            [
              "Django holdout accuracy",
              R.v1v2.djangoAcc.text,
              R.v1v2.djangoAcc.fusion,
              R.k0.accuracy.toFixed(3),
              R.k3.accuracy.toFixed(3),
            ],
            [
              "Django holdout Brier",
              R.v1v2.djangoBrier.text,
              R.v1v2.djangoBrier.fusion,
              R.k0.brier.toFixed(3),
              R.k3.brier.toFixed(3),
            ],
            [
              "Grouped 5-fold Route-AUC",
              R.v1v2.groupedRouteAuc.text,
              R.v1v2.groupedRouteAuc.fusion,
              "not run",
              "not run",
            ],
          ]}
        />

        <PaperSubsection id="k0" number="3.1" title="K=0 (issue text, 7B LoRA)">
          <p>
            Route-AUC jumped over the frozen floor; AUROC barely moved (
            {R.k0.auroc.toFixed(3)}); accuracy ({R.k0.accuracy.toFixed(3)}) sits
            below always-Qwen ({(R.djangoAlwaysSmall * 100).toFixed(1)}%); Brier
            got worse ({R.k0.brier.toFixed(3)} vs 0.250). That combination can
            be internally consistent: Route-AUC cares about ordering the
            extremes, while AUROC averages every pair. It is also the
            fingerprint of a statistic that can swing between seeds on a
            231-task holdout. Treat {k0} as the RQ2 estimate for this smoke,
            not a settled number — and not as evidence that trajectory
            conditioning works.
          </p>
        </PaperSubsection>

        <PaperSubsection id="k3" number="3.2" title="K=3 (packed trajectory)">
          <p>
            Training finished at epoch {R.k3.epochs} of {R.k3.epochs} (
            {R.k3.steps} steps), ~{R.k3.trainHours} hours on{" "}
            <code>{R.gpu.instance}</code>. Packed rows: {R.k3.nTrainRows} ={" "}
            {R.k3.nTrain} tasks × K∈{"{0..4}"}. Epoch-mean training loss:{" "}
            {epochLoss}. That clears ln(2) ≈ {R.ln2.toFixed(3)} at epoch 2
            (epoch 1 is still {R.k3.epochMeanLoss[1].toFixed(3)}), with the
            steep drop in the last epoch (
            {R.k3.epochMeanLoss[3].toFixed(3)} →{" "}
            {R.k3.epochMeanLoss[4].toFixed(3)}).
          </p>
          <p>
            During the actual K=3 fit, the Qwen tokenizer hit 8192 on{" "}
            {R.k3.trainTruncatedRows} of {R.k3.nTrainRows} packed rows every
            epoch ({trainTruncPct}%; seq p50={R.k3.trainSeqP50}, max=
            {R.k3.trainSeqMax}). That is the truncation figure that matters. The{" "}
            <code>results.json</code> block of 0/{R.n} (median{" "}
            {R.traces.whitespaceMedianTokens}) is a whitespace-split proxy and
            undercounts code tokens. An earlier HF-tokenizer audit of the 500
            traces was {(R.traces.hfAuditTruncationRate * 100).toFixed(1)}% (
            {R.traces.hfAuditTruncatedN}/{R.n}, median{" "}
            {R.traces.hfAuditMedianTokens}). None of these is a first-order
            confound for the gate.
          </p>
          <p>
            Django Route-AUC is {k3} versus K=0’s {k0}. H1 / RQ1 rejected.
            Against the frozen floor, {k3} still clears RQ2. AUROC{" "}
            {R.k3.auroc.toFixed(3)} vs {R.k0.auroc.toFixed(3)} is a 0.010 tick
            on one seed — not a ranking rescue. Brier {R.k3.brier.toFixed(3)} is
            worse than a constant-0.5 classifier (0.250). At the selected λ the
            routed resolved rate matches always-Opus (
            {(R.k3.bestRouteRate * 100).toFixed(1)}%), so the head is not
            finding cheap wins above the expensive default.
          </p>
        </PaperSubsection>

        <PaperSubsection id="figures" number="3.3" title="Figures">
          <RouterV3RouteAucCurve />
          <RouterV3Figures />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          RQ1: no. On this pair, three turns of Qwen’s own trace do not improve
          django-holdout routing over a LoRA that sees only the issue. The
          drop vs K=0 is large enough that a 5-fold × 3-seed protocol on this
          K=3 recipe is not justified. Extra turns also failed in SWE-Router
          when the test repo was held out, and helped only when train and test
          shared the same mix.<PaperCite n={4} /> Django holdout is the second
          kind of test. That cross-study pattern is the RQ1 finding, not a
          failure to bury.
        </p>
        <p>
          RQ2: yes, on Route-AUC. A trained 7B LoRA ranks django holdout tasks
          well above frozen ModernBERT (v1) and oracle AST fusion (v2). K=0 is
          the clean measurement: same architecture as K=3, no trajectory
          tokens, {k0} vs ~0.48. K=3 ({k3}) also clears that floor and still
          loses the gate. The positive outcome is “fine-tune the 7B head,” not
          “pack traces.” AUROC barely moved ({R.k0.auroc.toFixed(3)} /{" "}
          {R.k3.auroc.toFixed(3)} vs v1/v2 ~0.52); accuracy sits below
          always-Qwen; K=3 Brier {R.k3.brier.toFixed(3)} is worse than guessing
          0.5. One seed.
        </p>
        <p>
          Route-AUC dropped ({k0} → {k3}) while AUROC ticked {R.k0.auroc.toFixed(3)}{" "}
          → {R.k3.auroc.toFixed(3)} and Brier got substantially worse (
          {R.k0.brier.toFixed(3)} → {R.k3.brier.toFixed(3)}). A small AUROC
          movement on one seed does not mean pairwise ranking is better; the
          routing decision depends on the extremes that Route-AUC actually
          measures.
        </p>
        <p>
          This smoke tested a generalist router (train off django, test on
          django). RQ2 says that generalist LoRA has ranking lift the frozen
          encoder did not. It does not say a specialist — train and test on
          the same task type / similar repos — would look the same, and it
          does not revive H1.
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Do not scale this K=3 recipe to 5-fold × 3-seed or{" "}
            <code>{R.secondHoldout}</code> as a generalist. RQ1 already failed
            that gate.
          </li>
          <li>
            Next experiment is the opposite split: a specialist router. Train
            and test on the same task type in similar repos, not leave-django-out.
            Concrete first split: hold out a slice of the {R.djangoN} django
            tasks and train K=0 LoRA on the remaining django issues (in-repo,
            in-distribution). Same 7B recipe. Checkpoint the adapter and write
            holdout scores. Gate: django-in-distribution Route-AUC vs the
            frozen v1 floor on that split (does RQ2 hold when the router is a
            specialist?). Secondary: K=0 vs K=3 on the same specialist split —
            the mix-1 analogue, not a retry of H1 on repo-shift.
          </li>
          <li>
            Extra seeds on the existing generalist K=0 ({k0}) would tighten
            RQ2’s variance. They are optional for closing H1; {k3} vs {k0} is
            not a close call.
          </li>
          <li>
            If a preprint is next, two claims, not one: repository shift
            limits trajectory-conditioned routing (RQ1), and a 7B LoRA on
            issue text can beat a frozen encoder on that same shift (RQ2).
          </li>
          <li>
            <code>{R.gpu.instance}</code> is stopped. Leave it stopped unless
            the specialist split needs GPU time.
          </li>
        </ol>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <ul className="list-disc space-y-2 pl-6">
          <li>
            Both arms are one seed. No std is reported because none exists
            yet. RQ1’s gate was “clearly above K=0,” and {k3} vs {k0} is not a
            close call. RQ2’s {k0} vs ~0.48 is also not a close call on this
            seed, but it has no seed variance yet.
          </li>
          <li>
            Endpoints on django are the same labels-only trio as v1/v2:
            always-Opus {(R.k0.alwaysLarge * 100).toFixed(1)}%, always-Qwen{" "}
            {(R.k0.alwaysSmall * 100).toFixed(1)}%, oracle{" "}
            {(R.k0.oracle * 100).toFixed(1)}%.
          </li>
          <li>
            SWE-Router mix-1 and SWE-Smith tables are calibration from related
            work, not expected transfer numbers for this pair.
          </li>
          <li>
            The trained LoRA adapters were never checkpointed.{" "}
            <code>TrajLoraBackend.save()</code> exists; the smoke runner never
            called it. Weights lived in GPU memory and died with each process.
            There is no file to reload. Retraining is the only path back to the
            models themselves. H1’s answer is in the metrics; K=3{" "}
            <code>results.json</code> is local, K=0’s file is still only on the
            stopped L4 disk.
          </li>
        </ul>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
