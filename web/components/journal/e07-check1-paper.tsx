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

const SLUG = "2026-10-24-e07-check1-three-pass";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  { href: "#method", label: "Method" },
  { href: "#result", label: "Result" },
  { href: "#interpretation", label: "Interpretation" },
  { href: "#paper", label: "Against the paper" },
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
    href: "/journal/2026-10-23-e07-untrained-advisor",
    text: "Davis, S. (2026). Experiment 7: untrained advisor does not clear the step gate. Hecate Lab journal, 23 October 2026.",
  },
  {
    id: 3,
    href: "/journal/2026-10-19-e07-week1-student-baselines",
    text: "Davis, S. (2026). Experiment 7: Flash-Lite baselines and an efficiency prompt. Hecate Lab journal, 19 October 2026.",
  },
] as const;

export async function E07Check1Paper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 7: three passes per arm clear the step gate"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · 49 test issues · Flash-Lite student · 24 October 2026"
      date="October 24, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-10-24"
      tags="e7 · untrained advisor · flash-lite · qwen2.5-7b · tenacity · check 1 · pass"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Check 1 asks whether an untrained Qwen2.5-7B-Instruct advisor makes
          Gemini 2.5 Flash-Lite take fewer steps on the 49 Tenacity test issues,
          at some cost in resolve rate. That trade-off is what GRPO training is
          meant to repair <PaperCite n={1} />. On one pass per arm the step gap
          was 1.94, under the cutoff of 2 <PaperCite n={2} />.
        </p>
        <p>
          Three passes per arm, joined issue by issue, give a mean step gap of
          3.7 [+0.6, +6.7] and a resolve gap of 20.6 points [+12.1, +29.8] on 47
          kept issues. Check 1 passes on the point estimate. The decision to use
          three passes was recorded after the one-pass number was known. The
          lower bound of the step gap is under 2.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          The 23 October entry read one untrained pass (run-3: 7/49, 21.86
          steps) against one student-alone pass (run-5: 22/49, 23.8 steps) and
          stopped the experiment on a gap of 1.94 <PaperCite n={2} />. The
          original spec had locked check 1 as the mean of three passes per arm.
          The one-pass reading was a deviation from that.
        </p>
        <p>
          Before any new pass ran, the spec was amended to decide check 1 on
          three passes per arm, with six named run ids, a final stop if the
          three-pass gap is still under 2, and no fourth pass. That amendment
          was written after run-3’s 1.94 was known, and it says so. The
          student-alone baseline also moved between passes (22, 13, 13 of 49),
          which is why one pass per arm was too noisy to decide on.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <p>
          Same recipe as the 23 October pass. Student{" "}
          <code>openrouter/google/gemini-2.5-flash-lite</code>, one issue at a
          time, full <code>validation_jd__tenacity.json</code>. The untrained
          advisor is Qwen2.5-7B-Instruct served locally as <code>advisor</code>,
          temperature 0.7, top_p 0.8, top_k 20, min_p 0, advising every 5
          student steps. The advisor sees the task, its last advice, and the
          latest observation, with a 1,024-token reply. Training uses the whole
          conversation. This short context is fixed for every advisor arm,
          including a later trained arm.
        </p>
        <p>
          The four new passes ran in alternating order on fork commit{" "}
          <code>93678ef</code>: student-alone run-6, untrained run-4,
          student-alone run-7, untrained run-5. Student-alone run-5 is the 18
          October pass on <code>3ada694</code>. That commit difference inside
          the set is recorded, not rerun. Each pass writes a session map keyed
          by issue, with errored issues kept as error rows.
        </p>
        <p>
          Untrained run-5 took three attempts. Attempt 1 stopped at 22/49 when
          the GPU VM was stopped by hand. Attempt 2 stopped at 43/49 when the
          Spot VM was preempted at 01:09, and a Spot restart at 01:27 was
          preempted again within a minute. The spec was amended before attempt
          3 to name it as the replacement. Attempt 3 ran all 49 issues on
          on-demand provisioning (quota approved that night), same commit and
          flags, exit 0. Only attempt 3’s map is a gate file. The two partial
          logs are kept.
        </p>
        <p>
          <code>scripts/compare_swe_arms.py</code> joins the six maps on issue
          id. An issue that errored in any file is dropped from both arms.
          Differences are paired per issue. The 95% intervals bootstrap over
          issues.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <PaperTable
          id="table-files"
          caption="Table 1. The six gate files. Steps here include errored rows; the join drops them."
          headers={["Arm", "Run", "Commit", "Errors", "Resolved", "Mean steps", "Cost"]}
          rows={[
            ["Flash-Lite alone", "run-5", "3ada694", "0", "22/49", "23.8", "$2.97"],
            ["Flash-Lite alone", "run-6", "93678ef", "1", "13/49", "24.4", "$2.69"],
            ["Flash-Lite alone", "run-7", "93678ef", "1", "13/49", "27.2", "$3.24"],
            ["Untrained advisor", "run-3", "93678ef", "0", "7/49", "21.9", "$3.16"],
            ["Untrained advisor", "run-4", "93678ef", "0", "6/49", "21.5", "$2.85"],
            ["Untrained advisor", "run-5", "93678ef", "0", "6/49", "24.9", "$3.98"],
          ]}
        />
        <PaperTable
          id="table-join"
          caption="Table 2. Three-pass means on the 47 issues kept by the join."
          headers={["Arm", "Repeats", "Resolve", "Mean steps", "Steps on resolved"]}
          rows={[
            ["Flash-Lite alone", "3", "34.0%", "25.7", "19.9"],
            ["Untrained advisor", "3", "13.5%", "22.0", "16.8"],
          ]}
          highlight={(row) => row[0].startsWith("Untrained")}
        />
        <PaperTable
          id="table-diff"
          caption="Table 3. Paired difference, Flash-Lite alone minus untrained advisor, with 95% bootstrap intervals over issues."
          headers={["Measure", "Difference", "95% interval"]}
          rows={[
            ["Mean steps", "+3.7", "+0.6 to +6.7"],
            ["Resolve", "+20.6 points", "+12.1 to +29.8"],
          ]}
        />
        <p>
          The join dropped two issues, both from errors in a student-alone file:{" "}
          <code>combine_file__1n8ql04e</code> (run-6) and{" "}
          <code>func_pm_ctrl_shuffle__6vzkm0lh</code> (run-7). Both are the
          agent server deleting a session it saw as idle after 600 seconds. The
          student-alone arm sends one 40-step request per issue, so a slow issue
          looks idle. These are infrastructure errors, not student failures.
        </p>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          Check 1 passes. The untrained advisor is 3.7 steps faster on average,
          above the cutoff of 2, and it solves 20.6 points fewer issues. That is
          the trade-off GRPO is supposed to repair: keep the speed, recover the
          resolve rate. It is not the partial case, because resolve did fall.
        </p>
        <PaperCallout label="How strong the pass is">
          <p>
            The rule is on the point estimate, and the point estimate clears it.
            The interval does not: its lower end is +0.6 steps. The resolve cost
            is much clearer than the speed-up. The amendment that moved check 1
            to three passes was written after the one-pass result. The
            outcome is a pass under a rule that was changed once, in the
            direction the original spec had already specified.
          </p>
        </PaperCallout>
        <p>
          Student-alone variance is large. Run-5 solved 22/49, runs 6 and 7
          solved 13/49 each. A single pass on 49 issues cannot settle either
          check 1 or a later check 3.
        </p>
      </PaperSection>

      <PaperSection id="paper" number="5" title="Against the paper">
        <p>
          Asawa et al. report, with Gemini 2.5 Flash as the student, 61.2% and
          19.1 steps alone and 52.6% and 13.7 steps with the untrained advisor{" "}
          <PaperCite n={1} />. Our Flash harness check matched their
          student-alone row (31/49, 63.3%, 19.4 steps) <PaperCite n={3} />. With
          Flash-Lite the untrained advisor moves in the same direction but costs
          more resolve (20.6 points against 8.6) and saves fewer steps (3.7
          against 5.4). The student is weaker and the advisor eval context is
          shorter than theirs, so the sizes are not comparable. The direction
          is.
        </p>
      </PaperSection>

      <PaperSection id="next" number="6" title="Next">
        <p>
          Train the advisor: GRPO on the 56 training issues, 18 epochs, batch 4,
          group 8, on one 2×A100-80GB machine (<code>a2-ultragpu-2g</code>),
          on-demand rather than Spot after two preemptions in one night.
          Checkpoints every epoch. A one-step smoke on four issues comes first
          and must show rewarded rollouts, few errors, no out-of-memory, and a
          recorded fraction of rollouts ended by the 4,096-token response cap.
        </p>
        <p>
          The trained arm is then scored with the same short eval. Check 2:
          trained mean steps below student-alone. Check 3: trained resolve above
          the untrained arm and no more than 10 points below the student-alone
          three-pass mean on the joined issues, which is 24.0% here. The 18/49
          figure in earlier notes came from run-5 alone and is superseded.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="7" title="Notes">
        <p>
          Gate files are in <code>gs://whatsapp-sales-agent-hecate-artifacts/runs/</code>{" "}
          under their run ids. The join output is{" "}
          <code>runs/exp-07_check1_split-tenacityval_seed-0/check1.json</code>{" "}
          and <code>check1_stdout.txt</code> in that bucket. Run-3’s{" "}
          <code>CODE_SHA</code> was written after the pass, once{" "}
          <code>93678ef</code> existed. The efficiency prompt (14/49, 26.6
          steps) is a fourth arm and is not in this gate. After the join,{" "}
          <code>gpu-advisor</code> and <code>hecate-worker</code> were stopped.
          Spec and results: <code>experiments/e07-route-then-advise/</code>.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
