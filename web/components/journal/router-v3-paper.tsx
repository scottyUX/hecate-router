import {
  PaperAbstract,
  PaperCallout,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  PaperToc,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V3 as R } from "@/lib/experiments/router-v3";

const SLUG = "2026-08-26-v3-trajectory-router-spec";

const toc: PaperTocItem[] = [
  { href: "#introduction", label: "Introduction" },
  { href: "#rq", label: "Research question" },
  { href: "#hypothesis", label: "Hypothesis" },
  { href: "#setup", label: "Setup" },
  {
    href: "#results",
    label: "Results",
    children: [
      { href: "#prior", label: "Prior numbers" },
      { href: "#status", label: "Current status" },
    ],
  },
  { href: "#next", label: "Next" },
  { href: "#references", label: "References" },
];

const references = [
  {
    id: 1,
    href: "https://arxiv.org/abs/2310.06770",
    text: "Jimenez, C. E. et al. (2024). SWE-bench: Can Language Models Resolve Real-World GitHub Issues? ICLR. arXiv:2310.06770.",
  },
  {
    id: 2,
    href: "https://openai.com/index/introducing-swe-bench-verified/",
    text: "Chowdhury, N. et al. (2024). Introducing SWE-bench Verified. OpenAI.",
  },
  {
    id: 3,
    href: "https://github.com/SWE-agent/mini-swe-agent",
    text: "Yang, J. et al. (2025). mini-SWE-agent. Princeton NLP / SWE-agent.",
  },
  {
    id: 4,
    href: "https://arxiv.org/abs/2607.00053",
    text: "Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., and Bogunovic, I. (2026). SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks. arXiv:2607.00053.",
  },
] as const;

