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

const SLUG = "2026-10-24-e08-handoff-modes-plan";

const toc: PaperTocItem[] = [
  { href: "#question", label: "Question" },
  { href: "#setup", label: "Setup" },
  { href: "#steps", label: "Steps" },
  { href: "#measures", label: "What we measure" },
  { href: "#budget", label: "Budget" },
  { href: "#risks", label: "Risks" },
  { href: "#open", label: "Open points" },
  { href: "#notes", label: "Notes" },
  { href: "#references", label: "References" },
];

const references = [
  {
    id: 1,
    href: "https://arxiv.org/abs/2608.03893",
    text: "Heo, T. et al. (2026). Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse. NVIDIA. arXiv:2608.03893.",
  },
  {
    id: 2,
    href: "https://arxiv.org/abs/2310.06770",
    text: "Jimenez, C. E. et al. (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR. arXiv:2310.06770.",
  },
  {
    id: 3,
    href: "https://github.com/SWE-agent/mini-swe-agent",
    text: "Yang, J. et al. (2025). mini-SWE-agent. Princeton NLP / SWE-agent.",
  },
] as const;

export async function E08HandoffModesPlanPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 8: three ways to hand a coding task to a stronger model"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-bench Verified · Qwen3-8B → Qwen3-14B · one L4 · plan · 24 October 2026"
      date="October 24, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Computation and Language (cs.CL)",
        "Software Engineering (cs.SE)",
      ]}
      updated="2026-10-24"
      tags="e8 · handoff · kv cache transfer · escalation · qwen3 · swe-bench · plan"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          A router that escalates mid-run has to tell the strong model what the
          cheap model already did. Experiment 8 compares three ways: the strong
          model re-reads the full trajectory, reads a short summary written by
          the cheap model, or receives the cheap model’s KV cache translated
          into its own format with a closed-form linear mapping{" "}
          <PaperCite n={1} />. The hope is full-text quality at summary cost and
          speed.
        </p>
        <p>
          This entry records the plan before any run. It is an initial
          experiment: 100 test tasks, one seed, about $100 on one L4 over one to
          two weeks, with a go/no-go after a day-5 quick test so a weak result
          costs about $30.
        </p>
      </PaperAbstract>

      <PaperSection id="question" number="1" title="Question">
        <p>
          The cheap model gets stuck partway, and the task goes to the strong
          model. Which handoff gives the strong model the most useful context
          for the least time and money, and which passes on the cheap model’s
          mistakes?
        </p>
        <PaperTable
          id="table-modes"
          caption="Table 1. The three handoff modes."
          headers={["Mode", "What the strong model gets", "Expected trade-off"]}
          rows={[
            ["Full text", "Every step the cheap model took, re-read (prefilled)", "Complete; re-reading costs time and money"],
            ["Summary", "A note of at most 400 tokens written by the cheap model", "Cheap; details get lost"],
            ["KV transfer", "The cheap model’s KV cache, mapped to the strong model’s layers", "Reads nothing; quality is the open question"],
          ]}
        />
      </PaperSection>

      <PaperSection id="setup" number="2" title="Setup">
        <PaperTable
          id="table-setup"
          caption="Table 2. Fixed choices."
          headers={["Part", "Choice"]}
          rows={[
            ["Cheap model", "Qwen3-8B (bf16)"],
            ["Strong model", "Qwen3-14B, official FP8 checkpoint"],
            ["Mode", "Non-thinking for both, every run"],
            ["Tasks", "SWE-bench Verified, non-django only (django stays clean for the router experiments)"],
            ["Harness", "mini-SWE-agent v1.0.0, bash-only, 40-step cap, 24K-token context cap, images pinned by digest"],
            ["Serving", "Hugging Face transformers; the mapped cache passed as past_key_values"],
            ["Hardware", "1 × NVIDIA L4 (g2-standard-8); one model loaded at a time, state saved to disk between stages"],
          ]}
        />
        <p>
          The gold patch is never shown to any model. It is used once, offline,
          to label wrong-path edits after runs finish.
        </p>
      </PaperSection>

      <PaperSection id="steps" number="3" title="Steps">
        <PaperTable
          id="table-steps"
          caption="Table 3. Plan, with the go/no-go after step 3."
          headers={["Step", "When", "What"]}
          rows={[
            ["1. Handoff points", "Days 1–2", "Run Qwen3-8B on ~150 tasks, stop at step 10, save transcript, container state and touched files; drop tasks already solved; split 50 fit / 100 test"],
            ["2. Translator", "Days 3–4", "Authors’ code if released, else §3 of the paper: top-8 source layers per target layer, RoPE removed, one ridge per KV head (λ = 0.01), target RoPE re-applied. Identity test must pass"],
            ["3. Quick test", "Day 5", "Next action of the 14B under each mode at the 100 test points: first-command match with full text and token-level KL. Go only if KV transfer beats the summary"],
            ["4. Real test", "Week 2", "Restore each test point and let the 14B finish under each mode: 300 runs from identical container states"],
            ["5. Latency", "After step 2", "Time each mode at 2K–24K tokens, 5 repeats"],
          ]}
          highlight={(row) => row[0].startsWith("3.")}
        />
        <PaperCallout label="Identity test">
          <p>
            Before any comparison, the 14B is given its own cache through the
            same code path. Its greedy output must match a normal run exactly.
            This separates bugs in the plumbing from the quality of the mapping.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="measures" number="4" title="What we measure">
        <p>
          <strong>Speed:</strong> time from “escalate now” to the strong model’s
          first token, split into parts (14B prefill, 8B summary writing, mapper
          compute), and the trajectory length at which KV transfer becomes
          faster than each alternative. The two models cannot share the L4, so
          parts are timed separately and summed; disk loading is reported apart.
        </p>
        <p>
          <strong>Cost:</strong> tokens the 14B reads at handoff, GPU-seconds by
          model, dollars per solved task at OpenRouter list prices snapshotted
          once, and the size of mapped caches and translator weights.
        </p>
        <p>
          <strong>Quality:</strong> tasks solved out of 100, next-action match
          and KL, steps after handoff, re-exploration of files the 8B had
          already opened, malformed commands in the first 3 steps, and runs
          that hit the context cap.
        </p>
        <p>
          <strong>Inherited mistakes:</strong> a wrong-path file is one the 8B
          edited that the gold patch does not touch. The rate at which the 14B
          keeps editing it, or leaves those edits in its final diff, is reported
          per mode. The expectation to test is that full text and KV transfer
          pass on more wrong ideas than the summary.
        </p>
      </PaperSection>

      <PaperSection id="budget" number="5" title="Budget">
        <PaperTable
          id="table-budget"
          caption="Table 4. Planned spend at about $0.85 per L4-hour."
          headers={["Step", "GPU-hours", "Cost"]}
          rows={[
            ["1. Cheap-model runs", "~15", "~$13"],
            ["2. Translator fit + identity test", "~10", "~$9"],
            ["3. Quick test", "~5", "~$4"],
            ["4. Real test (300 runs)", "~60–80", "~$50–70"],
            ["5. Latency benchmark", "~2", "~$2"],
            ["Disk and slack", "—", "~$10"],
            ["Total", "", "~$85–105"],
          ]}
          highlight={(row) => row[0] === "Total"}
        />
        <p>
          The VM is stopped whenever nothing runs. Spot is allowed for steps 1–2
          only. If step 4 tracks above 80 GPU-hours after 100 runs, it pauses.
        </p>
      </PaperSection>

      <PaperSection id="risks" number="6" title="Risks">
        <p>
          If Qwen3-14B solves fewer than 10 of 100 under full text, solved-rate
          differences mean little, and the quick test, latency and
          re-exploration results carry the conclusion. The mapping has not been
          tested on code or on an FP8 target model; that is part of the
          question. Transformers on an L4 is slow, and the 80 GPU-hour check
          catches overruns early.
        </p>
      </PaperSection>

      <PaperSection id="open" number="7" title="Open points before day 1">
        <p>
          Raised in review of the plan, to settle before the first run:
        </p>
        <PaperTable
          id="table-open"
          caption="Table 5. Points to fix in the plan."
          headers={["Point", "Why it matters"]}
          rows={[
            ["Check layer counts as well as KV heads and head size", "Qwen3-8B has 36 layers and Qwen3-14B has 40; the per-target-layer source selection covers it, but the day-1 check should say so"],
            ["Fix the 14B KV cache dtype", "With the FP8 checkpoint the mapping must target the cache dtype transformers actually uses; otherwise the identity test may not match exactly"],
            ["Name the harness conventions directly", "The plan points at an E7 section number the E7 spec does not have"],
          ]}
        />
      </PaperSection>

      <PaperSection id="notes" number="8" title="Notes">
        <p>
          Owner: to be assigned (graduate student), supervised by Scott Davis.
          Files will live under <code>experiments/e08-handoff-modes/</code>,
          with check-ins at the end of days 2, 4 and 5 and of week 2, a
          half-page go/no-go memo, and a two-page write-up. Paired comparisons
          use bootstrap 95% intervals over tasks. Possible follow-ups, only if
          results are promising: more tasks and seeds, other escalation steps,
          the django holdout, the paper’s own 14B → 32B pair on the A100s, and
          the winning handoff as the escalate action in Experiment 7. Tasks
          from SWE-bench Verified <PaperCite n={2} />, run with mini-SWE-agent{" "}
          <PaperCite n={3} />.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
