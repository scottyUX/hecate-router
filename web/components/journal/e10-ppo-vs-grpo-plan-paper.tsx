import Link from "next/link";

import {
  PaperAbstract,
  PaperCallout,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";

const SLUG = "2026-11-11-e10-ppo-vs-grpo-plan";

const toc: PaperTocItem[] = [
  { href: "#question", label: "Question" },
  { href: "#known", label: "What is already known" },
  { href: "#design", label: "Design" },
  { href: "#rules", label: "Decision rules" },
  { href: "#budget", label: "Budget and time" },
  { href: "#risks", label: "Risks and scope" },
  { href: "#notes", label: "Notes" },
  { href: "#references", label: "References" },
];

const references = [
  {
    id: 1,
    href: "https://arxiv.org/abs/1707.06347",
    text: "Schulman, J., Wolski, F., Dhariwal, P., Radford, A., and Klimov, O. (2017). Proximal Policy Optimization Algorithms. arXiv:1707.06347.",
  },
  {
    id: 2,
    href: "https://arxiv.org/abs/2402.03300",
    text: "Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Bi, X., Zhang, H., Zhang, M., Li, Y. K., Wu, Y., and Guo, D. (2024). DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models. arXiv:2402.03300.",
  },
  {
    id: 3,
    href: "/journal/2026-09-15-e02-specialist-django-smoke",
    text: "Davis, S. (2026). Experiment 2: django in-distribution router, seed 0. Hecate Lab journal, 15 September 2026.",
  },
  {
    id: 4,
    href: "/journal/2026-10-26-e07-final-results",
    text: "Davis, S. (2026). Experiment 7: the trained advisor across three students. Hecate Lab journal, 26 October 2026.",
  },
] as const;

export async function E10PpoVsGrpoPlanPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 10: PPO vs GRPO for the router"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-bench Verified · django specialist split (165 train / 20 val / 46 holdout) · four objectives · plan · 11 November 2026"
      date="November 11, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Software Engineering (cs.SE)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-11-11"
      tags="e10 · routing · ppo · grpo · reinforcement learning · lora · route-auc · plan"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Hecate’s routers are trained with cross-entropy on “did the cheap
          model solve it”. Experiment 7 trained its advisor with GRPO{" "}
          <PaperCite n={2} />. Experiment 10 asks, on one fixed router problem,
          whether the training objective matters: the same Qwen2.5-Coder-7B
          LoRA policy, split, input and reward, trained four ways — label
          cross-entropy, a full-information expected-reward loss, GRPO, and PPO
          with a learned critic <PaperCite n={1} />.
        </p>
        <p>
          The router’s action is one token, and both models’ outcomes and costs
          are known for every training task. That makes this the simplest
          setting in which to compare PPO and GRPO, and it makes the
          full-information arm the natural ceiling. This entry records the
          plan before any run: on the lab’s DGX Spark, no API spend, under $10
          in cash, about 1–1.5 weeks.
        </p>
      </PaperAbstract>

      <PaperSection id="question" number="1" title="Question">
        <PaperTable
          id="table-questions"
          caption="Table 1. Pre-registered questions."
          headers={["ID", "Question"]}
          rows={[
            ["Q10.1", "Does GRPO (group-mean baseline) or PPO (learned critic) give the better router on Route-AUC, at the same sample budget?"],
            ["Q10.2", "Does either RL objective beat the full-information expected-reward loss, which uses both known outcomes and samples nothing?"],
            ["Q10.3", "Does a cost-aware objective beat Experiment 2-style label cross-entropy? (Diagnostic.)"],
            ["Q10.4", "Does any arm reach always-Opus quality on the holdout (33/46) with fewer than 46 Opus calls? Experiment 2’s K=0 LoRA did not."],
            ["Q10.5", "What does each objective cost to train: GPU-hours and peak memory?"],
          ]}
        />
        <PaperCallout label="Predictions, recorded before any run">
          <p>
            Full-information ≥ GRPO ≥ PPO on Route-AUC; PPO costs more compute
            than GRPO; most seeds of every arm still need all 46 Opus calls to
            match always-Opus, because the input is the same issue text that
            never found a cheaper 33 in Experiment 2.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="known" number="2" title="What is already known">
        <PaperTable
          id="table-known"
          caption="Table 2. Experiment 2 holdout, seed 0, 46 django issues."
          headers={["Policy", "Resolved", "Opus calls to reach 33", "Route-AUC"]}
          rows={[
            ["Always Qwen3-Coder (M1)", "27/46 ($8.97)", "—", "—"],
            ["Always Claude 4 Opus (M2)", "33/46 ($49.75)", "46", "—"],
            ["Oracle", "37/46 ($19.72)", "10", "—"],
            ["E2 frozen logreg", "—", "46", "0.373"],
            ["E2 K=0 LoRA (score head)", "—", "46", "0.489"],
            ["E2 K=1 LoRA (diagnostic)", "—", "36", "0.583"],
          ]}
          highlight={(row) => row[0].startsWith("E2 K=0")}
        />
        <p>
          Both models resolve 23 issues, only Qwen 4, only Opus 10, neither 9,
          so every number turns on about 10–14 issues <PaperCite n={3} />.
          Experiment 7’s GRPO was a full fine-tune of a 7B advisor on 4× A100{" "}
          <PaperCite n={4} />. A full fine-tune with a critic needs about
          240 GB, more than the Spark’s 128 GB, so Experiment 10 uses LoRA
          throughout and says nothing about PPO versus GRPO for full
          fine-tuning or for the advisor.
        </p>
      </PaperSection>

      <PaperSection id="design" number="3" title="Design">
        <p>
          <strong>Policy.</strong> Qwen2.5-Coder-7B-Instruct in bf16 with
          Experiment 2’s LoRA shape (r 32, alpha 64). The input is the issue
          text as Experiment 2 builds it, then an instruction to answer A
          (cheap model) or B (strong model). Logits are restricted to those
          two tokens, so there are no invalid outputs, and π(A | issue) is the
          score Hecate’s Route-AUC already sweeps. Both actions’
          log-probabilities come from one forward pass, so sampling several
          actions per issue costs no extra passes.
        </p>
        <p>
          <strong>Reward.</strong> r = solved − μ · cost / mean Opus cost, with
          μ = 0.5 fixed. Qwen costs about 0.18× Opus per issue here, so any μ
          between 0 and about 1.2 makes the best choice the oracle route; μ
          sets the margin, not the answer.
        </p>
        <PaperTable
          id="table-arms"
          caption="Table 3. Arms. One trainer, one prompt, one split; only the loss differs. Up to 10 epochs, early stopping on the 20 validation issues (patience 2), seeds 0–4."
          headers={["Arm", "Objective", "LR", "Early stopping on"]}
          rows={[
            ["A", "Label cross-entropy (target A iff Qwen resolves)", "5e-5", "Val CE"],
            ["B", "Full information: exact expected-reward gradient over both actions, no sampling", "5e-5", "Val expected reward"],
            ["C", "GRPO: 4 sampled actions per issue, group-normalized advantage, clip 0.2, KL 0.001", "1e-5", "Val expected reward"],
            ["D", "PPO: the same 4 samples, advantage r − V(x) from a LoRA critic, clip 0.2, KL 0.001", "1e-5 (critic 5e-5)", "Val expected reward"],
          ]}
          highlight={(row) => row[0] === "C" || row[0] === "D"}
        />
        <p>
          C and D see the same sampled actions, so they differ only in the
          baseline: group mean against learned critic. The trainer is new
          (<code>src/hecate/router/rl_route.py</code>), not SkyRL: with a
          one-token action there is nothing to generate, and SkyRL’s LoRA path
          on aarch64 is unverified.
        </p>
        <p>
          <strong>Metric.</strong> Route-AUC on the 46 holdout issues, mean over
          seeds, with a paired bootstrap over issues (10,000 resamples).
          Secondary: the fewest Opus calls that reach 33 and their dollar cost.
          Diagnostic: AUROC, Brier, and for GRPO the share of groups with zero
          spread.
        </p>
      </PaperSection>

      <PaperSection id="rules" number="4" title="Decision rules">
        <PaperTable
          id="table-rules"
          caption="Table 4. Fixed before any Experiment 10 run."
          headers={["Question", "Rule"]}
          rows={[
            ["Q10.1", "“GRPO better” if C − D > 0 with 95% lower bound > 0; “PPO better” if < 0 with upper bound < 0; otherwise “no detectable difference at n = 46”, not a positive result for either"],
            ["Q10.2", "For C and for D separately against B: “RL beats full information” only if the lower bound > 0; “full information beats RL” if the upper bound < 0"],
            ["Q10.3", "B − A: signed gap and interval, no pass/fail"],
            ["Q10.4, Q10.5", "Descriptive"],
            ["Path 2", "A full fine-tune on 4× A100 (~$200–400) gets its own spec only if Q10.1 returns “PPO better”; any other outcome closes the question for the router"],
          ]}
          highlight={(row) => row[0] === "Path 2"}
        />
      </PaperSection>

      <PaperSection id="budget" number="5" title="Budget and time">
        <PaperTable
          id="table-budget"
          caption="Table 5. Spark time, scaled from Experiment 6’s L4 epoch (about 15–17 min per supervised epoch here), assuming the Spark is about as fast as an L4. The timing smoke replaces these."
          headers={["Arm", "Per epoch vs CE", "Per seed", "5 seeds"]}
          rows={[
            ["A label CE", "1×", "~1–1.5 h", "~5–8 h"],
            ["B full-info", "1×", "~1–1.5 h", "~5–8 h"],
            ["C GRPO", "~1.7×", "~1.5–5 h", "~8–24 h"],
            ["D PPO", "~2.5×", "~2–7 h", "~10–35 h"],
            ["Total Spark", "", "", "~30–75 h"],
          ]}
          highlight={(row) => row[0] === "Total Spark"}
        />
        <p>
          Cash: $0 GPU (lab-owned), about $2–5 of electricity, $0 API, cents a
          month of storage. Engineering 2–3 days for the trainer, tests and
          Spark setup. About 1–1.5 weeks in all after review.
        </p>
      </PaperSection>

      <PaperSection id="risks" number="6" title="Risks and scope">
        <p>
          With 46 test issues, 10 of them Opus-only, the likely Q10.1 result is
          “no detectable difference”; the compute comparison is the low-noise
          result. Issue text alone never beat always-Opus at matched quality in
          Experiment 2, so every arm may tie there. Results are about LoRA and a
          one-token decision; they do not carry to full fine-tuning or to
          Experiment 7’s advisor, where a critic could matter more.
        </p>
        <p>
          Out of scope: the step-level escalate decision (needs Experiment 8),
          λ-conditioned policies, other repos, and a small MLP policy on fixed
          features.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="7" title="Notes">
        <p>
          Spec: <code>experiments/e10-ppo-vs-grpo-router/spec.md</code>,
          including a constitution check. Nothing is authorized to run until
          review. Gates: G0, the Spark environment (aarch64 wheels or an NGC
          container, one update per arm, peak memory, and a route for copying
          run directories to <code>gs://hecate-506120-artifacts</code>, since
          the Spark has no GCP credentials); G1, a one-epoch timing smoke for
          GRPO and PPO with no holdout scoring, cutting to three seeds if the
          projection exceeds 100 Spark hours; G2, offline tests. No cross-arm
          comparison is computed until every planned run has finished.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
