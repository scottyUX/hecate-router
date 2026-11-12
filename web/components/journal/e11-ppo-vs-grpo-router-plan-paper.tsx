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

const SLUG = "2026-11-12-e11-ppo-vs-grpo-router-plan";

const toc: PaperTocItem[] = [
  { href: "#question", label: "Question" },
  { href: "#known", label: "What Experiment 2 showed" },
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
    href: "/journal/2026-11-12-e10-ppo-vs-grpo-advisor-plan",
    text: "Davis, S. (2026). Experiment 10: PPO vs GRPO for the advisor, all on the DGX Spark. Hecate Lab journal, 12 November 2026.",
  },
] as const;

export async function E11PpoVsGrpoRouterPlanPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 11: PPO vs GRPO for the router, on the DGX Spark"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-bench Verified · django specialist split (185 train / 46 holdout) · Qwen2.5-Coder-7B LoRA router · DGX Spark · plan · 12 November 2026"
      date="November 12, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Software Engineering (cs.SE)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-11-12"
      tags="e11 · routing · ppo · grpo · reinforcement learning · lora · dgx spark · plan"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Experiment 7 trained an LLM with GRPO <PaperCite n={2} />, which
          drops PPO’s learned critic <PaperCite n={1} /> and scores each
          sample against the average of its group. Experiment 11 asks whether
          that choice matters on a small problem Hecate already has: the
          router that sends an SWE-bench task to the cheap model (Qwen3-Coder)
          or the strong one (Claude 4 Opus). Experiment 2’s router is
          retrained three ways on Experiment 2’s django split{" "}
          <PaperCite n={3} />: its own cross-entropy loss, GRPO and PPO.
        </p>
        <p>
          Both models’ outcomes and costs are already logged for every task,
          so nothing runs live: no API calls and no containers. It runs on the
          lab’s DGX Spark, reuses Experiment 2’s code, and takes about 2–3
          days for a few dollars of electricity. This entry records the plan
          before any run.
        </p>
      </PaperAbstract>

      <PaperSection id="question" number="1" title="Question">
        <PaperTable
          id="table-questions"
          caption="Table 1. Pre-registered questions, with the predictions recorded before any run."
          headers={["ID", "Question", "Prediction"]}
          rows={[
            ["Q11.1", "Does GRPO or PPO train the better router on Route-AUC, with everything else the same?", "No detectable difference"],
            ["Q11.2", "Secondary: does either beat Experiment 2’s cross-entropy loss on the same model?", "No"],
            ["Q11.3", "Descriptive: fewest Opus calls that still match always-Opus (33/46).", "Most seeds still need 46"],
            ["Q11.4", "Descriptive: training time, memory and epochs to the best checkpoint on the Spark.", "About the same for all three"],
          ]}
        />
      </PaperSection>

      <PaperSection id="known" number="2" title="What Experiment 2 showed">
        <PaperTable
          id="table-e02"
          caption="Table 2. Experiment 2 holdout, seed 0, 46 django issues."
          headers={["Policy", "Resolved", "Cost or Route-AUC"]}
          rows={[
            ["Always Qwen3-Coder", "27 / 46", "$8.97"],
            ["Always Claude 4 Opus", "33 / 46", "$49.75"],
            ["Oracle", "37 / 46", "10 Opus calls, $19.72"],
            ["K=0 LoRA router (cross-entropy)", "—", "Route-AUC 0.489; needs all 46 Opus calls to reach 33"],
          ]}
        />
        <p>
          The oracle is only 4 issues above always-Opus, and only 10 issues are
          solved by Opus alone, so every comparison turns on a handful of
          tasks. Experiment 11 reruns the cross-entropy arm on the Spark so
          that all three arms share hardware and settings.
        </p>
      </PaperSection>

      <PaperSection id="design" number="3" title="Design">
        <PaperCallout label="The router is already a two-action policy">
          <p>
            Experiment 2’s router ends in a head with two outputs, read today
            as the probability that the cheap model solves the task. The same
            two outputs are a policy over two actions: send to Qwen3-Coder or
            send to Opus. So GRPO and PPO can train the exact Experiment 2
            model, starting from a 50/50 policy, with no new prompt and no new
            model. Route-AUC scores all three arms with the same code.
          </p>
        </PaperCallout>
        <PaperTable
          id="table-arms"
          caption="Table 3. Arms. Shared: Qwen2.5-Coder-7B-Instruct with LoRA r 32 / alpha 64, issue text only, Experiment 2’s split and settings (LR 5e-5, batch 16, up to 5 epochs with early stopping), seeds 0–2."
          headers={["Arm", "Objective", "Baseline"]}
          rows={[
            ["CE (reference)", "Cross-entropy on “cheap model solves it”, as in Experiment 2", "—"],
            ["GRPO", "4 sampled routes per task; reward minus the group’s mean, divided by its spread", "Group mean"],
            ["PPO", "The same 4 samples; reward minus a critic’s estimate", "Learned critic (a small extra head)"],
          ]}
          highlight={(row) => row[0] === "GRPO" || row[0] === "PPO"}
        />
        <p>
          <strong>Reward.</strong> r = solved − 0.5 × cost / mean Opus cost,
          using each task’s logged cost. With these costs, the best possible
          policy under this reward is the oracle route, so 0.5 only sets how
          much an unnecessary Opus call is penalized.
        </p>
        <p>
          <strong>Fairness.</strong> GRPO and PPO see the same sampled routes,
          take one update per batch (as Experiment 7 did), and pay the same KL
          penalty for moving away from 50/50, so they differ only in the
          baseline.
        </p>
        <p>
          <strong>Code.</strong> Experiment 2’s router code is reused: the
          split, data loading, model, training loop, early stopping, saving,
          holdout scoring and Route-AUC. New: an <code>--objective</code>{" "}
          option with the GRPO and PPO losses, a script that downloads each
          task’s logged cost, and unit tests.
        </p>
      </PaperSection>

      <PaperSection id="rules" number="4" title="Decision rules">
        <PaperTable
          id="table-rules"
          caption="Table 4. Fixed before any Experiment 11 run. For a difference X − Y in seed-mean Route-AUC, with a paired bootstrap over the 46 holdout tasks."
          headers={["Outcome", "Rule"]}
          rows={[
            ["X better", "Point estimate > 0 and 95% lower bound > 0"],
            ["Y better", "Point estimate < 0 and 95% upper bound < 0"],
            ["Otherwise", "“No detectable difference at n = 46, 3 seeds”: not a win for either"],
            ["Q11.1 (primary)", "GRPO − PPO"],
            ["Q11.2 (secondary)", "GRPO − CE and PPO − CE, each on its own"],
            ["Scope", "Says nothing about long-text, multi-turn training; that is Experiment 10"],
          ]}
        />
      </PaperSection>

      <PaperSection id="budget" number="5" title="Budget and time">
        <PaperTable
          id="table-budget"
          caption="Table 5. Estimated cost and time. Per-epoch time is scaled from Experiment 6’s L4 timing; the Spark smoke replaces it."
          headers={["Item", "Estimate"]}
          rows={[
            ["Runs: 3 arms × 3 seeds × up to 5 epochs (~15–17 min each)", "~7–13 h of Spark time"],
            ["API calls, cloud machines, containers", "$0 (none used)"],
            ["Spark", "$0 (lab-owned); electricity a few dollars"],
            ["Wall time", "~2–3 days: code and tests, Spark setup and smoke, overnight runs, analysis"],
          ]}
        />
        <p>
          A lab member runs it over SSH from a runbook, after the spec is
          reviewed and the code is merged. If the smoke projects more than 72
          hours of runs, the seeds drop to two by amendment.
        </p>
      </PaperSection>

      <PaperSection id="risks" number="6" title="Risks and scope">
        <p>
          With 46 holdout tasks, most differences will read as “no
          detectable difference”; the training statistics and compute are
          the lower-noise results. Issue text alone never beat always-Opus at
          matched quality in Experiment 2, so all arms may still need every
          Opus call to reach 33. The Spark is ARM with a new GPU, so 4-bit
          loading may not work; then every arm runs in bf16, recorded.
        </p>
        <p>
          Out of scope: the advisor (Experiment 10 <PaperCite n={4} />), the
          trajectory arms, other repos, and any change to Experiment 2’s
          results.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="7" title="Notes">
        <p>
          Spec: <code>experiments/e11-ppo-vs-grpo-router/spec.md</code> (rev
          4), including a constitution check; runbook:{" "}
          <code>experiments/e11-ppo-vs-grpo-router/runbook.md</code>. This
          plan was Experiment 10 (revs 1 and 3) and was renumbered on 12
          November, unchanged, when the advisor comparison became Experiment
          10 <PaperCite n={4} />. The Spark runs one trainer at a time, so
          this experiment waits until Experiment 10 is done. Nothing is
          authorized to run until review.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
