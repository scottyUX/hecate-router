import Link from "next/link";

import {
  PaperAbstract,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";

const SLUG = "2026-10-23-e07-untrained-advisor";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  { href: "#method", label: "Method" },
  { href: "#result", label: "Result" },
  { href: "#interpretation", label: "Interpretation" },
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
    href: "/journal/2026-10-19-e07-week1-student-baselines",
    text: "Davis, S. (2026). Experiment 7: Flash-Lite baselines and an efficiency prompt. Hecate Lab journal, 19 October 2026.",
  },
] as const;

export async function E07UntrainedAdvisorPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 7: untrained advisor does not clear the step gate"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · 49 test issues · Flash-Lite student · 23 October 2026"
      date="October 23, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-10-24"
      tags="e7 · untrained advisor · flash-lite · qwen2.5-7b · tenacity · stop"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          <strong>Update, 24 October 2026.</strong> This entry reads one pass
          per arm. The spec was then amended to decide check 1 on three passes
          per arm, and the six-file join passed (step gap 3.7, resolve gap 20.6
          points). See{" "}
          <Link href="/journal/2026-10-24-e07-check1-three-pass">
            Experiment 7: three passes per arm clear the step gate
          </Link>
          . The text below is unchanged.
        </p>
        <p>
          The untrained Qwen2.5-7B-Instruct advisor was run once on the 49
          Tenacity test issues, with Gemini 2.5 Flash-Lite as the student and
          no GRPO. The valid pass solved 7/49 (14.3%) in 21.86 mean steps, with
          0 errors, against Flash-Lite alone at 22/49 and 23.8 steps
          <PaperCite n={2} />.
        </p>
        <p>
          The step gap is 1.94, under the locked cutoff of 2. The rule for that
          case is to stop. GRPO was not started. The GPU was stopped after the
          number was read.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          Figure 3 of Asawa et al. uses Gemini 2.5 Flash
          <PaperCite n={1} />. Their untrained advisor cuts steps from 19.1 to
          13.7 and resolve from 61.2% to 52.6%. Training is what brings resolve
          back. Our student is Flash-Lite, so the comparison is with our own
          student-only pass, not with 13.7 steps.
        </p>
        <p>
          The locked check, written before this run, is: untrained mean steps at
          least 2 below Flash-Lite alone (23.8), and resolve below 22/49. A step
          gap under 2 means do not train. A step drop of at least 2 whose
          resolve does not fall is partial: train, and record that there was no
          trade-off to recover. The efficiency sentence is not this baseline. It
          solved 14/49 in 26.6 steps.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <p>
          One pass, one issue at a time, full{" "}
          <code>validation_jd__tenacity.json</code>, no{" "}
          <code>--num_samples</code>. The advisor is Qwen2.5-7B-Instruct with
          its original weights, served locally as <code>advisor</code> with a
          32,768-token context. It comments every 5 student steps. Sampling is
          temperature 0.7, top_p 0.8, top_k 20, min_p 0. The student is{" "}
          <code>openrouter/google/gemini-2.5-flash-lite</code>.
        </p>
        <p>
          The first full attempt,{" "}
          <code>exp-07_arm-untrained_split-tenacityval_seed-0</code>, scored 23
          of 49 and errored on 26. Twenty-one died because the advisor request
          was about 34,887 tokens, past the 32,768 cap: 30,791 tokens of
          transcript and 4,096 reserved for the reply. Five died on the first
          student call when OpenRouter forwarded Google’s 404 that Gemini 2.5
          Flash-Lite is closed to new API users. The same model id worked on the
          other issues in that run. Those 26 are infrastructure. The 9 resolves
          among the 23 scored issues are not the gate.
        </p>
        <p>
          Before the rerun, two changes were made. Each advisor call reserves
          1,024 tokens for the reply, and the request keeps the task, the
          previous advice, and the latest observation, capped at the last 60,000
          characters. A “no longer available to new users” 404 is retried up to
          four times, waiting 4, 8, 16, then 32 seconds. A first restart of the
          worker omitted the LiteLLM price file, and that attempt (
          <code>_run-2</code>) was stopped after the first issue.{" "}
          <code>_run-3</code> is the pass below. Two A100-80GB machines were out
          of stock, so this serving job used one A100-80GB. Serving the 7B model
          does not need two GPUs. The GPU was stopped when the log was read.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <PaperTable
          id="table-gate"
          caption="Table 1. Flash-Lite on the 49 test issues. Alone is run-5. Untrained is run-3. Both have 0 errors. The step gap is 23.8 minus 21.86."
          headers={["Arm", "Resolved", "Rate", "Mean steps", "Steps on solved", "Cost"]}
          rows={[
            ["Flash-Lite alone", "22/49", "44.9%", "23.8", "21.1", "$2.97"],
            ["Untrained advisor", "7/49", "14.3%", "21.86", "15.86", "$3.16"],
          ]}
          highlight={(row) => row[0].startsWith("Untrained")}
        />
        <p>
          Resolve fell by 15 issues. Mean steps fell by 1.94. Solved issues took
          15.86 steps instead of 21.1. The paper’s untrained row is 52.6% and
          13.7 steps on Flash, which is a different student and a repeated-run
          average.
        </p>
        <PaperTable
          id="table-attempts"
          caption="Table 2. Attempts at the untrained arm. Only run-3 is a scored 49."
          headers={["Run", "What happened", "Use"]}
          rows={[
            [
              "untrained, no run suffix",
              "26/49 errors: 21 context limit, 5 Flash-Lite 404",
              "Infrastructure",
            ],
            [
              "run-2",
              "Stopped after one issue. Worker had no LiteLLM price file.",
              "Infrastructure",
            ],
            [
              "run-3",
              "49/49 scored. 7 resolved. 21.86 mean steps. 0 errors.",
              "The gate",
            ],
          ]}
          highlight={(row) => row[0] === "run-3"}
        />
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          Check 1 does not pass, and it is not the partial case. The partial
          case needs a step drop of at least 2. This drop is 1.94. The locked
          rule says a step gap under 2 stops the experiment. Resolve fell a long
          way, from 22 to 7, so there is not a small resolve cost sitting on top
          of a real speed-up. There is a small speed-up and a large resolve
          loss.
        </p>
        <p>
          On the issues the untrained advisor still solved, steps were lower
          (15.86 versus 21.1). That is the same shape as the efficiency
          sentence, which also shortened the successes and lost issues. It is
          not enough to start GRPO. Training would be spent trying to recover a
          trade-off the untrained model did not create.
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <p>
          Do not start GRPO. Do not run the trained-advisor eval.{" "}
          <code>gpu-advisor</code> is stopped. The 7B weights remain on the boot
          disk in <code>us-central1-c</code>.
        </p>
        <p>
          A later attempt needs a reason to reopen the gate, not a rerun of this
          recipe. The 2×A100 shape was out of stock on 22 October. That blocked
          training. It did not block this serving pass, and it is not why the
          gate failed.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <p>
          Valid run id:{" "}
          <code>exp-07_arm-untrained_split-tenacityval_seed-0_run-3</code>.
          Log and session map are on <code>gpu-advisor</code> under{" "}
          <code>runs/</code> of that id. The student-only row it is compared
          with is{" "}
          <code>exp-07_arm-weakalone_split-tenacityval_seed-0_run-5</code>.
          Advisor code for the rerun is the local edit on top of{" "}
          <code>3ada694</code>: shorter advisor requests, and a delayed retry
          for the Flash-Lite 404. The worker agent server for run-3 was started
          with <code>LITELLM_MODEL_REGISTRY_PATH</code> set. Run-2 was not.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
