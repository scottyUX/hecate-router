import { RouterE02Figures } from "@/components/experiments/router-e02-figures";
import {
  PaperAbstract,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_E02 as R } from "@/lib/experiments/router-e02";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = R.slug;

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  { href: "#method", label: "Method" },
  {
    href: "#result",
    label: "Result",
    children: [
      { href: "#fig-holdout", label: "Holdout mix" },
      { href: "#fig-calls", label: "Opus calls vs quality" },
      { href: "#tab-route-auc", label: "Route-AUC table" },
      { href: "#fig-metrics", label: "Route-AUC vs AUROC" },
      { href: "#fig-valce", label: "Val CE" },
      { href: "#fig-sub", label: "K=1 substitution" },
      { href: "#fig-pareto", label: "λ-sweep" },
      { href: "#fig-dollars", label: "Recorded API $" },
      { href: "#fig-regime", label: "Specialist vs generalist" },
      { href: "#tab-regime", label: "Regime-gap table" },
      { href: "#tab-ceilings", label: "Recorded $ ceilings" },
      { href: "#k3-vs-k1", label: "K=3 vs K=1 dollars" },
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
  {
    id: 5,
    href: "https://arxiv.org/abs/2406.18665",
    text: "Ong, I. et al. (2025). RouteLLM: Learning to Route LLMs with Preference Data. ICLR. arXiv:2406.18665.",
  },
] as const;

export async function RouterE02Paper() {
  await requireJournalPage(`/journal/${SLUG}`);
  const a = R.frozen.routeAuc.toFixed(3);
  const b = R.k0.routeAuc.toFixed(3);
  const d = R.k1.routeAuc.toFixed(3);
  const c = R.k3.routeAuc.toFixed(3);
  const q21 = (R.k0.routeAuc - R.frozen.routeAuc).toFixed(3);
  const q22 = (R.k3.routeAuc - R.k0.routeAuc).toFixed(3);
  const q23 = (R.k1.routeAuc - R.k0.routeAuc).toFixed(3);
  const gs = R.artifactsPrefix;

  return (
    <PaperShell
      title="Experiment 2: django in-distribution router, seed 0 — what we asked, what we saw, what we run next"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations={`SWE-bench Verified (${R.nPool} django) · rev ${R.rev} · SMOKE — ES rerun pending`}
      date="September 15, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-09-15"
      tags="router · specialist · django · lora · k-turn · smoke · e2"
      toc={toc}
      glossary={glossaryEntries("Route-AUC", "AUROC", "LoRA", "Brier", "K-turn", "QLoRA")}
    >
      <PaperAbstract>
        <p>
          Experiment 2 trains and tests a router on django issues (185 train /
          46 holdout, seed 0). Three questions: does a K=0 LoRA beat a frozen
          text baseline (Q2.1)? Does K=3 trajectory beat that K=0 LoRA (Q2.2)?
          Does a cheaper K=1 run look similar, as a diagnostic only (Q2.3)?
        </p>
        <p>
          Seed 0: frozen Route-AUC {a}; K=0 {b}; K=1 {d}; K=3 {c}. Q2.1 is a
          +{q21} gap, not a pass at n=46. K=3 overfit (val CE 0.637 → 2.902)
          and never matches Opus quality (33/46). K=1 once hit 33 successes
          with {R.k1.opusCallsAt33} Opus calls instead of 46; that cannot
          headline. Next is one early-stopped B/C/D rerun on the same split.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          v3 answered a generalist question: train off django, test on django.
          K=3 lost to K=0 ({R.generalist.k3.toFixed(3)} vs{" "}
          {R.generalist.k0.toFixed(3)}). E2 is the missing cell — train and
          test on django, SWE-Router’s mix-1 analogue
          <PaperCite n={4} />. Headroom over always-Opus on the full 231 is 3.9
          pp (9 small-only tasks). Routing value here is cost: send both-win
          tasks to Qwen, not accuracy lift.
        </p>
        <p>
          The first LoRA fits had no shuffle. Train rows were label-blocked, so
          K=1 collapsed (§5.5) and unshuffled K=0 Route-AUC {R.invalid.k0UnshuffledRouteAuc.toFixed(3)} is
          not Q2.1. Fit-loop patch {R.commitFit} (shuffle, 20-task val from the
          185, grad clip 1.0, zero-init score head) produced the numbers below.
          Early stopping was off for this smoke, as pre-registered.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <p>
          Split: <code>assign_specialist_split</code>, seed 0, 80/20 on{" "}
          <code>m1_resolves</code> inside <code>django/django</code> ({R.commitSplit}
          ). Arms: A frozen ModernBERT logreg; B K=0 LoRA; D K=1 LoRA
          (diagnostic); C K=3 LoRA (packed K=0..4). Backbone Qwen2.5-Coder-7B
          QLoRA on <code>{R.gpu}</code>. {R.nTrainGrad} rows get gradients; 20
          val tasks carved from the 185, never the 46. Artifacts in{" "}
          <code>{gs}/&lt;run_id&gt;</code> with adapter +{" "}
          <code>holdout_scores.jsonl</code> (A: scores only).
        </p>
        <p>
          Primary remains Route-AUC on the 46. Locked today, before the ES
          rerun: among λ with successes ≥ {R.hold.alwaysLarge}, minimum Opus
          calls, vs {R.hold.alwaysOpusCalls} and oracle {R.hold.oracleOpusCalls}.
          CPT is reported and dead on this split — always-Qwen already clears
          CPT(80%).
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <p>
          Seed 0 on the 46-task holdout. Figures first, then the same numbers
          as tables. Q2.1 (B − A) = +{q21} — above frozen on this seed, not a
          pass at n=46. Q2.2 (C − B) = +{q22} from an overfit checkpoint. Q2.3
          (D − B) = +{q23}, diagnostic only.
        </p>
        <RouterE02Figures />
        <PaperTable
          id="tab-route-auc"
          caption="Table 1: Seed-0 patched Route-AUC on the 46-task holdout. MLP frozen is not the arm-A headline. Unshuffled k0/k1 are omitted on purpose."
          highlight={(row) => row[0].startsWith("B")}
          headers={["Arm", "run_id", "Route-AUC", "AUROC", "Brier"]}
          rows={[
            [
              "A frozen logreg",
              R.frozen.runId,
              a,
              R.frozen.auroc.toFixed(3),
              R.frozen.brier.toFixed(3),
            ],
            [
              "B K=0 LoRA",
              R.k0.runId,
              b,
              R.k0.auroc.toFixed(3),
              R.k0.brier.toFixed(3),
            ],
            [
              "D K=1 LoRA (diagnostic)",
              R.k1.runId,
              d,
              R.k1.auroc.toFixed(3),
              R.k1.brier.toFixed(3),
            ],
            [
              "C K=3 LoRA",
              R.k3.runId,
              c,
              R.k3.auroc.toFixed(3),
              R.k3.brier.toFixed(3),
            ],
          ]}
        />
        <p>
          Q2.1 (B − A) = +{q21}. Above frozen on this seed; inside the n=46
          noise band in §6.1. Not a pass. Q2.2 (C − B) = +{q22}. Q2.3 (D − B) =
          +{q23}, diagnostic only.
        </p>
        <PaperTable
          id="tab-calls"
          caption="Table 2: Matched-quality Opus calls. Successes ≥ 33, then fewest large-model routes. Holdout complementarity: 23 both, 4 small-only, 10 large-only, 9 neither."
          highlight={(row) => row[0].startsWith("D")}
          headers={["Policy", "Opus calls", "Successes"]}
          rows={[
            ["Always Qwen", "0", String(R.hold.alwaysSmall)],
            ["Oracle (match 33)", String(R.hold.oracleOpusCalls), String(R.hold.alwaysLarge)],
            ["Always Opus", String(R.hold.alwaysOpusCalls), String(R.hold.alwaysLarge)],
            ["A frozen logreg", "46", "33"],
            ["B K=0", String(R.k0.opusCallsAt33), String(R.k0.successesAtBest)],
            ["D K=1", String(R.k1.opusCallsAt33), String(R.k1.successesAtBest)],
            ["C K=3 (best)", String(R.k3.opusCallsAtMax), String(R.k3.maxSuccesses)],
          ]}
        />
        <PaperSubsection id="d-sub" number="3.1" title="What D’s 26 actually is">
          <p>
            At λ={R.k1.lambda.toFixed(2)} D hits 33 successes with{" "}
            {R.k1.opusCallsAt33} Opus calls. That 33 is resolved tasks of 46,
            not “26 routing decisions were correct.” All {R.hold.both} both-win
            tasks succeed either way ({R.k1.bothToOpus} still went to Opus). It
            recovers {R.k1.largeOnlyToOpus}/{R.hold.largeOnly} Opus-only and{" "}
            {R.k1.smallOnlyToQwen}/{R.hold.smallOnly} Qwen-only — a cheaper 33,
            not “learned which tasks need Opus.”
          </p>
        </PaperSubsection>
        <PaperTable
          id="tab-dollars"
          caption="Table 3: Recorded mini-SWE-agent API cost on the same 46 holdout tasks (2025-08-02 run). D and C use the actual routed instance IDs from holdout scores, not a mean-per-call estimate. Oracle at 10 Opus calls gets 37 successes, not 33. These are recorded Aug 2025 dollars, not Sep 2026 list prices."
          highlight={(row) => row[0].startsWith("D")}
          headers={["Policy", "Opus calls", "Successes", "Cost", "Saved vs always-Opus"]}
          rows={[
            [
              "Always-Opus / A / B",
              "46",
              "33",
              `$${R.dollars.alwaysOpusUsd.toFixed(2)}`,
              "—",
            ],
            [
              "D K=1 (diagnostic)",
              "26",
              "33",
              `$${R.dollars.dUsd.toFixed(2)}`,
              `$${(R.dollars.alwaysOpusUsd - R.dollars.dUsd).toFixed(2)} (${(100 * (1 - R.dollars.dUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%)`,
            ],
            [
              "C K=3 (overfit)",
              "45",
              "32",
              `$${R.dollars.cUsd.toFixed(2)}`,
              `$${(R.dollars.alwaysOpusUsd - R.dollars.cUsd).toFixed(2)} (${(100 * (1 - R.dollars.cUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%)`,
            ],
            [
              "Oracle (Opus-only only)",
              "10",
              "37",
              `$${R.dollars.oracleUsd.toFixed(2)}`,
              `$${(R.dollars.alwaysOpusUsd - R.dollars.oracleUsd).toFixed(2)} (${(100 * (1 - R.dollars.oracleUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%)`,
            ],
            [
              "Always-Qwen",
              "0",
              "27",
              `$${R.dollars.alwaysQwenUsd.toFixed(2)}`,
              `$${(R.dollars.alwaysOpusUsd - R.dollars.alwaysQwenUsd).toFixed(2)} (quality −6)`,
            ],
          ]}
        />
        <PaperTable
          id="tab-val"
          caption="Table 4: Monitor-slice val CE by epoch (20 tasks from the 185). Early stopping was off. C’s dive is the trigger to turn it on."
          highlight={(row) => row[0].startsWith("C")}
          headers={["Arm", "ep0", "ep1", "ep2", "ep3", "ep4"]}
          rows={[
            ["B K=0", ...R.k0.valCe.map((x) => x.toFixed(3))],
            ["D K=1", ...R.k1.valCe.map((x) => x.toFixed(3))],
            ["C K=3", ...R.k3.valCe.map((x) => x.toFixed(3))],
          ]}
        />
        <PaperSubsection
          id="regime"
          number="3.2"
          title="Specialist vs generalist"
        >
          <p>
            The generalist router is v3 leave-django-out: train on{" "}
            {R.generalist.nTrain} non-django issues, test on all{" "}
            {R.generalist.nHold} django
            <PaperCite n={4} />. This smoke is the specialist cell: train on{" "}
            {R.nTrainGrad} django, test on {R.nHold}. Absolute Route-AUC is not
            comparable across those holdouts. The pre-registered contrasts are
            the signed gaps. Fine-tune lift is present in both. The trajectory
            gap flips sign — the SWE-Router mix-1 vs repo-disjoint pattern —
            but specialist K=3 is the overfit checkpoint, so Q2.2 is not
            confirmed. K=1 has no generalist counterpart.
          </p>
        </PaperSubsection>
        <PaperTable
          id="tab-regime"
          caption="Table 5: Train-and-test on django (specialist, n=46) vs train on non-django and test on django (generalist holdout, n=231). Do not stack 0.686 vs 0.482."
          highlight={(row) => row[0].startsWith("Trajectory")}
          headers={["Contrast", "Generalist: train off django, test django (n=231)", "Specialist: train and test on django (n=46)"]}
          rows={[
            [
              "Fine-tune lift (K=0 − frozen)",
              `+${R.generalist.k0MinusFrozen.toFixed(3)} (${R.generalist.k0.toFixed(3)} − ${R.generalist.frozen.toFixed(3)})`,
              `+${q21} (${b} − ${a})`,
            ],
            [
              "Trajectory gap (K=3 − K=0)",
              `${R.generalist.k3MinusK0.toFixed(3)} (${R.generalist.k3.toFixed(3)} − ${R.generalist.k0.toFixed(3)})`,
              `+${q22} (${c} − ${b}), C overfit`,
            ],
          ]}
        />
        <p>
          Because Opus already gets {R.hold.alwaysLarge}/{R.nHold}, a router
          cannot buy much extra accuracy. The useful win, if any, is cost:
          send the both-win tasks to Qwen and only the Opus-only tasks to
          Opus. A perfect cost-saving policy that still hits{" "}
          {R.hold.alwaysLarge} successes would call Opus on{" "}
          {R.hold.oracleOpusCalls} tasks, not {R.hold.alwaysOpusCalls} — and
          sending only those {R.hold.oracleOpusCalls} actually scores{" "}
          {R.hold.oracle}, because the {R.hold.smallOnly} Qwen-only wins come
          along for free.
        </p>
        <p>
          The same recorded Aug 2025 API costs on both protocols (not
          September 2026 list prices). Oracle = Opus-only → Opus, everyone
          else → Qwen. The cheaper “just match always-Opus” row uses Qwen-only
          wins as substitutes and picks the cheapest incremental Opus-only
          tasks (Opus $ minus Qwen $), so it can send fewer than the Opus-only
          count.
        </p>
        <PaperTable
          id="tab-ceilings"
          caption="Table 6: Recorded mini-SWE-agent API cost. Oracle is max quality. Matched-quality frontier is the cheapest label policy that still hits always-Opus’s own success count. Generalist K=3 call mix was never written to disk."
          highlight={(row) => row[0].startsWith("Frontier")}
          headers={[
            "",
            `Generalist (v3, n=${R.generalist.nHold})`,
            `Specialist (this smoke, n=${R.nHold})`,
          ]}
          rows={[
            [
              "Always-Opus cost",
              `$${R.generalist.alwaysOpusUsd.toFixed(2)}`,
              `$${R.dollars.alwaysOpusUsd.toFixed(2)}`,
            ],
            [
              "Oracle ceiling (Opus-only → Opus only)",
              `${R.generalist.oracleCalls} calls, $${R.generalist.oracleUsd.toFixed(2)}, ${R.generalist.oracleHits}/${R.generalist.nHold} succ`,
              `${R.dollars.oracleCalls} calls, $${R.dollars.oracleUsd.toFixed(2)}, ${R.dollars.oracleHits}/${R.nHold} succ`,
            ],
            [
              "% saved at oracle ceiling",
              `$${R.generalist.oracleSaveUsd.toFixed(2)}, ${R.generalist.oracleSavePct.toFixed(1)}%`,
              `$${(R.dollars.alwaysOpusUsd - R.dollars.oracleUsd).toFixed(2)}, ${(100 * (1 - R.dollars.oracleUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%`,
            ],
            [
              "Frontier cost to just match always-Opus quality",
              `${R.generalist.matchCalls} calls, $${R.generalist.matchUsd.toFixed(2)}, ${R.generalist.alwaysLarge} succ`,
              `${R.dollars.matchCalls} calls, $${R.dollars.matchUsd.toFixed(2)}, ${R.dollars.matchHits} succ`,
            ],
            [
              "% saved at matched quality",
              `$${R.generalist.matchSaveUsd.toFixed(2)}, ${R.generalist.matchSavePct.toFixed(1)}%`,
              `$${R.dollars.matchSaveUsd.toFixed(2)}, ${R.dollars.matchSavePct.toFixed(1)}%`,
            ],
            [
              "Trained K=3 (operating point)",
              `${(100 * R.generalist.k3BestRouteRate).toFixed(1)}% successes; call mix / $ not scored`,
              `${R.k3.opusCallsAtMax} calls, ${R.k3.maxSuccesses} succ — misses 33`,
            ],
            [
              "Trained D K=1 (diagnostic)",
              "no generalist K=1",
              `${R.k1.opusCallsAt33} calls, $${R.dollars.dUsd.toFixed(2)}, save $${(R.dollars.alwaysOpusUsd - R.dollars.dUsd).toFixed(2)} (${(100 * (1 - R.dollars.dUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}% vs a possible ${R.dollars.matchSavePct.toFixed(1)}%)`,
            ],
          ]}
        />
        <PaperSubsection
          id="k3-vs-k1"
          number="3.3"
          title="Generalist K=3 vs specialist K=1 — which saved more?"
        >
          <p>
            Specialist K=1 is the only trained mix we can price:{" "}
            {(100 * (1 - R.dollars.dUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%
            off always-Opus on these {R.nHold} tasks, still{" "}
            {R.hold.alwaysLarge} successes. Generalist K=3’s selected λ ties
            always-Opus quality ({R.generalist.alwaysLarge}/
            {R.generalist.nHold}). That is “no extra quality,” not “no
            savings.” Some both-win tasks could have gone to Qwen with the
            total still {R.generalist.alwaysLarge}. Those 231 scores were never
            written — local <code>v3-smoke-k3/results.json</code> has
            best_lambda=0.67 and no <code>holdout_scores.jsonl</code>; GCS has
            only this experiment’s runs. Without that vector the dollar % is
            unknown, not zero.
          </p>
          <p>
            We should not say generalist K=3 saved less than{" "}
            {(100 * (1 - R.dollars.dUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%
            as a measured fact. The sentence that holds: K=1 is the only arm
            that actually banked a cheaper 33; generalist K=3 never showed a
            cheaper 163. They are also not a fair horse race — {R.nHold} vs{" "}
            {R.generalist.nHold}, diagnostic K=1 vs confirmatory K=3.
          </p>
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          “Cuts Opus calls by 43% at matched quality” is the right sentence
          shape and the wrong status. It is D, one seed, n=46, and a messy
          substitution. Spec §5.4 forbids leading with it. C, the confirmatory
          arm, overfit and cannot match always-Opus quality.
        </p>
        <p>
          In recorded Aug 2025 API dollars on this holdout, always-Opus is $
          {R.dollars.alwaysOpusUsd.toFixed(2)}. D saves $
          {(R.dollars.alwaysOpusUsd - R.dollars.dUsd).toFixed(2)} (still
          diagnostic). C saves $
          {(R.dollars.alwaysOpusUsd - R.dollars.cUsd).toFixed(2)} and misses
          the quality bar. The 10-call oracle is $
          {R.dollars.oracleUsd.toFixed(2)} and gets 37 successes, not 33.
        </p>
        <p>
          Against the generalist router, do not stack K=0 0.686 (n=231) vs
          0.482 (n=46) as if in-distribution ranking is worse. The comparable
          facts are the two signed gaps: fine-tune lift in both regimes (+
          {R.generalist.k0MinusFrozen.toFixed(3)} generalist, +{q21}{" "}
          specialist, the latter not a pass at n=46); trajectory gap flipped
          from {R.generalist.k3MinusK0.toFixed(3)} under repository shift to +
          {q22} here. That is the SWE-Router mix-1 vs disjoint direction, with
          the specialist side still provisional because C overfit.
        </p>
        <p>
          How much money is theoretically on the table is not a
          specialist-vs-generalist effect. At the oracle ceiling the two
          splits save {R.generalist.oracleSavePct.toFixed(1)}% vs{" "}
          {(100 * (1 - R.dollars.oracleUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%;
          to just match always-Opus they save {R.generalist.matchSavePct.toFixed(1)}%
          vs {R.dollars.matchSavePct.toFixed(1)}%. Capture is what fails. D
          takes{" "}
          {(100 * (1 - R.dollars.dUsd / R.dollars.alwaysOpusUsd)).toFixed(1)}%
          against a possible {R.dollars.matchSavePct.toFixed(1)}% and cannot
          headline. Generalist K=3’s dollar % cannot be calculated from the
          files that exist.
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Do not boot the L4 until this amendment is the spec you are running
            (it is, as of today). Early stopping on, B/C/D together.
          </li>
          <li>
            Same 185/46 split, new IDs: <code>{R.nextRunIds.k0}</code>,{" "}
            <code>{R.nextRunIds.k1}</code>, <code>{R.nextRunIds.k3}</code>. Stop
            the VM when all three GCS copies exist.
          </li>
          <li>
            Decide from that set: if C reaches 33, its Opus-call count is the
            sentence and D is the cheap proxy. If C still cannot, the paper is
            the other kind — K=3 overfit, K=1 found a cheaper 33 once,
            diagnostic ≠ finding.
          </li>
          <li>
            No extra D seed. No ES-C-only rescue. Do not quote unshuffled 0.757
            or 0.500.
          </li>
        </ol>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <ul className="list-disc space-y-2 pl-6">
          <li>
            Frozen MLP Route-AUC {R.frozen.mlpRouteAuc.toFixed(3)} is not the
            Q2.1 floor. Logreg is.
          </li>
          <li>
            Weights for the patched adapters are in GCS, including{" "}
            <code>adapter_model.safetensors</code> and <code>score.pt</code>.
            Both VMs are TERMINATED. L4 smoke cost was about $28 at list price.
          </li>
          <li>
            Joined training labels are pass/fail only. Recorded per-task API
            cost is in the raw 2025-08-02 submissions (
            <code>per_instance_details.json</code> under{" "}
            <code>evaluation/verified/</code>, and Qwen{" "}
            <code>model_stats.instance_cost</code> in{" "}
            <code>data/raw/trajs/full.jsonl</code>, matching 500/500). Mean on
            this holdout: ${R.dollars.meanOpusUsd.toFixed(2)} Opus vs $
            {R.dollars.meanQwenUsd.toFixed(3)} Qwen (~{R.dollars.ratio.toFixed(1)}
            ×), not the 15–50× per-token sticker. Vintage is the Aug 2025 run,
            not current list prices.
          </li>
          <li>
            Generalist numbers in Figure 8–9 / Tables 5–6 are the v3 django
            holdout (
            <a href={R.generalist.journal}>
              2026-08-26-v3-trajectory-router-spec
            </a>
            ), not a re-score of this 46-task split. Matched-quality 6-call /
            29-call rows rank Opus-only tasks by incremental cost (Opus $
            minus Qwen $), not Opus sticker. Generalist K=3 scores were never
            checkpointed.
          </li>
          <li>
            Canonical numbers:{" "}
            <code>experiments/e02-specialist-django/results.md</code>.
          </li>
        </ul>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
