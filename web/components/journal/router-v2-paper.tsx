import { RouterV2Figures, RouterV2RouteAucCurve } from "@/components/experiments/router-v2-figures";
import {
  PaperAbstract,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { RouterArchitectureV2 } from "@/components/paper/router-architecture";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V2 as R } from "@/lib/experiments/router-v2";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = "2026-08-26-oracle-metrics-fusion-v2";

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
      { href: "#fig-route-auc-curve", label: "Route-AUC curve" },
      { href: "#figures", label: "More figures" },
      { href: "#tables", label: "Tables" },
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
    href: "https://arxiv.org/abs/2412.13663",
    text: "Warner, B. et al. (2024). Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient, and Long Context Finetuning and Inference. arXiv:2412.13663.",
  },
  {
    id: 5,
    href: "https://arxiv.org/abs/2406.18665",
    text: "Ong, I. et al. (2024). RouteLLM: Learning to Route LLMs with Preference Data. arXiv:2406.18665.",
  },
  {
    id: 6,
    href: "https://arxiv.org/abs/2607.00053",
    text: "Son, S., Yoon, S., Tang, J., Wang, S., Wolf, L., and Bogunovic, I. (2026). SWE-Router: Routing in Multi-turn Agentic Software Engineering Tasks. arXiv:2607.00053.",
  },
] as const;

