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

const SLUG = "2026-10-24-e07-smoke3-memory";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  { href: "#result", label: "Smoke 3" },
  { href: "#memory", label: "Why it runs out of memory" },
  { href: "#options", label: "Options" },
  { href: "#next", label: "Next" },
  { href: "#notes", label: "Notes" },
  { href: "#references", label: "References" },
];

const references = [
  {
    id: 1,
    href: "/journal/2026-10-24-e07-reward-cap-smokes",
    text: "Davis, S. (2026). Experiment 7: the released config zeroes most resolved training rollouts. Hecate Lab journal, 24 October 2026.",
  },
  {
    id: 2,
    href: "https://arxiv.org/abs/2510.02453",
    text: "Asawa, P., Zhu, A., O’Neill, A., Zaharia, M., Dimakis, A. G., and Gonzalez, J. E. (2026). How to Train Your Advisor: Steering Black-Box LLMs with Advisor Models. arXiv:2510.02453.",
  },
] as const;

export async function E07Smoke3MemoryPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 7: rewards are right, the update does not fit in two GPUs"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · GRPO smoke 3 · Flash-Lite student · 24 October 2026"
      date="October 24, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Distributed, Parallel, and Cluster Computing (cs.DC)",
        "Software Engineering (cs.SE)",
      ]}
      updated="2026-10-24"
      tags="e7 · grpo · fsdp2 · sequence parallel · cpu offload · out of memory · smoke"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Smoke 3 kept <code>max_turns=9</code> and split each sequence across
          the two A100s with Ulysses sequence parallelism. Rollouts were the best
          so far: 19 of 32 rewarded, none zeroed by length, mean reward 0.490.
          The policy update still ran out of GPU memory after about 100 seconds.
        </p>
        <p>
          The cause is the fixed memory of full fine-tuning, not the sequences
          alone. Smoke 4 moves the policy’s weights, gradients, and optimizer
          state to CPU memory (FSDP2 CPU offload). If that fails or is too slow,
          the fallback is four A100s, for which quota was approved the same day.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          The released training config zeroed most resolved rollouts through a
          4,096-token cap on the whole advisor conversation{" "}
          <PaperCite n={1} />. Raising <code>max_turns</code> to 9 fixed the
          rewards in smoke 2, but responses of up to about 31,000 tokens made
          the update run out of memory. Smoke 3 added sequence parallelism, a
          change to how the computation is spread over GPUs that leaves the
          algorithm, batch, learning rate, and reward as they were.
        </p>
      </PaperSection>

      <PaperSection id="result" number="2" title="Smoke 3">
        <PaperTable
          id="table-smokes"
          caption="Table 1. One-step GRPO smokes, 4 training issues × 8 advice samples = 32 rollouts, Flash-Lite student, 2×A100-80GB."
          headers={["Measure", "Smoke 1 (released)", "Smoke 2 (max_turns 9)", "Smoke 3 (+ seq-parallel 2)"]}
          rows={[
            ["Rewarded rollouts", "10 / 32", "11 / 32", "19 / 32"],
            ["Zeroed by length", "8", "0", "0"],
            ["Mean reward", "0.057 after zeroing", "0.285", "0.490"],
            ["Stopped at a length limit", "30 / 32", "8 / 32", "5 / 32"],
            ["Errors", "0", "0", "0"],
            ["Rollout time", "4.4 min", "9.1 min", "7.2 min"],
            ["Training update", "completed", "out of memory", "out of memory after ~100 s"],
          ]}
          highlight={(row) => row[0] === "Training update"}
        />
        <p>
          Rewarded counts vary between smokes partly because each rollout
          samples new advice and a new student trajectory. The rewards are now
          the ones the paper describes <PaperCite n={2} />: in smokes 2 and 3 no
          resolved rollout was zeroed.
        </p>
      </PaperSection>

      <PaperSection id="memory" number="3" title="Why it runs out of memory">
        <p>
          Full fine-tuning keeps fp32 weights, gradients, and Adam state for all
          7 billion parameters. Sharded over two GPUs, that is roughly 50 to 55
          GB per A100 before any sequence is processed, and the sleeping vLLM
          engine holds about 1 GB more. Sequence parallelism halved the
          long-sequence part (activations and output logits), but what is left
          of the 80 GB is not enough for a sequence of about 31,000 tokens. The
          update already used micro-batch 1, gradient checkpointing, sample
          packing, and flash attention.
        </p>
      </PaperSection>

      <PaperSection id="options" number="4" title="Options">
        <PaperTable
          id="table-options"
          caption="Table 2. Ways to fit the update, in the order they will be tried."
          headers={["Option", "Effect on memory", "Effect on the recipe", "Cost"]}
          rows={[
            [
              "CPU offload of the policy (smoke 4)",
              "Weights, gradients, optimizer state live in CPU RAM; moved to GPU per layer",
              "None",
              "Slower update; rollouts still dominate a step",
            ],
            [
              "Four A100s (a2-ultragpu-4g)",
              "Fixed memory drops to about 25–28 GB per GPU",
              "None; global batch 4 × 8 unchanged",
              "About twice the GPU price per hour; harder to get capacity",
            ],
            [
              "LoRA",
              "Gradients and optimizer state only for small adapters",
              "New learning rate, rank, and targets; weaker reproduction claim",
              "This SkyRL’s FSDP worker does not pass a LoRA rank: code changes",
            ],
          ]}
        />
        <PaperCallout label="Decision">
          <p>
            Smoke 4 uses CPU offload with sequence parallelism and{" "}
            <code>max_turns=9</code>. If it fails, or a training step takes more
            than 15 minutes, training moves to four A100s on the same boot disk.
            LoRA is not used. Both rules were written into the spec before
            smoke 4.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <p>
          The GPU is queued as a flex-start request in us-central1-c, where
          on-demand two-A100 capacity has repeatedly been out of stock. When it
          starts, smoke 4 runs, and if it passes the 18-epoch run starts with a
          checkpoint every epoch. The spec’s Sunday-night interim evaluation
          (one pass of the latest checkpoint, labelled interim) still applies.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <p>
          Smoke 3: <code>exp-07_arm-trainsmoke_split-tenacitytrain_seed-0_run-3</code>,
          fork commit <code>175853a</code>. Smoke 4:{" "}
          <code>…_run-4</code>, fork commit <code>6ae79d9</code>. Settings live
          in <code>scripts/train_swe_smith_1k.sh</code> as{" "}
          <code>MAX_TURNS</code>, <code>SEQ_PARALLEL</code>, and{" "}
          <code>CPU_OFFLOAD</code>; each defaults to the upstream value. Quota
          approved on 24 October in project whatsapp-sales-agent, us-central1:
          A100-80GB spot and on-demand 4, A2 and preemptible CPUs 96. Both VMs
          were stopped after smoke 3.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