export async function RouterV3Paper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="K-turn trajectory-conditioned router (LoRA value head)"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations={`SWE-bench Verified (${R.n}) · rev ${R.rev} · PENDING`}
      date="August 26, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-26"
      tags="router · trajectory-conditioning · lora · k-turn · spec"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          v1 frozen issue text and v2 oracle AST fusion are chance on django
          holdout (n={R.djangoN}): Route-AUC {R.v1v2.djangoRouteAuc.text} /{" "}
          {R.v1v2.djangoRouteAuc.fusion}. Static pre-execution signal is
          closed. The remaining candidate is what the cheap model discovers in
          its first few turns.
        </p>
        <p>
          <strong>Research question.</strong> Do the first K=3 turns of
          Qwen3-Coder’s own mini-SWE-agent trace rank “will Qwen resolve this
          task” better than issue text alone on the same django holdout?
        </p>
        <p>
          <strong>Hypothesis.</strong> A separately trained 7B LoRA value head
          on packed K∈{"{0..4}"} traces, evaluated at K=3, beats a K=0 LoRA
          trained only on issue text. Stretch is django Route-AUC ≥{" "}
          {R.stretch.djangoRouteAuc.toFixed(2)}. SWE-Router’s 0.694 is mix-1,
          not a repo holdout, and is not the expected transfer
          number.<PaperCite n={4} />
        </p>
        <p>
          <strong>Result.</strong> Not yet run. Traces recovered 500/500 from
          Hugging Face; K=3 truncation at 8192 is{" "}
          {(R.traces.k3TruncationRate * 100).toFixed(1)}%. GPU smoke is blocked:{" "}
          {R.gpu.reason} H1/H2 stay untested until that gate passes. No empty
          charts.
        </p>
      </PaperAbstract>

      <PaperToc items={toc} />

      <PaperSection id="introduction" number="1" title="Introduction">
        <p>
          Related:{" "}
          <a href={R.related[0]}>text-only v1</a>
          {" · "}
          <a href={R.related[1]}>oracle fusion v2</a>
          . Both failed the django ship bar. SWE-Router argues that the missing
          signal is in the partial trajectory, not the prompt.<PaperCite n={4} />
        </p>
      </PaperSection>

      <PaperSection id="rq" number="2" title="Research question">
        <PaperCallout label="RQ1">
          <p>
            On the same 500-task Qwen3-Coder vs Claude 4 Opus pair, does a LoRA
            value head reading K=3 turns of Qwen’s own mini-SWE-agent trace
            improve django-holdout Route-AUC over a K=0 LoRA that sees only
            issue text?
          </p>
        </PaperCallout>
        <p>
          The control is a separately trained 7B LoRA on issue text, not frozen
          ModernBERT. Route-AUC is the only gate; AUROC is diagnostic. Grouped
          5-fold is reported after a django smoke, not instead of it.
        </p>
      </PaperSection>

      <PaperSection id="hypothesis" number="3" title="Hypothesis">
        <PaperCallout label="H1 — trajectory lift">
          <p>
            Packed K=3 django Route-AUC is clearly above the matched K=0 LoRA
            on the same split. A null of “grouped looks alive, django still
            chance” would replicate SWE-Router’s repository-shift finding, not
            bury a failure.<PaperCite n={4} />
          </p>
        </PaperCallout>
        <PaperCallout label="H2 — stretch bar">
          <p>
            K=3 django Route-AUC ≥ {R.stretch.djangoRouteAuc.toFixed(2)}. This
            is stretch, not the expected transfer from mix-1 0.694. Rejecting
            H2 while accepting H1 is still a positive result.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="setup" number="4" title="Setup">
        <p>
          Weak/strong pair unchanged: Qwen3-Coder-480B vs Claude 4 Opus,
          mini-SWE-agent v1.0.0, same 500 labels.<PaperCite n={[2, 3]} /> Value
          head: Qwen2.5-Coder-7B-Instruct, LoRA r=32 α=64, last-token logits,
          8192 context, QLoRA on L4. A turn is a user/observation boundary.
          Packing is only inside the K=3 arm. {R.paperDeviation} Do not train
          on <code>hecate-exec</code>.
        </p>
        <p>
          Protocol: recover traces fail-closed 500/500; measure K=3 truncation;
          one leave-django-out seed, K=0 vs packed K=3; stop unless K=3 is
          clearly above K=0; only then 5-fold × 3 seeds plus a second holdout (
          <code>{R.secondHoldout}</code>, n=75).
        </p>
      </PaperSection>

      <PaperSection id="results" number="5" title="Results">
        <PaperCallout label="H1 / H2 untested">
          <p>
            No LoRA fit yet. RQ1 cannot be answered. The tables below are
            priors and gates, not v3 metrics.
          </p>
        </PaperCallout>

        <PaperSubsection id="prior" number="5.1" title="Prior numbers">
          <PaperTable
            id="tab-v3-hypotheses"
            caption="Table 1: Pre-registered claims. Confirmatory split is django holdout. Status is PENDING."
            headers={["Claim", "Test", "Observed", "Decision"]}
            rows={[
              [
                "H1 K=3 beats K=0 LoRA",
                "django Route-AUC, one seed then 5-fold",
                "Smoke not run",
                "Untested",
              ],
              [
                "H2 stretch bar",
                `django Route-AUC ≥ ${R.stretch.djangoRouteAuc.toFixed(2)}`,
                "Smoke not run",
                "Untested",
              ],
              [
                "RQ1 traces beat issue text",
                "H1 accepted",
                "GPU quota blocked",
                "Open",
              ],
            ]}
          />
          <PaperTable
            id="tab-v3-swerouter"
            caption="Table 2: SWE-Router Route-AUC (Son et al., 2026, Table 2). Mix-1 is not a repo holdout."
            headers={["Pair", "Split", "K=0", "K=3"]}
            rows={[
              [
                "gpt-5-mini → gemini-3-pro",
                "SB-V mix-1",
                R.sweRouter.mix1.gpt5miniK0,
                R.sweRouter.mix1.gpt5miniK3,
              ],
              [
                "deepseek-v3.2 → gemini-3-pro",
                "SB-V mix-1",
                R.sweRouter.mix1.deepseekK0,
                R.sweRouter.mix1.deepseekK3,
              ],
              [
                "gpt-5-mini → gemini-3-pro",
                "SWE-Smith repo-disjoint",
                R.sweRouter.smithRepoDisjoint.gpt5miniK0,
                R.sweRouter.smithRepoDisjoint.gpt5miniK3,
              ],
              [
                "deepseek-v3.2 → gemini-3-pro",
                "SWE-Smith repo-disjoint",
                R.sweRouter.smithRepoDisjoint.deepseekK0,
                R.sweRouter.smithRepoDisjoint.deepseekK3,
              ],
            ]}
          />
          <PaperTable
            id="tab-v3-floor"
            caption="Table 3: Hecate v1/v2 floor on this pair. Grouped 5-fold is the django-weighted trap."
            highlight={(row) => row[0].includes("Django")}
            headers={["Metric", "v1 text", "v2 fusion", "Role"]}
            rows={[
              [
                "Django holdout Route-AUC",
                R.v1v2.djangoRouteAuc.text,
                R.v1v2.djangoRouteAuc.fusion,
                `Primary. Stretch ≥ ${R.stretch.djangoRouteAuc.toFixed(2)}`,
              ],
              [
                "Django holdout AUROC",
                R.v1v2.djangoAuroc.text,
                R.v1v2.djangoAuroc.fusion,
                "Diagnostic only — do not gate",
              ],
              [
                "Grouped 5-fold Route-AUC",
                R.v1v2.groupedRouteAuc.text,
                R.v1v2.groupedRouteAuc.fusion,
                "Report, do not headline",
              ],
            ]}
          />
        </PaperSubsection>

        <PaperSubsection id="status" number="5.2" title="Current status">
          <p>
            Step 0 recovered Hugging Face{" "}
            <code>parsaidp/swe-bench-verified-raw-traces-qwen3-coder</code>
            {". "}
            {R.traces.nMatched}/500 instance_id match. Dump has no resolve bits
            (277/500 join is ID-only). K=3 truncation at 8192 is{" "}
            {(R.traces.k3TruncationRate * 100).toFixed(1)}% (
            {R.traces.k3TruncatedN}/500; median{" "}
            {R.traces.medianTokens.toLocaleString()} tokens, max{" "}
            {R.traces.maxTokens.toLocaleString()}).
          </p>
          <p>
            GPU smoke is blocked: {R.gpu.reason} Do not start the full protocol
            until that gate passes. Rewrite this results section in place with
            django K=0 vs K=3 Route-AUC; do not add empty charts before then.
          </p>
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="next" number="6" title="Next">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Raise <code>GPUS_ALL_REGIONS</code> on hecate-506120 (L4 regional
            quota is already 1).
          </li>
          <li>
            <code>scripts/run_traj_smoke.sh</code> on{" "}
            <code>hecate-traj-l4</code>, not <code>hecate-exec</code>.
          </li>
          <li>
            Fill Table 1 with observed K=0 vs K=3 django Route-AUC and accept
            or reject H1/H2.
          </li>
        </ol>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
