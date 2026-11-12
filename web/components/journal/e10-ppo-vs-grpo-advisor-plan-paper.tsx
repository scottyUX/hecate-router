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

const SLUG = "2026-11-12-e10-ppo-vs-grpo-advisor-plan";

const toc: PaperTocItem[] = [
  { href: "#question", label: "Question" },
  { href: "#known", label: "What Experiment 7 showed" },
  { href: "#design", label: "Design" },
  { href: "#trajectories", label: "Saved trajectories" },
  { href: "#rules", label: "Decision rules" },
  { href: "#cost", label: "Cost" },
  { href: "#risks", label: "Risks and scope" },
  { href: "#notes", label: "Notes" },
  { href: "#references", label: "References" },
];

const references = [
  {
    id: 1,
    href: "https://arxiv.org/abs/2510.02453",
    text: "Asawa, P., Zhu, A., O’Neill, A., Zaharia, M., Dimakis, A. G., and Gonzalez, J. E. (2026). How to Train Your Advisor: Steering Black-Box LLMs with Advisor Models. arXiv:2510.02453.",
  },
  {
    id: 2,
    href: "https://arxiv.org/abs/1707.06347",
    text: "Schulman, J., Wolski, F., Dhariwal, P., Radford, A., and Klimov, O. (2017). Proximal Policy Optimization Algorithms. arXiv:1707.06347.",
  },
  {
    id: 3,
    href: "https://arxiv.org/abs/2402.03300",
    text: "Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Bi, X., Zhang, H., Zhang, M., Li, Y. K., Wu, Y., and Guo, D. (2024). DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models. arXiv:2402.03300.",
  },
  {
    id: 4,
    href: "/journal/2026-10-26-e07-final-results",
    text: "Davis, S. (2026). Experiment 7: the trained advisor across three students. Hecate Lab journal, 26 October 2026.",
  },
  {
    id: 5,
    href: "/journal/2026-11-12-e11-ppo-vs-grpo-router-plan",
    text: "Davis, S. (2026). Experiment 11: PPO vs GRPO for the router, on the DGX Spark. Hecate Lab journal, 12 November 2026.",
  },
] as const;

