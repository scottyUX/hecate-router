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

const SLUG = "2026-10-24-e07-reward-cap-smokes";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  { href: "#cap", label: "The 4,096-token cap" },
  { href: "#smokes", label: "Two smokes" },
  { href: "#paper", label: "Against the paper" },
  { href: "#decision", label: "Decision" },
  { href: "#next", label: "Next" },
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
    href: "/journal/2026-10-24-e07-check1-three-pass",
    text: "Davis, S. (2026). Experiment 7: three passes per arm clear the step gate. Hecate Lab journal, 24 October 2026.",
  },
] as const;

export async function E07RewardCapPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 7: the released config zeroes most resolved training rollouts"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · GRPO smokes · Flash-Lite student · 24 October 2026"
      date="October 24, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Software Engineering (cs.SE)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-10-24"
      tags="e7 · grpo · skyrl · max_turns · reward cap · smoke · reproduction"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Before training the advisor, a one-step GRPO smoke ran the authors’
          released training settings unchanged. It found that 30 of 32 rollouts
          ended at a 4,096-token cap on the whole advisor conversation, and that
          8 of the 10 rollouts where the student fixed the bug were scored 0
          because of it. Mean reward fell from 0.273 to 0.057.
        </p>
        <p>
          With <code>generator.max_turns=9</code>, a second smoke kept every
          resolved rollout’s reward (11 rewarded, 0 zeroed, mean 0.285) but ran
          out of GPU memory in the training update on the longer sequences.
          Training has not started. The next step is sequence parallelism across
          the two GPUs.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          Check 1 passed on 24 October: the untrained advisor is 3.7 steps faster
          than Flash-Lite alone and solves 20.6 points fewer issues{" "}
          <PaperCite n={2} />. The next step is to train the advisor with GRPO:
          56 training issues, 18 epochs, batch 4, group 8, on one
          2×A100-80GB machine. The spec requires a one-step smoke first, with
          pass rules fixed before it runs. One rule stops training if more than
          90% of rollouts end at the length cap.
        </p>
      </PaperSection>

      <PaperSection id="cap" number="2" title="The 4,096-token cap">
        <p>
          A training rollout is one advisor conversation. After the prompt, the
          advisor writes advice every 5 student steps, and SkyRL appends an
          observation between its turns: the student’s last 10 messages with
          full command output. Observations, often 1,500 to 5,000 tokens each,
          are much larger than the advice.
        </p>
        <p>
          The released script leaves <code>generator.max_turns</code> at SkyRL’s
          default of 1, a setting for single-turn tasks. SkyRL then caps
          everything after the prompt, advice and observations together, at{" "}
          <code>max_generate_length</code> = 4,096 tokens. Longer rollouts are
          truncated and marked as stopped for length, and{" "}
          <code>zero_reward_on_non_stop=true</code> sets their reward to 0, even
          when the student resolved the issue. In practice only rollouts that
          finish within about one or two advice rounds (5 to 10 student steps)
          keep their reward. Flash-Lite averages 22 to 26 steps.
        </p>
        <PaperCallout label="Whose code">
          <p>
            This is the authors’ released implementation, not ours. Our training
            script copied the setting from their{" "}
            <code>train_swe_smith_advisor.sh</code>, and the vendored SkyRL
            config and generator are identical to upstream commit{" "}
            <code>f27efa7</code>. Our only SkyRL edit is a log line that counts
            rollouts stopped for length and rewards about to be zeroed.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="smokes" number="3" title="Two smokes">
        <p>
          Both smokes ran one GRPO step on the same 4 training issues × 8 advice
          samples = 32 rollouts, with Flash-Lite as the student. Two of the 4
          issues were ones Flash-Lite had solved in 6 to 7 steps, so the sample
          leans toward short runs.
        </p>
        <PaperTable
          id="table-smokes"
          caption="Table 1. One-step GRPO smokes. Smoke 1 uses the released settings (max_turns 1). Smoke 2 sets max_turns 9; nothing else changes."
          headers={["Measure", "Smoke 1 (released)", "Smoke 2 (max_turns 9)"]}
          rows={[
            ["Rollouts with raw reward > 0", "10 / 32", "11 / 32"],
            ["Of those, zeroed by the length cap", "8", "0"],
            ["Mean reward before → after zeroing", "0.273 → 0.057", "0.285, kept"],
            ["Rollouts stopped for length", "30 / 32", "8 / 32"],
            ["Errors", "0", "0"],
            ["Rollout time for 32", "4.4 min", "9.1 min"],
            ["Training update", "completed", "CUDA out of memory"],
            ["Verdict", "fail: length rule", "fail: out of memory"],
          ]}
          highlight={(row) => row[0].startsWith("Of those")}
        />
        <p>
          In smoke 2 the 8 rollouts stopped for length were unresolved runs that
          reached the 28,672-token advisor input limit, the prompt limit the
          paper lists. None of them had a reward to lose.
        </p>
        <p>
          The out-of-memory error came in the policy update, on GPU 0 (79 GB
          full). The update already runs with micro-batch 1, gradient
          checkpointing, sample packing, and flash attention. A response of
          about 31,000 tokens is the remaining cost: the output logits alone are
          roughly 32,000 tokens × 152,000 vocabulary entries, about 20 GB in
          fp32.
        </p>
      </PaperSection>

      <PaperSection id="paper" number="4" title="Against the paper">
        <p>
          Appendix C.1 of Asawa et al. gives the reward as 0 if unresolved and
          0.5 + 0.5 × (40 − steps)/40 if resolved, with no length condition{" "}
          <PaperCite n={1} />. Their Table 1 lists a 28,672-token maximum prompt
          and a 4,096-token maximum generation, which read as per-prompt and
          per-reply limits. The paper does not mention <code>max_turns</code> or
          zeroing on truncation, and it describes training on “a lightly modified
          fork of SkyRL”, so the run behind their numbers may differ from the
          released code.
        </p>
        <p>
          If they did train with the cap, a stronger student (Flash) would have
          lost fewer rewards, and about 2.5× as many updates (30 epochs at batch
          8) would have helped. A cap that rewards only fast successes also fits
          their headline of fewer steps. The cap is mostly structural: Flash’s
          typical solved run (about 17 steps, 4 advice rounds) would also pass
          4,096 tokens.
        </p>
      </PaperSection>

      <PaperSection id="decision" number="5" title="Decision">
        <p>
          Training uses <code>generator.max_turns=9</code>, recorded in the spec
          as a deviation from the released code before smoke 2 ran. Each
          advisor reply keeps its 4,096-token limit, the advisor input keeps its
          28,672-token limit, and <code>zero_reward_on_non_stop</code> stays on.
          A resolved rollout now receives the reward the paper describes.
        </p>
        <p>
          Kept as a diagnostic, not a gate: a Flash-student smoke under the
          released setting, to measure how often the cap hits the paper’s own
          student, and a question to the authors about the settings of their SWE
          run.
        </p>
      </PaperSection>

      <PaperSection id="next" number="6" title="Next">
        <p>
          Smoke 3 adds sequence parallelism (<code>sequence_parallel_size=2</code>{" "}
          for the policy and reference model). It splits each long sequence
          across the two GPUs and leaves the algorithm, batch, learning rate, and
          reward unchanged. If it still runs out of memory, the fallback is CPU
          offload of weights and optimizer state, which is slower. The 18-epoch
          run starts only after a smoke passes.
        </p>
        <p>
          Rollouts now take about 9 minutes per step before the update, so the
          18 epochs take longer than first planned. The spec’s Sunday-night
          interim evaluation (one pass of the latest checkpoint, labelled
          interim) still applies once training is running.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="7" title="Notes">
        <p>
          Smoke run ids: <code>exp-07_arm-trainsmoke_split-tenacitytrain_seed-0</code>{" "}
          (fork commit <code>fc2c988</code>) and{" "}
          <code>exp-07_arm-trainsmoke_split-tenacitytrain_seed-0_run-2</code>{" "}
          (<code>8809f18</code>). Logs and <code>smoke_summary.json</code> are on
          the <code>gpu-advisor</code> boot disk under <code>runs/</code>.
          Smoke issues: <code>func_basic__fyidz2ap</code>,{" "}
          <code>pr_425</code>, <code>func_basic__wx2vx0ly</code>,{" "}
          <code>combine_file__4gcf36bk</code>. The GPU ran on flex-start
          provisioning after on-demand 2×A100 was out of stock in us-central1-a
          and us-central1-c. Both machines were stopped after each failed smoke.
          Evaluation scripts have no response cap, so the student-alone,
          untrained, and check-1 results are unaffected.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
