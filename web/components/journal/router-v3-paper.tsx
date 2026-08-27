import { RouterV3Figures } from "@/components/experiments/router-v3-figures";
import {
  PaperAbstract,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { RouterArchitectureV3 } from "@/components/paper/router-architecture";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V3 as R } from "@/lib/experiments/router-v3";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = "2026-08-26-v3-trajectory-router-spec";

const toc: PaperTocItem[] = [
  { href: "#context", label: "Context" },
  {
    href: "#method",
    label: "Method",
    children: [{ href: "#fig-arch", label: "Architecture" }],
  },
  {
    href: "#result",
    label: "Result",
    children: [
      { href: "#k0", label: "K=0" },
      { href: "#k3", label: "K=3" },
      { href: "#figures", label: "Figures" },
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
  const k0 = R.k0.routeAuc.toFixed(3);
  const k3 = R.k3.routeAuc.toFixed(3);

  return (
    <PaperShell
      title="K-turn trajectory router v3 (LoRA value head)"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations={`SWE-bench Verified (${R.n}) · closed — K=3 missed the K=0 gate`}
      date="August 27, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-27"
      tags="router · trajectory-conditioning · lora · k-turn · missed-target"
      toc={toc}
      glossary={glossaryEntries(
        "Route-AUC",
        "AUROC",
        "LoRA",
        "value head",
        "Brier",
        "K-turn",
        "QLoRA"
      )}
    >
      <PaperAbstract>
        <p>
          v1 frozen issue text and v2 oracle AST fusion are both chance on
          django holdout (n={R.djangoN}): Route-AUC{" "}
          {R.v1v2.djangoRouteAuc.text} / {R.v1v2.djangoRouteAuc.fusion}. Static
          pre-execution signal is closed. The remaining candidate was what the
          cheap model discovers in its first few turns.
        </p>
        <p>
          K=0 — a 7B LoRA value head on issue text only — scores django
          Route-AUC {k0} (one seed). Packed K=3, same architecture, scores{" "}
          {k3}. H1 is rejected: extra turns lost to the trajectory-blind
          control (Δ = {(R.k3.routeAuc - R.k0.routeAuc).toFixed(3)}). The old
          stretch bar of {R.stretch.djangoRouteAuc.toFixed(2)} would have been
          a trap — K=3 clears it and still fails the real gate. AUROC barely
          moves; calibration gets worse. One seed, no CI. Do not scale this
          smoke to 5-fold.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          Related:{" "}
          <a href={R.related[0]}>text-only v1</a>
          {" · "}
          <a href={R.related[1]}>oracle fusion v2</a>
          . Both failed the django ship bar. SWE-Router argues that the missing
          signal is in the partial trajectory, not the prompt.<PaperCite n={4} />
          This experiment tests that claim on the same Qwen3-Coder-480B vs
          Claude 4 Opus pair.
        </p>
        <p>
          Question: does a LoRA value head reading K=3 turns of Qwen’s own
          mini-SWE-agent trace improve django-holdout Route-AUC over a matched
          K=0 LoRA that sees only issue text? The control is a separately
          trained 7B LoRA, not frozen ModernBERT.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <RouterArchitectureV3 />
        <p>
          Weak/strong pair unchanged: Qwen3-Coder-480B vs Claude 4 Opus,
          mini-SWE-agent v1.0.0, same 500 labels.<PaperCite n={[1, 2, 3]} />{" "}
          Value head: Qwen2.5-Coder-7B-Instruct, LoRA r=32 α=64, last-token
          logits scoring P(Qwen resolves), 8192 context, QLoRA (4-bit LoRA) on
          one L4. A turn is a user/observation boundary. Packing is only inside
          the K=3 arm. {R.paperDeviation} Trained on{" "}
          <code>{R.gpu.instance}</code>, not the execution box.
        </p>
        <p>
          Primary split is still leave-django-out. Route-AUC is the only gate;
          AUROC, accuracy, and Brier are diagnostic. This write-up is the
          one-seed django smoke, not a 5-fold claim.
        </p>
        <p>
          H1: packed K=3 django Route-AUC is clearly above the matched K=0 LoRA
          on the same split. The bar is {k0}. H2 (stretch, written before K=0
          was measured): K=3 ≥ {R.stretch.djangoRouteAuc.toFixed(2)}. H2 can
          pass while H1 fails.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <p>Django holdout (n={R.djangoN}), one seed each, no CI:</p>
        <PaperTable
          id="tab-v3-gate"
          caption="Table 1: Leave-django-out smoke. Highlighted row is the gate. K=0 and K=3 are one seed; v1/v2 are 3-seed means."
          highlight={(row) => row[0].includes("Route-AUC")}
          headers={[
            "Metric",
            "v1 text",
            "v2 fusion",
            "K=0 LoRA",
            "K=3 LoRA",
          ]}
          rows={[
            [
              "Django Route-AUC",
              R.v1v2.djangoRouteAuc.text,
              R.v1v2.djangoRouteAuc.fusion,
              k0,
              k3,
            ],
            [
              "Django AUROC",
              R.v1v2.djangoAuroc.text,
              R.v1v2.djangoAuroc.fusion,
              R.k0.auroc.toFixed(3),
              R.k3.auroc.toFixed(3),
            ],
            [
              "Django accuracy",
              R.v1v2.djangoAcc.text,
              R.v1v2.djangoAcc.fusion,
              R.k0.accuracy.toFixed(3),
              R.k3.accuracy.toFixed(3),
            ],
            [
              "Django Brier",
              R.v1v2.djangoBrier.text,
              R.v1v2.djangoBrier.fusion,
              R.k0.brier.toFixed(3),
              R.k3.brier.toFixed(3),
            ],
          ]}
        />

        <PaperSubsection id="k0" number="3.1" title="K=0 (issue text, 7B LoRA)">
          <p>
            Route-AUC jumped over the frozen floor; AUROC barely moved (
            {R.k0.auroc.toFixed(3)}); accuracy ({R.k0.accuracy.toFixed(2)}) sits
            below always-Qwen ({(R.djangoAlwaysSmall * 100).toFixed(1)}%); Brier
            got worse ({R.k0.brier.toFixed(3)} vs 0.250). That combination can
            be internally consistent: Route-AUC cares about ordering the
            extremes, while AUROC averages every pair. It is also the
            fingerprint of a statistic that can swing between seeds on a
            231-task holdout. Treat {k0} as a control value for this smoke, not
            a settled number.
          </p>
        </PaperSubsection>

        <PaperSubsection id="k3" number="3.2" title="K=3 (packed trajectory)">
          <p>
            Packed K=3 uses the same architecture on the first three
            user/observation turns. Truncation at 8192 tokens is{" "}
            {(R.traces.k3TruncationRate * 100).toFixed(1)}% ({R.traces.k3TruncatedN}{" "}
            of 500) — not a plausible confound. Django Route-AUC is {k3} versus
            K=0’s {k0}. H1 rejected. H2’s stretch bar of{" "}
            {R.stretch.djangoRouteAuc.toFixed(2)} is cleared and is not
            confirmatory — that is the outcome this protocol said to report as
            an H1 failure. AUROC {R.k3.auroc.toFixed(3)} is a tick above K=0;
            Brier {R.k3.brier.toFixed(3)} is worse than either prior arm. At the
            selected λ the routed resolved rate matches always-Opus (
            {(R.k3.bestRouteRate * 100).toFixed(1)}%), so the head is not
            finding cheap wins above the expensive default.
          </p>
        </PaperSubsection>

        <PaperSubsection id="figures" number="3.3" title="Figures">
          <RouterV3Figures />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          RQ1: no. On this pair, three turns of Qwen’s own trace do not improve
          django-holdout routing over a LoRA that sees only the issue. The
          drop vs K=0 is large enough that a 5-fold × 3-seed protocol is not
          justified. Extra turns also failed in SWE-Router when the test repo
          was held out, and helped only when train and test shared the same
          mix.<PaperCite n={4} /> Django holdout is the second kind of test.
        </p>
        <p>
          K=0 still sits well above the frozen v1/v2 floor on Route-AUC. That
          is a different claim — “a 7B LoRA on issue text ranks better than
          frozen ModernBERT” — and it is still one seed. It is not evidence
          that trajectory conditioning works.
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Do not run 5-fold × 3-seed or the{" "}
            <code>{R.secondHoldout}</code> holdout on this K=3 recipe. The
            smoke already failed the gate.
          </li>
          <li>
            <code>{R.gpu.instance}</code> is stopped. Leave it stopped unless a
            new hypothesis needs GPU time.
          </li>
          <li>
            If anything is next, it is diagnosing K=0’s {k0} across seeds — not
            packing more turns on a recipe that lost to that control.
          </li>
        </ol>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <ul className="list-disc space-y-2 pl-6">
          <li>
            Both arms are one seed. No std is reported because none exists
            yet. The gate was “clearly above K=0,” and {k3} vs {k0} is not a
            close call.
          </li>
          <li>
            Endpoints on django are the same labels-only trio as v1/v2:
            always-Opus {(R.k0.alwaysLarge * 100).toFixed(1)}%, always-Qwen{" "}
            {(R.k0.alwaysSmall * 100).toFixed(1)}%, oracle{" "}
            {(R.k0.oracle * 100).toFixed(1)}%.
          </li>
          <li>
            SWE-Router mix-1 and SWE-Smith tables in Figure 3 are calibration
            from related work, not expected transfer numbers for this pair.
          </li>
        </ul>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
