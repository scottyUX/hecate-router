import { RouterV2Figures } from "@/components/experiments/router-v2-figures";
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
import { ROUTER_V2 as R } from "@/lib/experiments/router-v2";

const SLUG = "2026-08-26-oracle-metrics-fusion-v2";

const toc: PaperTocItem[] = [
  { href: "#introduction", label: "Introduction" },
  { href: "#rq", label: "Research question" },
  { href: "#hypothesis", label: "Hypothesis" },
  { href: "#setup", label: "Setup" },
  {
    href: "#results",
    label: "Results",
    children: [
      { href: "#figures", label: "Figures" },
      { href: "#tables", label: "Tables" },
    ],
  },
  { href: "#discussion", label: "Discussion" },
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
      title="Structural fusion v2: oracle AST metrics on gold-patch files still don't beat the text floor"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations="SWE-bench Verified (500) · frozen ModernBERT-base"
      date="August 26, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-26"
      tags="router · structural-fusion · ast · oracle-ceiling · verified"
      toc={toc}
    >
      <PaperAbstract>
        <p>
          Routing SWE-bench tasks between a cheap model (Qwen3-Coder-480B) and a
          frontier model (Claude 4 Opus) is only useful if the router can tell,
          before execution, which issues the cheap model will resolve. Frozen
          issue text is already at chance on held-out repos: v1 django holdout
          Route-AUC {R.logistic.django.text.routeAuc}, AUROC{" "}
          {R.logistic.django.text.auroc}. Prompt-only LLM routers share that
          Bayes-error floor: two issues can read alike and hide a typo versus a
          multi-file refactor.
        </p>
        <p>
          <strong>Research question.</strong> Does static code structure — even
          when the router is told exactly which files the gold patch will touch
          — add ranking signal that issue text lacks?
        </p>
        <p>
          <strong>Hypothesis.</strong> If structure carries that signal, then a
          12-d Python AST vector on gold-patch files at{" "}
          <code>base_commit</code>, fused with frozen ModernBERT CLS, should
          beat text-only on django holdout (n={R.djangoN}) and meet Route-AUC ≥{" "}
          {R.target.djangoRouteAuc.toFixed(2)} and AUROC ≥{" "}
          {R.target.djangoAuroc.toFixed(2)}. Metrics-only should itself rank
          above chance. Failure of this leaky ceiling would close leak-free
          structural fusion as well, because a deployed router has strictly less
          information.
        </p>
        <p>
          <strong>Result.</strong> The hypothesis is not supported. Logistic
          fusion is {R.logistic.django.fusion.routeAuc} Route-AUC and{" "}
          {R.logistic.django.fusion.auroc} AUROC versus v1{" "}
          {R.logistic.django.text.routeAuc} / {R.logistic.django.text.auroc}.
          Metrics-only is {R.logistic.django.metrics.routeAuc} /{" "}
          {R.logistic.django.metrics.auroc}. Grouped fusion{" "}
          {R.logistic.grouped.fusion.routeAuc.split(" ")[0]} is the same 0.589
          trap. Static pre-execution structure is closed; remaining signal is
          trajectory-level.
        </p>
      </PaperAbstract>

      <PaperToc items={toc} />

      <PaperSection id="introduction" number="1" title="Introduction">
        <p>
          v1 established that a frozen ModernBERT embedding of issue text alone
          ranks “will Qwen3-Coder resolve this task” barely above chance on
          held-out repos.<PaperCite n={4} /> Django holdout AUROC is{" "}
          {R.logistic.django.text.auroc} and Route-AUC is{" "}
          {R.logistic.django.text.routeAuc}. The grouped 5-fold headline
          (Route-AUC {R.logistic.grouped.text.routeAuc}) looked better but is
          mostly the django fold behaving near-chance averaged against a couple
          of small noisy folds — not a stable estimate.
        </p>
        <p>
          The open question from v1 was whether the router needs some structural
          view of the repo, or whether text is already the ceiling for a frozen
          encoder. Prompt-only LLM routers inherit that same limit: two issues
          can read alike and hide a one-line typo versus a multi-file
          refactor.<PaperCite n={5} /> This note answers a stronger version of
          that question: give the router the gold-patch file list, compute
          Python AST counts on those files at <code>base_commit</code>, and fuse
          the 12-d vector with frozen CLS. If that still fails, a leak-free file
          guesser has           strictly less information and is not worth pursuing.
        </p>
      </PaperSection>

      <PaperSection id="rq" number="2" title="Research question">
        <PaperCallout label="RQ1">
          <p>
            On SWE-bench Verified (500), with a frozen ModernBERT encoder, do
            Python AST metrics computed on gold-patch files at{" "}
            <code>base_commit</code> — alone or fused with issue-text CLS —
            improve ranking of “will Qwen3-Coder resolve this task” over
            text-only, on a repository holdout?
          </p>
        </PaperCallout>
        <p>
          The confirmatory split is leave-django-out (n={R.djangoN}). Grouped
          5-fold is reported but is not the decision split: v1 already showed
          that headline is a django-weighted average against small noisy folds.
          The practical implication of a negative answer is that a leak-free
          structural pipeline (BM25 files, whole-repo ts-repo-metrics, predicted
          locations) cannot beat a ceiling that itself did not move.
        </p>
      </PaperSection>

      <PaperSection id="hypothesis" number="3" title="Hypothesis">
        <p>
          If static structure carries routing signal that issue text lacks, the
          leaky oracle should be the easiest place to see it. We pre-register
          two claims against django holdout. Both must hold for structural
          fusion to stay open.
        </p>
        <PaperCallout label="H1 — fusion ceiling">
          <p>
            Logistic fusion of frozen CLS and the 12-d oracle AST vector beats
            v1 text-only on django holdout and meets the ship bar: Route-AUC ≥{" "}
            {R.target.djangoRouteAuc.toFixed(2)} with tight std (~±0.03), and
            AUROC ≥ {R.target.djangoAuroc.toFixed(2)}.
          </p>
        </PaperCallout>
        <PaperCallout label="H2 — structure alone">
          <p>
            The same AST vector with no text ranks above chance on django
            holdout (AUROC ≥ {R.target.djangoAuroc.toFixed(2)}). If H2 fails
            while H1 holds, structure is only useful as a text complement. If
            both fail, static structure is closed.
          </p>
        </PaperCallout>
        <p>
          MLP is a diagnostic for extra capacity, not a confirmatory head.
          Grouped 5-fold is not used to accept H1 or H2.
        </p>
      </PaperSection>

      <PaperSection id="setup" number="4" title="Setup">
        <p>
          Same 500 SWE-bench Verified tasks<PaperCite n={[1, 2]} /> and
          matched-scaffold mini-SWE-agent v1.0.0 labels (Qwen3-Coder-480B vs
          Claude 4 Opus).<PaperCite n={3} /> Frozen CLS (768) plus a 12-d Python
          AST vector on gold-patch files: n_files, n_functions, n_imports, loc,
          mean/max cyclomatic, mean/max nesting, mean/max function LOC, mean
          arity, parse_errors. No fan-out. Metrics scaled on the train fold
          only. Weighted BCE. Fail-closed {R.n}/{R.n} cache ({R.cacheFiles}{" "}
          oracle files, {R.parseErrors} parse error). Prompt char caps were not
          applied. Encoder stayed frozen.<PaperCite n={4} /> Spec 015{" "}
          <code>run_train.py</code> unchanged.
        </p>
        <p>
          Headline head is logistic. MLP is a diagnostic for extra capacity.
          Django holdout (n={R.djangoN}) is the target split; grouped 5-fold is
          reported but not used as a ship criterion.
        </p>
      </PaperSection>

      <PaperSection id="results" number="5" title="Results">
        <p>
          We answer RQ1 by testing H1 and H2 on django holdout. Confirmatory
          metric is Route-AUC; AUROC is co-primary because H1 names the ship
          bar. Neither hypothesis is supported.
        </p>
        <PaperCallout label="H1 rejected">
          <p>
            Fusion Route-AUC is {R.logistic.django.fusion.routeAuc} versus text{" "}
            {R.logistic.django.text.routeAuc} (Δ ≈ +0.005, inside the ±0.02
            band). Fusion AUROC is {R.logistic.django.fusion.auroc} versus{" "}
            {R.logistic.django.text.auroc}. Both miss ≥{" "}
            {R.target.djangoRouteAuc.toFixed(2)} / ≥{" "}
            {R.target.djangoAuroc.toFixed(2)}. Oracle fusion does not beat the
            text floor.
          </p>
        </PaperCallout>
        <PaperCallout label="H2 rejected">
          <p>
            Metrics-only django Route-AUC is {R.logistic.django.metrics.routeAuc}{" "}
            and AUROC {R.logistic.django.metrics.auroc} — at or below chance,
            and worse than text. AST counts have no independent ranking signal
            on the holdout.
          </p>
        </PaperCallout>
        <p>
          <strong>RQ1.</strong> No. Oracle AST metrics do not improve routing
          over text-only. Grouped fusion {R.logistic.grouped.fusion.routeAuc}{" "}
          versus grouped text {R.logistic.grouped.text.routeAuc} is the same
          0.589 trap and is not confirmatory. MLP loses to logistic in every
          arm, including a noisy metrics-only django Route-AUC of 0.546 (AUROC
          0.521) that we do not treat as support for H2.
        </p>

        <PaperSubsection id="figures" number="5.1" title="Figures">
          <RouterV2Figures />
        </PaperSubsection>

        <PaperSubsection id="tables" number="5.2" title="Tables">
          <PaperTable
            id="tab-hypotheses"
            caption="Table 1: Decisions against H1 and H2. Confirmatory split is django holdout (n=231). Logistic head, frozen encoder."
            headers={["Claim", "Test", "Observed", "Decision"]}
            rows={[
              [
                "H1 fusion beats text and hits ship bar",
                `django Route-AUC ≥ ${R.target.djangoRouteAuc.toFixed(2)}, AUROC ≥ ${R.target.djangoAuroc.toFixed(2)}`,
                `${R.logistic.django.fusion.routeAuc} / ${R.logistic.django.fusion.auroc} vs text ${R.logistic.django.text.routeAuc} / ${R.logistic.django.text.auroc}`,
                "Rejected",
              ],
              [
                "H2 metrics-only above chance",
                `django AUROC ≥ ${R.target.djangoAuroc.toFixed(2)}`,
                `${R.logistic.django.metrics.routeAuc} / ${R.logistic.django.metrics.auroc}`,
                "Rejected",
              ],
              [
                "RQ1 structure adds ranking signal",
                "H1 or H2 accepted",
                "Both rejected; grouped fusion is the 0.589 trap",
                "No",
              ],
            ]}
          />
          <PaperTable
            id="tab-target"
            caption="Table 2: Where we are versus the django holdout target named in H1."
            headers={["Metric", "Where we are", "H1 target"]}
            rows={[
              [
                "Django holdout Route-AUC",
                `fusion ${R.logistic.django.fusion.routeAuc}`,
                "≥ 0.55, tight std (~±0.03)",
              ],
              [
                "Django holdout AUROC",
                `fusion ${R.logistic.django.fusion.auroc}`,
                "≥ 0.60",
              ],
              [
                "Grouped 5-fold Route-AUC",
                `fusion ${R.logistic.grouped.fusion.routeAuc}`,
                "Not confirmatory",
              ],
              [
                "Metrics-only (H2)",
                `grouped ${R.logistic.grouped.metrics.routeAuc} / django ${R.logistic.django.metrics.routeAuc}`,
                "Dead end",
              ],
            ]}
          />
          <PaperTable
            id="tab-logistic"
            caption="Table 3: Logistic headline. Highlighted rows are the confirmatory django holdout used to test H1 and H2. Accuracy stays under always-Qwen on django (58.0%)."
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
            caption="Table 4: Leave-repo reverse (hold n=269). Not averaged with django and not used to accept H1 or H2."
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
            caption="Table 5: MLP diagnostic. Extra capacity fits noise and is not a confirmatory test of H1/H2. Metrics-only django Route-AUC 0.546 is a noisy cell (AUROC 0.521)."
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

      <PaperSection id="discussion" number="6" title="Discussion">
        <p>
          RQ1 is answered in the negative, and both pre-registered claims fail.
          Even with oracle file paths, AST counts add no lift over frozen issue
          text. A leak-free structural pipeline has strictly less information,
          so H1/H2 already close that direction. That matches the prompt-only
          floor in SWE-Router: embedding fusions stay near chance, and the lift
          is K-turn trajectories (gpt-5-mini K=3 Route-AUC 0.694; deepseek K=2
          0.780 vs K=0 0.627).<PaperCite n={6} /> Next signal is that class. On
          escalation, restart the strong model from the original issue text
          rather than the weak model’s partial attempt.<PaperCite n={6} />
        </p>
      </PaperSection>

      <PaperSection id="next" number="7" title="Next">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Do not pursue static structural fusion (BM25 files, whole-repo
            ts-repo-metrics, or other non-oracle file guesses).
          </li>
          <li>
            v3: K-turn trajectory-conditioned router (K=3, LoRA value head
            Qwen2.5-Coder-7B r=32 α=64), matching SWE-Router’s primary
            setting.<PaperCite n={6} /> Same django-holdout target.
          </li>
          <li>
            Check public mini-swe-agent v1.0.0 logs before paying for new
            Qwen3-Coder turns.<PaperCite n={3} />
          </li>
        </ol>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
