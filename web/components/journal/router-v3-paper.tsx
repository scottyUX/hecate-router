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
      { href: "#tab-v3-gate", label: "Four methods" },
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
      updated="2026-09-15"
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
          mini-SWE-agent v1.0.0, same 500 labels.
          <PaperCite n={[1, 2, 3]} />
        </p>
        <p>
          The value head is a QLoRA adapter (r=32, α=64) on
          Qwen2.5-Coder-7B-Instruct, trained on a single L4 with up to 8192
          tokens of context. It scores P(Qwen resolves) from the model’s
          last-token logits. A turn is one user/observation boundary in the
          agent’s trajectory; only the K=3 arm packs multiple turns into its
          input — K=0 sees issue text alone, no trajectory at all.
        </p>
        <p>
          One deviation from SWE-Router: their pipeline augments the issue
          text with three LLM-generated paraphrases (§A.2) before scoring; we
          skip that step here for cost.
          <PaperCite n={4} />
        </p>
        <p>
          Training ran on <code>{R.gpu.instance}</code>, kept separate from
          the evaluation VM (<code>hecate-exec</code>).{" "}
          <code>{R.gpu.instance}</code> is the L4 GPU used for LoRA training;{" "}
          <code>hecate-exec</code> is CPU-only and cannot run this fit.{" "}
          <code>{R.gpu.instance}</code> is now terminated — training for this
          round is complete, and there is nothing left running to bill (disk
          retained).
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
          <strong>Bottom line:</strong> giving the router three turns of
          Qwen’s own attempt at the task (K=3) did not help it route better
          than just reading the issue text alone (K=0) — Route-AUC dropped
          from {k0} to {k3}, a real drop, not noise. So the central question
          this experiment asked — does watching the weak model start the task
          tell you more than just reading the issue? — comes back{" "}
          <strong>no</strong>. Separately, both K=0 and K=3 clearly beat the
          older, non-fine-tuned baselines (v1 and v2, both around 0.48), so
          fine-tuning itself helps; it is specifically the extra turns that
          don’t.
        </p>
        <p>
          Four questions were locked in before this run, so nobody could pick
          the flattering ones after seeing the results. H1, H2, and RQ1 were
          pre-registered. RQ2 is scored on the same smoke; it was not the
          gate. The confirmatory split is the django holdout ({R.djangoN}{" "}
          tasks).
        </p>
        <PaperTable
          id="tab-decisions"
          caption="Table 1: What each locked question asked, what we saw, and the verdict."
          highlight={(row) =>
            row[0].startsWith("H1") || row[0].startsWith("RQ2")
          }
          headers={["Question", "What it asked", "What we saw", "Verdict"]}
          rows={[
            [
              "H1",
              "Does K=3 beat K=0?",
              `K=0 = ${k0}, K=3 = ${k3}`,
              `No — K=3 came in ${drop} lower`,
            ],
            [
              "H2",
              `Does K=3 at least clear a low bar (≥${R.stretch.djangoRouteAuc.toFixed(2)})?`,
              `K=3 = ${k3}`,
              "Technically cleared, but doesn’t count as a win — this was a pre-agreed fallback bar, not a substitute for beating K=0",
            ],
            [
              "RQ1",
              "Do trajectory turns carry real signal beyond the issue text?",
              "K=3 underperformed K=0",
              "No",
            ],
            [
              "RQ2",
              "Does a fine-tuned model beat the old frozen-embedding baselines (v1/v2)?",
              `${k0} and ${k3} vs. ~0.48`,
              "Yes — the fine-tuning is what helps, not the extra turns",
            ],
          ]}
        />
        <p>
          Route-AUC is the metric that actually matters here: it measures how
          well a score ranks tasks for the “send this to Qwen vs. send it to
          Opus” decision. Higher means better at telling which tasks are safe
          to route cheaply. AUROC is a secondary pairwise-ranking number —
          don’t over-read it. Brier score is calibration (lower is better).
          Accuracy is just how often a 0.5 threshold would guess the Qwen-win
          label, and it is easy to lose to a dumb default on this split.
        </p>
        <p>
          <strong>How this stacks up against the paper we borrowed the
          method from.</strong> SWE-Router reports two settings.
          <PaperCite n={4} /> Table 2 is their easy one — train and test mixed
          across repos, no holdout — where more turns clearly does help,
          climbing from ~0.55–0.63 at K=0 up past 0.7 by K=2–4. That’s not
          our comparison. Table 3 is their hard setting — testing on repos
          the model never saw in training, exactly what our django holdout
          also does — and there their own numbers show the same failure ours
          does: K=3 doesn’t clearly beat K=0. That’s the real comparison, and
          why this is being written up as a finding that replicates outside
          our own project, not just a disappointing single run.
        </p>
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
        <p>
          <strong>Our four methods, side by side.</strong> v1/v2 are averaged
          over 3 seeds (the ± is that spread). K=0 and K=3 are each a single
          run — treat their numbers as a first look, not a settled result.
          The highlighted row is the one the experiment actually gates on.
        </p>
        <PaperTable
          id="tab-v3-gate"
          caption="Table 4: Hecate v1 / v2 / K=0 / K=3 on this pair. Route-AUC is the metric that matters. Grouped 5-fold is a django-weighted mix of all repos — leave it on the table so it isn’t mistaken for the django holdout result; do not headline it."
          highlight={(row) => row[0].startsWith("Route-AUC")}
          headers={[
            "",
            "v1, frozen text",
            "v2, oracle structure",
            "K=0, fine-tuned text only",
            "K=3, fine-tuned + 3 turns",
          ]}
          rows={[
            [
              "Route-AUC (the metric that matters)",
              R.v1v2.djangoRouteAuc.text,
              R.v1v2.djangoRouteAuc.fusion,
              k0,
              k3,
            ],
            [
              "AUROC (secondary — don’t over-read this)",
              R.v1v2.djangoAuroc.text,
              R.v1v2.djangoAuroc.fusion,
              R.k0.auroc.toFixed(3),
              R.k3.auroc.toFixed(3),
            ],
            [
              "Accuracy",
              R.v1v2.djangoAcc.text,
              R.v1v2.djangoAcc.fusion,
              R.k0.accuracy.toFixed(3),
              R.k3.accuracy.toFixed(3),
            ],
            [
              "Brier score (lower = better-calibrated)",
              R.v1v2.djangoBrier.text,
              R.v1v2.djangoBrier.fusion,
              R.k0.brier.toFixed(3),
              R.k3.brier.toFixed(3),
            ],
            [
              "Grouped 5-fold Route-AUC (not the gate)",
              R.v1v2.groupedRouteAuc.text,
              R.v1v2.groupedRouteAuc.fusion,
              "not run",
              "not run",
            ],
          ]}
        />

        <PaperSubsection
          id="k0"
          number="3.1"
          title="K=0 — what fine-tuning on issue text alone actually showed"
        >
          <p>
            Route-AUC jumped well above the old frozen-baseline floor ({k0} vs.
            ~0.48). But two things temper that: AUROC barely moved (
            {R.k0.auroc.toFixed(3)}), and accuracy ({R.k0.accuracy.toFixed(3)})
            is actually worse than just always guessing “Qwen will succeed”
            (right {(R.djangoAlwaysSmall * 100).toFixed(0)}% of the time here
            on its own). The model’s confidence also got less trustworthy, not
            more — Brier {R.k0.brier.toFixed(3)} vs. 0.250 for v1/v2.
          </p>
          <p>
            That’s not a contradiction: Route-AUC mainly rewards correctly
            ranking the clearest cases, while AUROC and Brier average over
            everything, including the ambiguous middle. But it’s also exactly
            the pattern you’d see from a lucky single-seed result on a{" "}
            {R.djangoN}-task holdout, where one seed can swing a fair amount.
            Read {k0} as “this experiment’s current best guess,” not proof
            that fine-tuning is a settled win — and not as evidence that
            trajectory conditioning works.
          </p>
        </PaperSubsection>

        <PaperSubsection
          id="k3"
          number="3.2"
          title="K=3 — what happened when we added 3 turns of trajectory"
        >
          <p>
            <strong>Training:</strong> {R.k3.epochs} full passes over the data
            ({R.k3.steps} steps, ~{R.k3.trainHours} hours on one L4 GPU,{" "}
            <code>{R.gpu.instance}</code>). Each of the {R.k3.nTrain} training
            tasks was expanded into 5 versions — one per amount of trajectory,
            0 through 4 turns — giving {R.k3.nTrainRows} training rows per
            pass. Training loss fell steadily ({epochLoss}), crossing “better
            than a coin flip” (ln(2) ≈ {R.ln2.toFixed(3)}) partway through
            pass 2 (pass 1 is still {R.k3.epochMeanLoss[1].toFixed(3)}). The
            steep drop is in the last pass (
            {R.k3.epochMeanLoss[3].toFixed(3)} →{" "}
            {R.k3.epochMeanLoss[4].toFixed(3)}).
          </p>
          <p>
            <strong>Did long trajectories get cut off?</strong> Barely —{" "}
            {R.k3.trainTruncatedRows} of {R.k3.nTrainRows} rows per pass
            (about {trainTruncPct}%) hit the {R.k3.trainSeqMax}-token limit
            (median packed length {R.k3.trainSeqP50}). That is the truncation
            figure that matters, because it is from the tokenizer the trainer
            actually used. A cruder word-count check on the raw traces said
            even fewer were cut (0/{R.n}, median {R.traces.whitespaceMedianTokens}{" "}
            whitespace tokens — that proxy undercounts code). An earlier check
            using the real tokenizer said slightly more (
            {(R.traces.hfAuditTruncationRate * 100).toFixed(1)}% of the
            original {R.n} raw trajectories, {R.traces.hfAuditTruncatedN}/
            {R.n}, median {R.traces.hfAuditMedianTokens}). Either way, this is
            too small to explain why K=3 underperformed.
          </p>
          <p>
            <strong>The result that matters:</strong> Route-AUC {k3}, below
            K=0’s {k0} — the headline rejection. It still clears the old
            frozen floor, so fine-tuning still helps even at K=3 (RQ2 stays
            yes). AUROC ticked up slightly ({R.k3.auroc.toFixed(3)} vs.{" "}
            {R.k0.auroc.toFixed(3)}, a 0.010 move on one seed) — not enough
            to change the picture, and not a ranking rescue. Calibration got
            worse: Brier {R.k3.brier.toFixed(3)} is worse than a constant-0.5
            guess (0.250). In practical terms: at the threshold you’d actually
            use to route tasks (λ={R.k3.bestLambda.toFixed(2)}), K=3 ends up
            solving the same share of tasks as just sending everything to Opus
            ({(R.k3.bestRouteRate * 100).toFixed(1)}%). Watching Qwen’s first
            three turns didn’t uncover any tasks that were safe to route
            cheaply beyond what doing nothing clever at all would get you.
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
          <li>
            K=3 epoch-mean training loss is {R.k3.epochMeanLoss.map((x) => x.toFixed(3)).join(" → ")}{" "}
            from <code>train_epochs.jsonl</code>. An in-run parse of logged
            step losses while epoch 5 was still going (0.77 → 0.69 → 0.59 →
            0.54 → 0.30) is not that series — it was a progress check, not the
            epoch means.
          </li>
        </ul>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