export async function E10PpoVsGrpoAdvisorPlanPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 10: PPO vs GRPO for the advisor, all on the DGX Spark"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · local Qwen3-Coder-30B student · Qwen2.5-7B advisor, LoRA · DGX Spark · plan · 12 November 2026"
      date="November 12, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Software Engineering (cs.SE)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-11-12"
      tags="e10 · advisor models · ppo · grpo · reinforcement learning · lora · dgx spark · qwen3-coder · plan"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Experiment 7 trained a Qwen2.5-7B advisor with GRPO, following
          Advisor Models <PaperCite n={1} />, to advise Gemini 2.5 Flash-Lite
          on SWE-smith Tenacity. GRPO <PaperCite n={3} /> drops PPO’s learned
          critic <PaperCite n={2} /> and scores each run against the average
          of 8 runs on the same issue. The advisor did not beat Flash-Lite
          alone <PaperCite n={4} />.
        </p>
        <p>
          Experiment 10 trains the same kind of advisor twice, once with GRPO
          and once with PPO, both with LoRA, and changes only how each run is
          scored. To spend almost nothing, everything runs on the lab’s DGX
          Spark: the trainer, the advisor, a local Qwen3-Coder-30B student and
          the test containers. Every training rollout is saved as state,
          action and reward. This entry records the plan before any run.
        </p>
      </PaperAbstract>

      <PaperSection id="question" number="1" title="Question">
        <PaperTable
          id="table-questions"
          caption="Table 1. Pre-registered questions, with the predictions recorded before any run."
          headers={["ID", "Question", "Prediction"]}
          rows={[
            ["Q10.1", "Does the PPO advisor beat the GRPO advisor on resolve or steps on the 49 test issues?", "No detectable difference"],
            ["Q10.2", "Does either trained advisor beat the student alone?", "No"],
            ["Q10.3", "Does either trained advisor beat the untrained advisor?", "Yes, on resolve"],
            ["Q10.4", "Training: reward, KL, share of zero-signal groups, critic quality, memory.", "PPO has more non-zero advantages, by construction"],
          ]}
        />
        <PaperCallout label="Why PPO might help here">
          <p>
            When every run in a group of 8 fails, or every run succeeds in the
            same number of steps, the group has zero spread and GRPO learns
            nothing from it. PPO’s critic predicts the final reward from the
            conversation so far, so each turn of advice gets its own score
            even then. Whether that makes a better advisor is the question.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="known" number="2" title="What Experiment 7 showed">
        <PaperTable
          id="table-e07"
          caption="Table 2. Experiment 7, 49 Tenacity test issues, 40-step cap. Flash-Lite three passes; Qwen3-Coder-30B two passes through OpenRouter (pilot)."
          headers={["Student", "Arm", "Resolve", "Mean steps"]}
          rows={[
            ["Flash-Lite", "Alone", "34.0%", "25.7"],
            ["Flash-Lite", "+ untrained advisor", "13.5%", "22.0"],
            ["Flash-Lite", "+ GRPO advisor (full fine-tune)", "31.9%", "26.3"],
            ["Qwen3-Coder-30B", "Alone", "58.5%", "22.6"],
            ["Qwen3-Coder-30B", "+ Flash-Lite’s GRPO advisor", "53.2%", "23.2"],
          ]}
          highlight={(row) => row[0] === "Qwen3-Coder-30B" && row[1] === "Alone"}
        />
        <p>
          Qwen3-Coder-30B resolves well over half the issues, so more groups
          of 8 mix resolved and unresolved runs than with Flash-Lite, and it
          is small enough to serve on the Spark. Flash-Lite’s advisor did not
          transfer to it; Experiment 10 trains for it directly. These numbers
          are context only: Experiment 10 reruns the student alone and with
          the untrained advisor on the Spark’s own serving stack.
        </p>
      </PaperSection>

      <PaperSection id="design" number="3" title="Design">
        <PaperTable
          id="table-setup"
          caption="Table 3. Setup, shared by both trained arms."
          headers={["Part", "Choice"]}
          rows={[
            ["Task", "SWE-smith Tenacity: 56 training issues, 49 test issues, mini-SWE-agent, 40-step cap, advice every 5 steps"],
            ["Student", "Qwen3-Coder-30B-A3B-Instruct, FP8, served by vLLM on the Spark; not trained"],
            ["Advisor", "Qwen2.5-7B-Instruct, LoRA rank 32 on all linear layers, LR 1e-5"],
            ["Tests", "Tenacity containers rebuilt for ARM and run on the Spark, checked against the x86 image"],
            ["Reward", "Experiment 7’s: 0.5 + 0.5 × (40 − steps)/40 if the hidden tests pass, else 0"],
            ["Training", "4 issues × 8 rollouts per step, KL 0.001, one seed; 295 steps, or 150 if the smoke shows 295 does not fit"],
          ]}
        />
        <PaperTable
          id="table-arms"
          caption="Table 4. Arms. Both trained arms draw the same 32 student runs per step; only the advantage, and PPO’s critic, differ."
          headers={["Arm", "What it is", "Extra model"]}
          rows={[
            ["G: GRPO", "Run reward minus its group’s mean, divided by the group’s spread; the same value on every advice token", "None"],
            ["P: PPO", "Final reward minus a critic’s estimate at each advice turn (γ = 1, λ = 1)", "Qwen2.5-1.5B critic with its own LoRA"],
            ["A: alone", "The student with no advisor", "None"],
            ["U: untrained", "The student with the untrained Qwen2.5-7B advisor", "None"],
          ]}
        />
        <p>
          <strong>Evaluation.</strong> Three passes per arm on the 49 test
          issues, with Experiment 7’s eval sampling. Comparisons use paired
          bootstrap intervals over issues.
        </p>
        <p>
          <strong>Memory.</strong> The student (~31 GB at FP8), the advisor’s
          vLLM, the LoRA trainer and the 1.5B critic share the Spark’s ~114
          GiB. If PPO does not fit, the advisor’s vLLM sleeps during updates;
          after that, the student drops to Qwen3-8B for both arms.
        </p>
      </PaperSection>

      <PaperSection id="trajectories" number="4" title="Saved trajectories">
        <p>
          Every training rollout of both arms is saved, so the training data
          can be re-analysed, or reused for offline RL, without rerunning.
          One record per advice turn, gzipped JSON Lines, one file per
          training step.
        </p>
        <PaperTable
          id="table-trajectories"
          caption="Table 5. What each advice-turn record holds."
          headers={["Field", "Contents"]}
          rows={[
            ["State", "The advisor’s full input at that turn: the issue and the student’s conversation so far"],
            ["Action", "The advice text, its token ids and log-probabilities under the policy and the reference"],
            ["Reward", "Resolved, student steps and the scalar reward for the rollout"],
            ["Training", "The advantage on this turn; PPO’s critic value and return; GRPO’s group mean and spread"],
            ["Student", "Per rollout, mini-SWE-agent’s full trajectory and the test report"],
          ]}
        />
      </PaperSection>

      <PaperSection id="rules" number="5" title="Decision rules">
        <PaperTable
          id="table-rules"
          caption="Table 6. Fixed before any Experiment 10 run, using Experiment 7’s reading rule for a difference X − Y."
          headers={["Outcome", "Rule"]}
          rows={[
            ["X raises resolve", "Resolve 95% lower bound > 0"],
            ["X keeps resolve and cuts steps", "Steps 95% upper bound < 0 and resolve 95% lower bound > −10 points"],
            ["Otherwise", "“No detectable difference at n = 49, one training seed”"],
            ["Q10.1", "PPO − GRPO, either reading, in either direction"],
            ["Q10.2, Q10.3", "Each trained arm − alone, and − untrained"],
          ]}
        />
      </PaperSection>

      <PaperSection id="cost" number="6" title="Cost">
        <PaperTable
          id="table-cost"
          caption="Table 7. Estimated cost. No paid inference: the student and the advisor run on the Spark."
          headers={["Item", "Cost"]}
          rows={[
            ["Student and advisor inference", "$0 (local)"],
            ["Spark GPU", "$0 (lab-owned)"],
            ["APIs", "$0 (none used)"],
            ["x86 worker, once, for the container check", "~$2"],
            ["Storage for runs and trajectories", "~$1–5 a month"],
            ["Electricity", "A few tens of dollars at most"],
            ["Cap", "$50 total"],
          ]}
          highlight={(row) => row[0] === "Cap"}
        />
      </PaperSection>

      <PaperSection id="risks" number="7" title="Risks and scope">
        <p>
          One training seed per arm and 49 test issues, with passes that vary
          by up to about 19 points: “no detectable difference” is the most
          likely outcome, and the training curves are the lower-noise result.
          The results are not comparable with Experiment 7’s: the student,
          LoRA and the serving stack all differ. The ARM containers must give
          the same pass/fail as the x86 ones, or the experiment stops. SkyRL’s
          LoRA path and PPO critic are unverified on the Spark’s ARM CPU.
        </p>
        <p>
          Out of scope: other students, repos or harnesses, advise-or-escalate,
          full fine-tuning, and the M1/M2 router (Experiment 11{" "}
          <PaperCite n={5} />).
        </p>
      </PaperSection>

      <PaperSection id="notes" number="8" title="Notes">
        <p>
          Spec: <code>experiments/e10-ppo-vs-grpo-advisor/spec.md</code> (rev
          4), including a constitution check. An earlier version of this plan
          kept Experiment 7’s Flash-Lite student and the x86 worker, at about
          $1,500–1,750; this one moves everything onto the Spark. Gates before
          any full run: the Spark environment and the ARM container check
          (G0), memory (G1), a 3-step smoke with trajectory saving (G2), the
          copy off the Spark (G3) and offline tests (G4). Nothing is
          authorized to run until review.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
