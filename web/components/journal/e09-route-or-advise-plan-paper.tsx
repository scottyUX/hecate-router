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

const SLUG = "2026-10-25-e09-route-or-advise-plan";

const toc: PaperTocItem[] = [
  { href: "#question", label: "Question" },
  { href: "#pilot", label: "What the pilot data says" },
  { href: "#design", label: "Design" },
  { href: "#rules", label: "Decision rules" },
  { href: "#budget", label: "Budget and time" },
  { href: "#risks", label: "Risks" },
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
  {
    id: 3,
    href: "/journal/2026-10-24-e08-handoff-modes-plan",
    text: "Davis, S. (2026). Experiment 8: three ways to hand a coding task to a stronger model. Hecate Lab journal, 24 October 2026.",
  },
] as const;

export async function E09RouteOrAdvisePlanPaper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Experiment 9: route or advise"
      authors={
        <>
          Scott Davis · <Link href="/">Hecate Lab</Link>
        </>
      }
      affiliations="SWE-smith Tenacity · 49 test issues · four treatments · plan · 25 October 2026"
      date="October 25, 2026"
      subjects={[
        "Machine Learning (cs.LG)",
        "Software Engineering (cs.SE)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-10-25"
      tags="e9 · routing · advisor models · cost–quality frontier · route-auc · plan"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Routing papers choose a model per task. Advisor papers always advise{" "}
          <PaperCite n={1} />. Experiment 9 asks whether choosing per task among
          four treatments gives a better cost–quality frontier than any single
          one or a fixed mix of them. The four are the cheap student alone, the
          cheap student with Experiment 7’s trained advisor, a mid-price model,
          and a premium model.
        </p>
        <p>
          This entry records the plan before any run. E9 needs no new training:
          it reuses Experiment 7’s student-alone and trained-advisor passes and
          adds two API-only arms, for about $75–200 over about 1.5 weeks.
        </p>
      </PaperAbstract>

      <PaperSection id="question" number="1" title="Question">
        <PaperTable
          id="table-questions"
          caption="Table 1. Pre-registered questions."
          headers={["ID", "Question"]}
          rows={[
            ["Q9.1", "How often is advice enough: issues the advised student resolves that the student alone does not, and the share of the premium model’s extra resolves that advice recovers."],
            ["Q9.2", "Does a router on pre-run features beat the best fixed mix of treatments on Route-AUC?"],
            ["Q9.3", "How much headroom is there: the oracle router (best treatment per issue in hindsight) against the best fixed mix."],
            ["Q9.4", "Is the advisor on the cost–quality frontier at all once a mid-price model is an option?"],
          ]}
        />
        <p>
          E9 is the one-shot router that Experiment 7’s reserved Q7.2 compares
          against (an advisor that learns to escalate mid-run). It does not
          train an escalate action, and it does not move context between models
          the way Experiment 8 does <PaperCite n={3} />.
        </p>
      </PaperSection>

      <PaperSection id="pilot" number="2" title="What the pilot data says">
        <PaperTable
          id="table-pilot"
          caption="Table 2. Per-issue OpenRouter cost on the 49 Tenacity test issues, from Experiment 7 session maps."
          headers={["Arm", "Passes", "Resolved", "$ per issue", "Steps"]}
          rows={[
            ["Gemini 2.5 Flash-Lite alone", "run-6, run-7", "13, 13 / 49", "0.055–0.066", "24.4–27.2"],
            ["Flash-Lite + untrained advisor", "run-3 to run-5", "6–7 / 49", "0.058–0.081", "21.5–24.9"],
            ["Gemini 2.5 Flash alone", "run-2", "31 / 49", "0.077", "19.4"],
          ]}
          highlight={(row) => row[0].startsWith("Gemini 2.5 Flash alone")}
        />
        <PaperCallout label="Why this changes the design">
          <p>
            Flash costs only about 1.4× Flash-Lite per issue, despite higher
            per-token prices, because it takes fewer and shorter steps. It also
            resolves about twice as many issues. With Flash as the only
            stronger option, “always Flash” would win and a router would have
            little to do. So Flash is one of the router’s choices (the
            mid-price model), the strong model is a premium model at least 10×
            Flash-Lite’s per-token price, and the advisor must earn its place
            against Flash, not only against Flash-Lite (Q9.4).
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="design" number="3" title="Design">
        <PaperTable
          id="table-arms"
          caption="Table 3. Treatments (router actions). Same harness for all: mini-SWE-agent, 40-step cap, three separate passes per arm."
          headers={["Action", "Treatment", "Source"]}
          rows={[
            ["A", "Flash-Lite alone", "Reuse E7 student-alone passes"],
            ["B", "Flash-Lite + E7 trained advisor", "Reuse E7’s three final passes"],
            ["C", "Gemini 2.5 Flash alone", "Three new passes (~$12)"],
            ["D", "Premium model alone (default Gemini 2.5 Pro)", "Three new passes; model fixed by amendment before any run"],
          ]}
        />
        <p>
          <strong>Data.</strong> The headline uses the 49 test issues, where
          every arm is out of sample (the advisor trained on the other 56). The
          router is scored with stratified 7-fold cross-validation, repeated
          with 5 fold seeds, fixed in a file before any fit. Results on the 56
          training issues are reported separately and flagged as in-sample for
          the advisor.
        </p>
        <p>
          <strong>Cost.</strong> API cost per issue from the session maps, plus,
          for B, the advisor’s tokens priced at a hosted 7B rate (primary) and
          its measured GPU time (secondary).
        </p>
        <p>
          <strong>Router.</strong> Features available before any agent step:
          a frozen embedding of the problem statement (Hecate’s v1 text
          encoder), its length, counts of code blocks, tracebacks and file
          paths, and the SWE-smith bug type. One logistic regression per action
          predicts the resolve rate. For a price of quality λ, the router picks
          the action with the best expected resolve minus cost/λ; sweeping λ
          traces its curve. Baselines: each single action, the best fixed mix
          (convex hull), the oracle, and a two-action cheap/premium router to
          isolate what advice and the mid-price model add.
        </p>
        <p>
          <strong>Metric.</strong> Route-AUC, the area under the
          resolve-versus-cost curve normalized by the cost range, with a paired
          bootstrap over issues for router minus best fixed mix.
        </p>
      </PaperSection>

      <PaperSection id="rules" number="4" title="Decision rules">
        <PaperTable
          id="table-rules"
          caption="Table 4. Fixed before any E9 run."
          headers={["Outcome", "Rule"]}
          rows={[
            ["Router wins", "Router minus best-fixed-mix Route-AUC > 0 and its 95% lower bound > 0"],
            ["No detectable gain", "Point estimate > 0, lower bound ≤ 0: reported as no detectable gain at n = 49"],
            ["Router loses", "Point estimate ≤ 0"],
            ["Headroom", "Oracle minus best fixed mix, reported whatever the router does; a lower bound ≤ 0 means routing has nothing to gain here"],
            ["Advisor on the frontier", "B is on the frontier unless a mix of A, C and D matches its resolve at no more cost; reported plainly either way"],
            ["E7 outcome", "E9 runs whether or not E7 checks 2 and 3 pass; the E7 verdict is stated next to every number that uses B"],
          ]}
        />
      </PaperSection>

      <PaperSection id="budget" number="5" title="Budget and time">
        <PaperTable
          id="table-budget"
          caption="Table 5. Estimated spend. No GPU is needed: A and B reuse E7 passes, C and D are API models."
          headers={["Item", "Est. cost"]}
          rows={[
            ["C: Flash alone, 3 × 49", "~$12"],
            ["D: premium alone, 3 × 49", "~$45–150"],
            ["A, B: reuse E7", "$0"],
            ["Router fits and bootstrap", "~$0 (laptop)"],
            ["Buffer, ~25%", "~$15–40"],
            ["Total", "~$75–200 (cap $400)"],
          ]}
          highlight={(row) => row[0] === "Total"}
        />
        <p>
          About 1.5 weeks after Experiment 7’s write-up: review 2–3 days, arms C
          and D about 2 days, router and write-up 3–4 days. Arm D stops and
          reports if its first pass costs more than $100.
        </p>
      </PaperSection>

      <PaperSection id="risks" number="6" title="Risks">
        <p>
          Forty-nine issues give wide intervals, so a null result is a
          statement about power, not evidence of no effect. The advisor comes
          from one training seed. Hecate’s v1 frozen-text router was near
          chance on SWE-bench Verified (Route-AUC 0.477); if the router is weak
          here too, the oracle headroom carries the result. A multi-repo
          follow-up, estimated at $2,500–4,600 and 3–4 weeks, would need its own
          spec.
        </p>
      </PaperSection>

      <PaperSection id="notes" number="7" title="Notes">
        <p>
          Spec: <code>experiments/e09-route-or-advise/spec.md</code>, including
          a constitution check. Nothing is authorized to run until review.
          Pilot costs are from the Experiment 7 session maps in{" "}
          <code>gs://whatsapp-sales-agent-hecate-artifacts/runs/</code>, priced
          with the fork’s LiteLLM registry. The student-alone and
          untrained-advisor baselines are from check 1 <PaperCite n={2} />.
        </p>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