export async function RouterV2Paper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Structural fusion v2 (oracle AST + frozen embedding)"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations="SWE-bench Verified (500) · closed — superseded by v3"
      date="August 27, 2026 (curve added retroactively; original run 2026-08-26)"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-27"
      tags="router · structural-fusion · ast · oracle-ceiling · closed"
      toc={toc}
      glossary={glossaryEntries(
        "Route-AUC",
        "AUROC",
        "AST",
        "CLS",
        "MLP",
        "Brier"
      )}
    >
      <PaperAbstract>
        <p>
          v1 showed that a frozen embedding of the GitHub issue alone is chance
          on a held-out repo. Question: if the router is told exactly which
          files the gold patch will touch, and we count structure on those
          files, does that add ranking signal that issue text lacks? This is a
          leaky ceiling — a deployed router would have strictly less
          information — so if this still fails, leak-free structural fusion is
          closed too.
        </p>
        <p>
          Django holdout (n={R.djangoN}): fusion Route-AUC{" "}
          {R.logistic.django.fusion.routeAuc} versus v1 text{" "}
          {R.logistic.django.text.routeAuc}. Metrics-only is{" "}
          {R.logistic.django.metrics.routeAuc}. Structure does not move the
          needle.
        </p>
      </PaperAbstract>

      <PaperSection id="context" number="1" title="Context">
        <p>
          Related:{" "}
          <a href="/journal/2026-08-25-text-only-router-v1">text-only v1</a>
          . Frozen issue text ranked “will Qwen3-Coder resolve this task”
          at chance on django holdout (Route-AUC{" "}
          {R.logistic.django.text.routeAuc}). Prompt-only LLM routers share
          that floor: two issues can read alike and hide a typo versus a
          multi-file refactor.<PaperCite n={[5, 6]} />
        </p>
        <p>
          The remaining pre-execution candidate was static code structure. This
          run answers the strongest version of that question: leak the gold
          patch’s file list, parse those files at <code>base_commit</code>, and
          fuse the counts with the same frozen embedding. If even that ceiling
          is chance, guessing files with BM25 or scanning the whole repo cannot
          do better.
        </p>
      </PaperSection>

      <PaperSection id="method" number="2" title="Method">
        <RouterArchitectureV2 />
        <p>
          Same 500 SWE-bench Verified tasks and matched-scaffold mini-SWE-agent
          v1.0.0 labels (Qwen3-Coder-480B vs Claude 4
          Opus).<PaperCite n={[1, 2, 3]} /> Frozen ModernBERT CLS (768-d)
          concatenated with a 12-d Python AST vector — abstract syntax tree
          counts on gold-patch files: n_files, n_functions, n_imports, loc,
          mean/max cyclomatic, mean/max nesting, mean/max function LOC, mean
          arity, parse_errors.<PaperCite n={4} /> Metrics are scaled on the
          train fold only. Encoder stays frozen. Fail-closed {R.n}/{R.n} cache
          ({R.cacheFiles} oracle files, {R.parseErrors} parse error).
        </p>
        <p>
          Same heads as v1: logistic (headline) and MLP (capacity check). Same
          recipe (4 epochs, batch 8, AdamW, lr 2e-5). Same primary split:
          leave-django-out, train on {R.restN}, evaluate on {R.djangoN}. Grouped
          5-fold is reported, not headlined — v1 already showed that mean is a
          django-weighted trap.
        </p>
        <p>
          Three arms: text-only (v1 floor), fusion (CLS + AST), and
          metrics-only (AST with no text). If fusion does not beat text, and
          metrics-only is itself chance, static structure is closed.
        </p>
      </PaperSection>

      <PaperSection id="result" number="3" title="Result">
        <p>Django holdout (n={R.djangoN}), logistic head:</p>
        <PaperTable
          id="tab-v2-django"
          caption="Table 1: Leave-django-out, logistic, 3 seeds. Confirmatory split."
          headers={["Arm", "Route-AUC", "AUROC", "Accuracy", "Brier"]}
          rows={[
            [
              "v1 text",
              R.logistic.django.text.routeAuc,
              R.logistic.django.text.auroc,
              R.logistic.django.text.acc,
              R.logistic.django.text.brier,
            ],
            [
              "v2 fusion",
              R.logistic.django.fusion.routeAuc,
              R.logistic.django.fusion.auroc,
              R.logistic.django.fusion.acc,
              R.logistic.django.fusion.brier,
            ],
            [
              "v2 metrics-only",
              R.logistic.django.metrics.routeAuc,
              R.logistic.django.metrics.auroc,
              R.logistic.django.metrics.acc,
              R.logistic.django.metrics.brier,
            ],
            [
              "Grouped 5-fold fusion",
              `${R.logistic.grouped.fusion.routeAuc} (not headlined)`,
              R.logistic.grouped.fusion.auroc,
              R.logistic.grouped.fusion.acc,
              R.logistic.grouped.fusion.brier,
            ],
          ]}
        />
        <p>
          Fusion vs text is Δ ≈ +0.005 Route-AUC — inside the ±0.02 band, still
          chance, still under the 0.55 ship bar. Metrics-only is at or below
          chance and worse than text. MLP loses to logistic in every arm
          (fusion django {R.mlp.django.fusion.routeAuc}), so extra capacity is
          not hiding a nonlinear structural pattern.
        </p>
        <p>
          Endpoints are the same labels-only trio as v1: always-Opus 70.6%,
          always-Qwen 58.0%, oracle 74.5% on django (n={R.djangoN}). Ranking
          quality only changes the path between those points.
        </p>

        <RouterV2RouteAucCurve />
        <p>
          The reconstructed fusion curve (seed 0) sits on the same no-signal
          diagonal as v1. Overlaying the two makes the result easier to see
          than the headline Δ: structure did not lift the curve above chance,
          it traced a different wobble around the same line.
        </p>

        <PaperSubsection id="figures" number="3.1" title="More figures">
          <RouterV2Figures />
        </PaperSubsection>

        <PaperSubsection id="tables" number="3.2" title="Tables">
          <PaperTable
            id="tab-logistic"
            caption="Table 2: Logistic headline across splits. Highlighted rows are the confirmatory django holdout. Accuracy stays under always-Qwen on django (58.0%)."
            highlight={(row) => row[1].includes("leave-django-out")}
            headers={["Arm", "Split", "Route-AUC", "AUROC", "Accuracy", "Brier"]}
            rows={[
              [
                "v1 text",
                "grouped 5-fold",
                R.logistic.grouped.text.routeAuc,
                R.logistic.grouped.text.auroc,
                R.logistic.grouped.text.acc,
                R.logistic.grouped.text.brier,
              ],
              [
                "v2 fusion",
                "grouped 5-fold",
                R.logistic.grouped.fusion.routeAuc,
                R.logistic.grouped.fusion.auroc,
                R.logistic.grouped.fusion.acc,
                R.logistic.grouped.fusion.brier,
              ],
              [
                "v2 metrics-only",
                "grouped 5-fold",
                R.logistic.grouped.metrics.routeAuc,
                R.logistic.grouped.metrics.auroc,
                R.logistic.grouped.metrics.acc,
                R.logistic.grouped.metrics.brier,
              ],
              [
                "v1 text",
                "leave-django-out n=231",
                R.logistic.django.text.routeAuc,
                R.logistic.django.text.auroc,
                R.logistic.django.text.acc,
                R.logistic.django.text.brier,
              ],
              [
                "v2 fusion",
                "leave-django-out n=231",
                R.logistic.django.fusion.routeAuc,
                R.logistic.django.fusion.auroc,
                R.logistic.django.fusion.acc,
                R.logistic.django.fusion.brier,
              ],
              [
                "v2 metrics-only",
                "leave-django-out n=231",
                R.logistic.django.metrics.routeAuc,
                R.logistic.django.metrics.auroc,
                R.logistic.django.metrics.acc,
                R.logistic.django.metrics.brier,
              ],
            ]}
          />
          <PaperTable
            id="tab-rest"
            caption="Table 3: Leave-repo reverse (hold n=269). Not averaged with django and not used as a ship criterion."
            headers={["Arm", "Route-AUC", "AUROC", "Accuracy"]}
            rows={[
              [
                "v1 text",
                R.logistic.rest.text.routeAuc,
                R.logistic.rest.text.auroc,
                R.logistic.rest.text.acc,
              ],
              [
                "v2 fusion",
                R.logistic.rest.fusion.routeAuc,
                R.logistic.rest.fusion.auroc,
                R.logistic.rest.fusion.acc,
              ],
              [
                "v2 metrics-only",
                R.logistic.rest.metrics.routeAuc,
                R.logistic.rest.metrics.auroc,
                R.logistic.rest.metrics.acc,
              ],
            ]}
          />
          <PaperTable
            id="tab-mlp"
            caption="Table 4: MLP diagnostic. Extra capacity fits noise. Metrics-only django Route-AUC 0.546 is a noisy cell (AUROC 0.521) and is not treated as a win."
            headers={[
              "Arm",
              "Grouped Route-AUC",
              "Grouped AUROC",
              "Django Route-AUC",
              "Django AUROC",
            ]}
            rows={[
              [
                "v1 text",
                R.mlp.grouped.text.routeAuc,
                R.mlp.grouped.text.auroc,
                R.mlp.django.text.routeAuc,
                R.mlp.django.text.auroc,
              ],
              [
                "v2 fusion",
                R.mlp.grouped.fusion.routeAuc,
                R.mlp.grouped.fusion.auroc,
                R.mlp.django.fusion.routeAuc,
                R.mlp.django.fusion.auroc,
              ],
              [
                "v2 metrics-only",
                R.mlp.grouped.metrics.routeAuc,
                R.mlp.grouped.metrics.auroc,
                R.mlp.django.metrics.routeAuc,
                R.mlp.django.metrics.auroc,
              ],
            ]}
          />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="interpretation" number="4" title="Interpretation">
        <p>
          Even with oracle file paths, AST counts add no lift over frozen issue
          text. Fusion is chance; metrics-only is chance or worse. A leak-free
          structural pipeline (BM25 files, whole-repo metrics, predicted
          locations) has strictly less information, so this ceiling already
          closes that direction.
        </p>
        <p>
          That matches the prompt-only floor in SWE-Router: embedding fusions
          stay near chance, and the lift — when it exists — is in K-turn
          trajectories.<PaperCite n={6} /> Remaining signal is that class. See{" "}
          <a href="/journal/2026-08-26-v3-trajectory-router-spec">
            v3 trajectory router
          </a>
          .
        </p>
      </PaperSection>

      <PaperSection id="next" number="5" title="Next">
        <p>
          Already superseded by v3. Do not pursue static structural fusion. On
          escalation, restart the strong model from the original issue text
          rather than the weak model’s partial attempt.<PaperCite n={6} />
        </p>
      </PaperSection>

      <PaperSection id="notes" number="6" title="Notes">
        <ul className="list-disc space-y-2 pl-6">
          <li>
            Curve reconstruction (added 2026-08-27). The original
            leave-django-out fusion head was not checkpointed, so the λ-sweep
            was refit from cached CLS + oracle AST vectors on the 269
            non-django tasks only (metrics scaled on that train fold). Per-seed
            Route-AUC matched the archived fusion figures bit-for-bit (seed 0
            = 0.469, seed 1 = 0.472, seed 2 = 0.505; mean 0.482). The
            reconstruction did not reuse any all-500 grouped checkpoint.
          </li>
          <li>
            The curve figure shows seed 0 only (Route-AUC 0.469), not the
            3-seed mean (0.482). Seed 0 sits slightly below the mean, same
            caveat as v1.
          </li>
          <li>
            Oracle file paths are a leak by design. This run is a ceiling
            test, not a deployable router.
          </li>
        </ul>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
