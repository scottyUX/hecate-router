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

const SLUG = "2026-11-11-e11-ppo-vs-grpo-advisor-plan";

const toc: PaperTocItem[] = [
  { href: "#question", label: "Question" },
  { href: "#known", label: "What Experiment 7 showed" },
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
] as const;

export async function E11PpoVsGrpoAdvisorPlanPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 11: PPO vs GRPO for the advisor, with LoRA"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · Flash-Lite student · Qwen2.5-7B advisor, LoRA · DGX Spark · plan · 11 November 2026"
      date="November 11, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Software Engineering (cs.SE)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-11-11"
      tags="e11 · advisor models · ppo · grpo · reinforcement learning · lora · dgx spark · plan"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Experiment 7 trained a Qwen2.5-7B advisor with GRPO, following
          Advisor Models <PaperCite n={1} />, to advise Gemini 2.5 Flash-Lite
          on SWE-smith Tenacity. GRPO <PaperCite n={3} /> drops PPO’s learned
          critic <PaperCite n={2} /> and scores each run against the average
          of 8 runs on the same issue. The advisor recovered most of what
          untrained advice lost, but did not beat Flash-Lite alone{" "}
          <PaperCite n={4} />.
        </p>
        <p>
          Experiment 11 retrains that advisor twice on the lab’s DGX Spark,
          once with GRPO and once with PPO, both with LoRA, and keeps
          everything else from Experiment 7’s recipe. This entry records the
          plan before any run: about $1,500–1,750, almost all of it student
          API calls, and 3–4 weeks.
        </p>
      </PaperAbstract>

      <PaperSection id="question" number="1" title="Question">
        <PaperTable
          id="table-questions"
          caption="Table 1. Pre-registered questions, with the predictions recorded before any run."
          headers={["ID", "Question", "Prediction"]}
          rows={[
            ["Q11.1", "With LoRA, does the PPO advisor beat the GRPO advisor on resolve or steps on the 49 test issues?", "No detectable difference"],
            ["Q11.2", "Does either LoRA advisor beat Flash-Lite alone?", "No"],
            ["Q11.3", "Does LoRA GRPO land where Experiment 7’s full fine-tune did (31.9% resolved, no step cut)?", "Yes, within ±10 points"],
            ["Q11.4", "Training: reward, KL, share of zero-signal groups, critic quality, time and memory per step.", "PPO has fewer zero-signal updates and costs more per step"],
          ]}
        />
        <PaperCallout label="Why PPO might help here">
          <p>
            Flash-Lite resolves about a third of the training issues, so many
            groups of 8 runs contain no resolved run. In GRPO such a group has
            zero spread and gives no learning signal. PPO’s critic predicts
            the final reward from the conversation so far, so each turn of
            advice gets its own score, even in a group where every run
            failed. Whether that turns into a better advisor is the question.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="known" number="2" title="What Experiment 7 showed">
        <PaperTable
          id="table-e07"
          caption="Table 2. Experiment 7, Flash-Lite student, 49 Tenacity test issues, three passes per arm."
          headers={["Arm", "Resolve", "Mean steps", "Steps on resolved"]}
          rows={[
            ["Flash-Lite alone", "34.0%", "25.7", "19.9"],
            ["+ untrained Qwen2.5-7B", "13.5%", "22.0", "16.8"],
            ["+ GRPO advisor, full fine-tune, step 295", "31.9%", "26.3", "16.7"],
            ["+ GRPO advisor, epoch 10", "27.7%", "26.4", "15.4"],
          ]}
          highlight={(row) => row[0].startsWith("+ GRPO advisor, full")}
        />
        <p>
          The trained advisor against Flash-Lite alone: resolve −2.1 points
          [−11.3, +7.1], steps +0.6 [−2.3, +3.6]. Experiment 7’s GRPO was a
          full fine-tune on four A100s. A full fine-tune with a critic does
          not fit on one Spark, so Experiment 11 uses LoRA for both arms and
          checks, through Q11.3, whether LoRA alone changes the GRPO result.
        </p>
      </PaperSection>

      <PaperSection id="design" number="3" title="Design">
        <PaperTable
          id="table-arms"
          caption="Table 3. Arms. Shared: Qwen2.5-7B-Instruct, LoRA rank 32 on all linear layers, LR 1e-5, Flash-Lite student, the 56 training issues, batch 4 issues × 8 rollouts, KL 0.001, 9 advice turns, 295 steps, Experiment 7’s reward, one seed."
          headers={["Arm", "Advantage", "Extra model"]}
          rows={[
            ["G: GRPO", "Run reward minus its group’s mean, divided by the group’s spread; the same value on every advice token of the run", "None"],
            ["P: PPO", "Final reward minus a critic’s estimate at each advice turn (γ = 1, λ = 1)", "A second Qwen2.5-7B with its own LoRA and a value head"],
          ]}
        />
        <p>
          Both arms draw the same 32 student runs per training step, so they
          cost the same in API calls and see the same amount of data. Only
          the advantage, and PPO’s critic, differ.
        </p>
        <p>
          <strong>Evaluation.</strong> Each arm’s step-295 checkpoint, three
          passes on the 49 test issues, with Experiment 7’s short-context
          eval and sampling. Flash-Lite alone reuses Experiment 7’s three
          passes. Comparisons use paired bootstrap intervals over issues.
        </p>
        <p>
          <strong>Infrastructure.</strong> Training and the vLLM advisor run
          on the Spark. The SWE-smith containers, agent server and eval
          server stay on the x86 worker, reached over an SSH tunnel.
        </p>
      </PaperSection>

      <PaperSection id="rules" number="4" title="Decision rules">
        <PaperTable
          id="table-rules"
          caption="Table 4. Fixed before any Experiment 11 run, using Experiment 7’s reading rule for a difference X − Y."
          headers={["Outcome", "Rule"]}
          rows={[
            ["X raises resolve", "Resolve 95% lower bound > 0"],
            ["X keeps resolve and cuts steps", "Steps 95% upper bound < 0 and resolve 95% lower bound > −10 points"],
            ["Otherwise", "“No detectable difference at n = 49, one training seed”"],
            ["Q11.1", "PPO − GRPO, either reading, in either direction"],
            ["Q11.2", "Each arm − Flash-Lite alone"],
            ["Q11.3", "LoRA GRPO within ±10 points of 31.9% with no step cut; if not, any PPO − GRPO result is read as a LoRA result only"],
            ["Next step", "A full-fine-tune PPO run gets its own spec only if PPO trains a better advisor"],
          ]}
        />
      </PaperSection>

      <PaperSection id="budget" number="5" title="Budget and time">
        <PaperTable
          id="table-budget"
          caption="Table 5. Estimated cost. Student calls dominate: 32 Flash-Lite runs per step at about $0.062 each, for 295 steps per arm."
          headers={["Item", "GRPO", "PPO"]}
          rows={[
            ["Student API, training", "~$585", "~$585"],
            ["Student API, eval and smokes", "~$25", "~$25"],
            ["x86 worker", "~$110–230", "~$140–290"],
            ["Spark GPU", "$0", "$0"],
            ["Per arm", "~$720–840", "~$750–900"],
            ["Total", "~$1,470–1,740", ""],
          ]}
          highlight={(row) => row[0] === "Total"}
        />
        <p>
          Caps: $900 per arm and $1,800 in total. The OpenRouter key’s limit
          has to be raised before the timing smoke. Step time on the Spark is
          unknown until that smoke; assuming 10–20 minutes per step, training
          takes 2–4 days for GRPO and 3–6 for PPO. With setup, evaluation and
          write-up, about 3–4 weeks from approval.
        </p>
      </PaperSection>

      <PaperSection id="risks" number="6" title="Risks and scope">
        <p>
          One training seed per arm and 49 test issues, with passes that vary
          by up to 19 points: “no detectable difference” is the most likely
          outcome, and the training curves are the lower-noise result.
          SkyRL’s LoRA path and PPO critic are unverified on the Spark’s ARM
          CPU, and there is no PPO fallback outside SkyRL. If PPO’s critic
          does not fit beside the policy and vLLM, a 1.5B critic is the
          recorded fallback. OpenRouter has intermittently refused{" "}
          <code>gemini-2.5-flash-lite</code> since late October; if the model
          becomes unavailable, the experiment pauses.
        </p>
        <p>
          Out of scope: the M1/M2 router (Experiment 10), other students,
          repos or harnesses, and full fine-tuning.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="7" title="Notes">
        <p>
          Spec: <code>experiments/e11-ppo-vs-grpo-advisor/spec.md</code>,
          including a constitution check. This plan was first written as
          Experiment 10 and moved here on 11 November, when Experiment 10
          became the router study; it starts after Experiment 10.
          Nothing is authorized to run until review. Gates before any full
          run: the Spark stack and memory (G0), a 3-step timing and cost
          smoke (G1), offline tests (G2), and the artifact copy off the
          Spark (G3). The GRPO arm is the same run as the “Does advice
          transfer?” proposal’s Phase C bridge, and is run only once.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
