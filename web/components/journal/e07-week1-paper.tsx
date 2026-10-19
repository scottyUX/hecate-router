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

const SLUG = "2026-10-19-e07-week1-student-baselines";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  { href: "#method", label: "Method" },
  {
    href: "#result",
    label: "Result",
    children: [
      { href: "#tab-49", label: "49 test issues" },
      { href: "#tab-56", label: "56 training issues" },
      { href: "#tab-efficiency", label: "Efficiency prompt" },
      { href: "#tab-split", label: "Which issues moved" },
      { href: "#tab-paper", label: "Paper rows" },
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
    href: "https://arxiv.org/abs/2510.02453",
    text: "Asawa, P., Zhu, A., O’Neill, A., Zaharia, M., Dimakis, A. G., and Gonzalez, J. E. (2026). How to Train Your Advisor: Steering Black-Box LLMs with Advisor Models. arXiv:2510.02453.",
  },
  {
    id: 2,
    href: "https://github.com/SWE-agent/mini-swe-agent",
    text: "Yang, J. et al. (2025). mini-SWE-agent. Princeton NLP / SWE-agent.",
  },
] as const;

export async function E07Week1Paper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 7: Flash-Lite baselines and an efficiency prompt"
      authors={
        <>
          Scott Davis · <a href="/">Hecate Lab</a>
        </>
      }
      affiliations="SWE-smith Tenacity · Advisor Models, advice only · week of 18–19 October 2026"
      date="October 19, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-10-19"
      tags="e7 · swe-smith · tenacity · flash-lite · efficiency prompt · advisor"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Phase 0 of Experiment 7 follows Asawa et al. on SWE-smith Tenacity
          <PaperCite n={1} />. A frozen mini-SWE-agent student is steered, later,
          by a Qwen2.5-7B-Instruct advisor trained with GRPO. This note records
          the week before that training: a trusted score, the student-only
          passes, and Monday’s efficiency sentence.
        </p>
        <p>
          The training student is Gemini 2.5 Flash-Lite. Alone on the 49 test
          issues it solved 22/49 (44.9%) in 23.8 mean steps. The same student
          with one added sentence, “use fewer steps,” solved 14/49 (28.6%) in
          26.6 mean steps. On the issues that sentence still solved, steps fell
          to 16.5 from 21.1. A one-pass Flash check on the same 49, 31/49
          (63.3%) and 19.4 steps, sits next to the paper’s Flash average of
          61.2% and 19.1. The 56-issue training probe passed at 17/56. The
          advisor has not been run.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          The paper’s Figure 3 is four rows on 49 held-out Tenacity issues, with
          Gemini 2.5 Flash as the student. Student alone resolves 61.2% in 19.1
          steps. An efficiency sentence in the prompt reaches 65.7% and 18.2
          steps. An untrained 7B advisor drops steps to 13.7 and resolve to
          52.6%. After GRPO the advisor holds 14.4 steps and returns resolve to
          61.2%. Those percentages are a repeated-run average. The model is not
          trained on the 49.
        </p>
        <p>
          The other Tenacity issues are the training pool. Any training issue
          the student failed on all five tries is dropped, which leaves 56. A
          score on the 56 cannot be set next to 61.2%. Our student is Flash-Lite,
          not Flash, so our rows will not match those percentages. The comparison
          that matters is against our own Flash-Lite-alone pass. The Flash pass
          is only a check that the harness is in range of the paper.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <p>
          The student is <code>openrouter/google/gemini-2.5-flash-lite</code>{" "}
          except for the one Flash harness check. Calls go through OpenRouter
          with a price file so LiteLLM can bill the model id. The worker runs
          mini-SWE-agent on port 8081 and SWE-bench in Docker on port 8082
          <PaperCite n={2} />. The advisor machine, two A100-80GB GPUs with
          SkyRL and Qwen2.5-7B-Instruct, is installed and stopped. No advice was
          sent this week.
        </p>
        <p>
          Early smokes were not trusted. LiteLLM had no price for the OpenRouter
          id, and the eval server called itself instead of Docker. One of those
          runs finished in 7 steps with an untrusted resolve flag. Commit{" "}
          <code>3ada694</code> makes the eval server score in Docker, keeps a
          remote path for the GPU trainer, and treats a session with no
          successful model call as an error rather than an unsolved issue. After
          that fix, <code>jd__tenacity.0d40e76f.pr_425</code> resolved in 15
          steps on one Docker evaluation. A later full pass that returned mostly
          session errors is excluded. The numbers below are one issue at a time,
          one pass, on the full file. <code>--num_samples</code> was not used.
        </p>
        <p>
          Monday’s row adds one fixed sentence after the rendered task message.
          The shared mini-SWE template was not edited, so training and the
          untrained-advisor run stay on the normal instructions. The sentence is
          ours. The paper says it told the student to be more efficient and does
          not print the wording. Ours was: work in as few steps as possible; once
          the original issue is fixed and a minimal check passes, submit; do not
          add tests, refactors, or extra exploration unless they unblock that
          fix. The step cap on a run is 40.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <PaperSubsection id="tab-49" number="3.1" title="Student alone, 49 test issues">
          <p>
            The paper’s 61.2% and 19.1 steps are an average of several Flash
            runs. Each of our rows is one pass. On 49 issues, one issue is about
            two points.
          </p>
          <PaperTable
            id="table-49"
            caption="Table 1. Student working alone on the 49 test issues. Flash is the paper’s student and our harness check. Flash-Lite is the student GRPO will steer."
            headers={["Who", "Resolved", "Rate", "Mean steps", "Errors", "Cost"]}
            rows={[
              ["Paper, Flash, repeated-run average", "—", "61.2%", "19.1", "—", "—"],
              ["Us, Flash, one pass", "31/49", "63.3%", "19.4", "0", "$3.76"],
              ["Us, Flash-Lite, one pass", "22/49", "44.9%", "23.8", "0", "$2.97"],
            ]}
            highlight={(row) => row[0].includes("Flash-Lite")}
          />
          <p>
            Flash on one pass is within about two points and 0.3 steps of the
            paper’s average. The harness is in range. One pass is not the
            paper’s distribution. Flash-Lite solves fewer issues and takes more
            steps. Solved Flash-Lite issues took 21.1 steps on average.
          </p>
        </PaperSubsection>

        <PaperSubsection id="tab-56" number="3.2" title="Flash-Lite on the 56 training issues">
          <PaperTable
            id="table-56"
            caption="Table 2. Training set, Flash-Lite only. This is not Figure 3. The floor was 9 of 56 resolved and almost no session errors."
            headers={["Run", "Resolved", "Rate", "Mean steps", "Solved steps", "Errors", "Gate"]}
            rows={[
              ["Flash-Lite, 56 training issues", "17/56", "30.4%", "20.7", "14.1", "1", "Pass"],
            ]}
          />
          <p>
            The probe stands. It does not need to be repeated before GRPO. Flash
            has not been run on these 56, and it will not be. The training
            student is Flash-Lite.
          </p>
        </PaperSubsection>

        <PaperSubsection
          id="tab-efficiency"
          number="3.3"
          title="Efficiency sentence, Flash-Lite, same 49"
        >
          <p>
            Same model, same 49 issues, same one-at-a-time harness. The only
            change is the sentence. Paired on all 49, the sentence resolved 8
            fewer issues and used 2.8 more steps on average. The step gap’s 95%
            interval is −1.8 to +7.4 and includes zero. The resolve gap does
            not: plain prompt minus efficiency sentence is +16.3 points, with
            interval +4.1 to +28.6.
          </p>
          <PaperTable
            id="table-efficiency"
            caption="Table 3. Flash-Lite on the 49 test issues, with and without the efficiency sentence. Both runs had 0 errors."
            headers={["Arm", "Resolved", "Rate", "Mean steps", "Steps on solved", "Cost"]}
            rows={[
              ["No extra sentence (run-5)", "22/49", "44.9%", "23.8", "21.1", "$2.97"],
              ["Efficiency sentence", "14/49", "28.6%", "26.6", "16.5", "$3.41"],
            ]}
            highlight={(row) => row[0].startsWith("Efficiency")}
          />
        </PaperSubsection>

        <PaperSubsection id="tab-split" number="3.4" title="Which issues moved">
          <PaperTable
            id="table-split"
            caption="Table 4. Paired outcomes on the 49. The 16.5-step average is only the 14 issues the sentence solved. It leaves out the 10 the sentence lost."
            headers={["Outcome", "Issues"]}
            rows={[
              ["Solved in both passes", "12"],
              ["Solved only with no extra sentence", "10"],
              ["Of those, hit the 40-step cap once the sentence was added", "8"],
              ["Solved only with the efficiency sentence", "2"],
              ["Unsolved in both", "25"],
            ]}
          />
          <p>
            The two step averages are different sets. 16.5 is the 14 the
            sentence solved. 21.1 is the 22 the plain prompt solved. The long
            failures, including eight that ran to the cap, are what pull the
            overall mean from 23.8 up to 26.6.
          </p>
        </PaperSubsection>

        <PaperSubsection id="tab-paper" number="3.5" title="Where this sits against Figure 3">
          <PaperTable
            id="table-paper"
            caption="Table 5. The paper’s four rows use Flash. Our measured rows use Flash-Lite, except the Flash harness check. Paper resolve and steps are the published averages."
            headers={["Row", "What it is", "Paper", "Us", "Status"]}
            rows={[
              [
                "Student only",
                "No advisor",
                "61.2%, 19.1 steps",
                "Flash-Lite 22/49, 23.8 steps",
                "Done",
              ],
              [
                "Efficiency prompt",
                "A sentence, still no advisor",
                "65.7%, 18.2 steps",
                "Flash-Lite 14/49, 26.6 steps",
                "Done",
              ],
              [
                "Untrained advisor",
                "7B advice every 5 steps, before GRPO",
                "52.6%, 13.7 steps",
                "—",
                "Tuesday",
              ],
              [
                "Trained advisor",
                "Same 7B after GRPO",
                "61.2%, 14.4 steps",
                "—",
                "Thursday",
              ],
            ]}
          />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          The harness can host the paper’s student. One Flash pass landed within
          two points and a third of a step of Figure 3’s student-only average.
          That does not make Flash the student we train. Flash-Lite is weaker,
          which is the expected price of the cheaper student, and the 56-issue
          probe already clears the floor of 9/56.
        </p>
        <p>
          The efficiency sentence is not a substitute for the advisor. It solved
          fewer issues, and the overall step count did not fall. The resolve gap
          is large enough that its interval stays above zero. The step increase
          is not: that interval includes zero. What the sentence did do is
          shorten the runs it still solved, from 21.1 steps to 16.5, while
          pushing eight previously solved issues into the 40-step cap.
        </p>
        <p>
          This is our sentence on Flash-Lite, one pass. It is the same kind of
          row as the paper’s efficiency cell. It is not a reproduction of 65.7%
          and 18.2 steps. Tuesday’s gate stays against Flash-Lite alone, 22/49
          and 23.8 steps. Comparing the untrained advisor with 14/49 and 26.6
          would make that advisor look better than the locked rule allows.
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <p>
          Tuesday, run the untrained advisor on the same 49. Qwen2.5-7B-Instruct
          comments every 5 student steps, before any GRPO. Train on Wednesday
          only if those mean steps are at least 2 below 23.8. If the steps drop
          by at least 2 but resolve does not fall, still train, and record that
          there was no trade-off to recover. If the step gap is under 2, stop.
        </p>
        <p>
          Wednesday is GRPO on the 56, Flash-Lite as the student, 18 epochs,
          batch 4, on the 2×A100 machine. Resize the worker to n2-standard-32
          before that training, not before Tuesday’s one-at-a-time eval.
          Thursday, score the trained advisor on the 49.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <p>
          Run ids for the trusted passes: Flash-Lite on the 49 is{" "}
          <code>exp-07_arm-weakalone_split-tenacityval_seed-0_run-5</code>.
          Flash-Lite on the 56 is{" "}
          <code>exp-07_arm-weakalone_split-tenacitytrain_seed-0_run-10</code>.
          Flash on the 49 is{" "}
          <code>exp-07_arm-weakalone_split-tenacityval_seed-0_run-2</code>.
          Copies are under{" "}
          <code>gs://hecate-506120-artifacts/runs/</code>. The Monday efficiency
          mapping is the new file paired to run-5. It does not replace run-5.
        </p>
        <p>
          Earlier ids on these splits, including the 49-issue pass that returned
          49 errors at zero cost and the 56-issue pass that died in session
          errors, are not baselines. The worker is <code>hecate-worker</code>.
          Scoring code is <code>advisor-models</code> at <code>3ada694</code> on{" "}
          <code>scott/train-2xa100</code>, plus the efficiency-sentence change
          on that branch. <code>advisor-models-main</code> is not the checkout
          that ran.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
