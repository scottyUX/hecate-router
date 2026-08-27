import { RouterV1Figures } from "@/components/experiments/router-v1-figures";
import {
  PaperAbstract,
  PaperCallout,
  PaperCite,
  PaperReferences,
  PaperSection,
  PaperShell,
  PaperSubsection,
  type PaperTocItem,
} from "@/components/paper/paper-shell";
import { PaperTable } from "@/components/paper/paper-table";
import { requireJournalPage } from "@/lib/auth";
import { ROUTER_V1 as R } from "@/lib/experiments/router-v1";
import { glossaryEntries } from "@/lib/paper-glossary";

const SLUG = "2026-08-25-text-only-router-v1";

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
  { href: "#next", label: "Future work" },
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

export async function RouterV1Paper() {
  await requireJournalPage(`/journal/${SLUG}`);

  return (
    <PaperShell
      title="Text-only router v1: frozen ModernBERT on Verified issue text"
      authors={
        <>
          <a href="/">Hecate Lab</a>
        </>
      }
      affiliations="SWE-bench Verified (500) · frozen ModernBERT-base"
      date="August 25, 2026"
      subjects={[
        "Software Engineering (cs.SE)",
        "Machine Learning (cs.LG)",
        "Artificial Intelligence (cs.AI)",
      ]}
      updated="2026-08-26"
      tags="router · text-only · modernbert · verified · E-M4"
      toc={toc}
      glossary={glossaryEntries("Route-AUC", "AUROC", "CLS", "MLP", "Brier")}
    >
      <PaperAbstract>
        <p>
          A router between Qwen3-Coder-480B and Claude 4 Opus is only useful if
          it can rank, before execution, which SWE-bench issues the cheap model
          will resolve. The input here is only GitHub issue text: no repo,
          diffs, tests, or traces.<PaperCite n={[1, 2]} /> Resolve-rate headroom
          versus always-Opus is {R.headroomPp}pp (oracle {R.oracle} vs always-large{" "}
          {R.alwaysLarge}); the 258 both-win tasks are a cost prize, not an
          accuracy prize.
        </p>
        <p>
          <strong>Research question.</strong> Can a frozen ModernBERT embedding
          of <code>problem_statement</code> alone rank “will Qwen3-Coder resolve
          this task” above chance when the test repository is held out?
        </p>
        <p>
          <strong>Hypothesis.</strong> If issue text is a sufficient routing
          signal, logistic readout of frozen CLS (ModernBERT’s 768-d
          classification-token embedding) should meet Route-AUC ≥{" "}
          {R.target.routeAuc.toFixed(2)} — routing quality as the
          cheap/expensive threshold is swept; 0.5 is chance — and AUROC ≥{" "}
          {R.target.auroc.toFixed(2)} — pairwise ranking of Qwen-successes
          versus failures; 0.5 is a coin flip — on grouped-by-repo CV, and the
          same bar on django holdout (n={R.djangoN}). An MLP (small nonlinear
          net) should beat logistic if the embedding space has a nonlinear
          pattern.
        </p>
        <p>
          <strong>Result.</strong> The hypothesis is not supported. Logistic
          django holdout is {R.logistic.django.routeAuc} Route-AUC /{" "}
          {R.logistic.django.auroc} AUROC. Grouped {R.logistic.grouped.routeAuc}{" "}
          is a django-weighted trap. MLP loses to logistic. Frozen issue text is
          the v1 floor; it is chance, not a router.
        </p>
      </PaperAbstract>

      <PaperSection id="introduction" number="1" title="Introduction">
        <p>
          Prompt-only LLM routers decide from the query string
          alone.<PaperCite n={5} /> In agentic SWE that string can look the same
          for a one-line typo and a multi-file refactor, which is a Bayes-error
          floor.<PaperCite n={6} /> v1 measures that floor on this lab’s pair:
          Qwen3-Coder-480B vs Claude 4 Opus, mini-SWE-agent v1.0.0, SWE-bench
          Verified (500).<PaperCite n={[2, 3]} />
        </p>
        <p>
          The encoder is frozen ModernBERT-base.<PaperCite n={4} /> If a linear
          readout of locked CLS cannot rank Qwen-success, unfreezing would only
          let the encoder memorize Verified phrasing. That is why this run is
          the text floor later fusion and trajectory work have to beat.
        </p>
      </PaperSection>

      <PaperSection id="rq" number="2" title="Research question">
        <PaperCallout label="RQ1">
          <p>
            Does frozen issue text, with no codebase or trace, rank “will
            Qwen3-Coder resolve this SWE-bench Verified task” above chance when
            evaluation is grouped by repository?
          </p>
        </PaperCallout>
        <p>
          Confirmatory split is leave-django-out (n={R.djangoN}, 46% of the
          data). Grouped 5-fold is reported; it is not the decision split if
          django is chance and a few small folds inflate the mean. A leaky
          label-stratified split is a sensitivity check: if it looks much
          better than grouped, the headline was repo leak.
        </p>
      </PaperSection>

      <PaperSection id="hypothesis" number="3" title="Hypothesis">
        <p>
          If GitHub issue text is a sufficient routing feature, a cheap frozen
          encoder should clear a usable ranking bar. We treat two claims as
          jointly required for a text-only router to stay open.
        </p>
        <PaperCallout label="H1 — text ranking">
          <p>
            Logistic on frozen CLS meets Route-AUC ≥ {R.target.routeAuc.toFixed(2)}{" "}
            and AUROC ≥ {R.target.auroc.toFixed(2)} on django holdout. Grouped
            5-fold must not be the only number that looks alive.
          </p>
        </PaperCallout>
        <PaperCallout label="H2 — extra capacity">
          <p>
            MLP on the same frozen vectors beats logistic on django holdout. If
            H2 fails, there is no nonlinear pattern in CLS space worth fitting.
          </p>
        </PaperCallout>
      </PaperSection>

      <PaperSection id="setup" number="4" title="Setup">
        <p>
          500 Verified tasks, labels from matched-scaffold mini-SWE-agent
          v1.0.0 (2025-08-02).<PaperCite n={[1, 2, 3]} /> Target is{" "}
          <code>small_model_resolved</code>. Frozen CLS (768-d), 2048-token
          truncation ({(R.truncation * 100).toFixed(1)}% of examples). Two
          heads, same recipe (4 epochs, batch 8, AdamW, lr 2e-5, BCE): logistic
          768→1 and MLP 768→128→GELU→dropout 0.2→1. Primary metric is
          normalized Route-AUC; AUROC, accuracy, and Brier (mean squared error
          of predicted probabilities; lower is better) are secondary. F1 at
          0.5 is a threshold trap and is not confirmatory.
        </p>
        <p>
          Headline CV is grouped by repo (12 repos, greedy pack). Label-stratified
          5-fold is leaky. Leave-django-out trains on 11 repos and evaluates on
          django; reverse (train on django, hold n={R.restN}) is reported
          separately and not averaged.
        </p>
      </PaperSection>

      <PaperSection id="results" number="5" title="Results">
        <p>
          We answer RQ1 by testing H1 and H2. Neither is supported. Nothing
          here is a working router.
        </p>
        <PaperCallout label="H1 rejected">
          <p>
            Django holdout logistic is {R.logistic.django.routeAuc} Route-AUC
            and {R.logistic.django.auroc} AUROC — chance, and below ≥{" "}
            {R.target.routeAuc.toFixed(2)} / ≥ {R.target.auroc.toFixed(2)}.
            Accuracy {R.logistic.django.acc} is under django always-Qwen (
            {(R.djangoAlwaysSmall * 100).toFixed(1)}%). Grouped{" "}
            {R.logistic.grouped.routeAuc} is not confirmatory: seed-0 django is
            0.45 on 231 tasks.
          </p>
        </PaperCallout>
        <PaperCallout label="H2 rejected">
          <p>
            MLP grouped Route-AUC is {R.mlp.grouped.routeAuc}, below logistic
            and below chance. Django MLP {R.mlp.django.routeAuc} /{" "}
            {R.mlp.django.auroc} does not beat logistic. Extra capacity fitted
            fold noise.
          </p>
        </PaperCallout>
        <p>
          <strong>RQ1.</strong> No. Frozen issue text does not rank Qwen-success
          above chance on a held-out repo. Leaky stratified Route-AUC{" "}
          {R.logistic.grouped.leakyRouteAuc} is still chance, so grouped CV did
          not hide a real text effect.
        </p>

        <PaperSubsection id="figures" number="5.1" title="Figures">
          <RouterV1Figures />
        </PaperSubsection>

        <PaperSubsection id="tables" number="5.2" title="Tables">
          <PaperTable
            id="tab-v1-hypotheses"
            caption="Table 1: Decisions against H1 and H2. Confirmatory split is django holdout (n=231)."
            headers={["Claim", "Test", "Observed", "Decision"]}
            rows={[
              [
                "H1 text ranking",
                `django Route-AUC ≥ ${R.target.routeAuc.toFixed(2)}, AUROC ≥ ${R.target.auroc.toFixed(2)}`,
                `${R.logistic.django.routeAuc} / ${R.logistic.django.auroc}`,
                "Rejected",
              ],
              [
                "H2 MLP beats logistic",
                "django MLP > logistic",
                `MLP ${R.mlp.django.routeAuc} vs logistic ${R.logistic.django.routeAuc}`,
                "Rejected",
              ],
              [
                "RQ1 issue text is enough",
                "H1 accepted",
                "Grouped 0.589 is the trap; leaky still chance",
                "No",
              ],
            ]}
          />
          <PaperTable
            id="tab-v1-ceiling"
            caption="Table 2: Label ceiling before any model. Headroom vs always-Opus is only the 19 small-only wins."
            headers={["Policy", "Resolved", "Note"]}
            rows={[
              ["Always Qwen", `${(R.alwaysSmall * 100).toFixed(1)}% (277/500)`, "Cheap default"],
              ["Always Opus", `${(R.alwaysLarge * 100).toFixed(1)}% (338/500)`, "Expensive default"],
              ["Oracle", `${(R.oracle * 100).toFixed(1)}% (357/500)`, `Headroom ${R.headroomPp}pp`],
              [
                "Complementarity",
                `${R.complementarity.smallOnly} / ${R.complementarity.both} / ${R.complementarity.opusOnly} / ${R.complementarity.neither}`,
                "small-only / both / Opus-only / neither",
              ],
            ]}
          />
          <PaperTable
            id="tab-v1-headline"
            caption="Table 3: Frozen-head means over 15 runs (5 folds × 3 seeds). Highlighted rows are django holdout."
            highlight={(row) => row[1].includes("leave-django-out")}
            headers={["Head", "Split", "Route-AUC", "AUROC", "Accuracy"]}
            rows={[
              ["logistic", "grouped 5-fold", R.logistic.grouped.routeAuc, R.logistic.grouped.auroc, R.logistic.grouped.acc],
              ["MLP", "grouped 5-fold", R.mlp.grouped.routeAuc, R.mlp.grouped.auroc, R.mlp.grouped.acc],
              ["logistic", "leaky stratified", R.logistic.grouped.leakyRouteAuc, "—", "—"],
              ["logistic", "leave-django-out n=231", R.logistic.django.routeAuc, R.logistic.django.auroc, R.logistic.django.acc],
              ["MLP", "leave-django-out n=231", R.mlp.django.routeAuc, R.mlp.django.auroc, "—"],
              ["logistic", "leave-rest n=269", R.logistic.rest.routeAuc, R.logistic.rest.auroc, R.logistic.rest.acc],
            ]}
          />
          <PaperTable
            id="tab-v1-folds"
            caption="Table 4: Logistic grouped, seed 0. Django is one test fold every seed."
            highlight={(row) => row[0].includes("django")}
            headers={["Test fold", "n", "Route-AUC", "AUROC"]}
            rows={[
              ["django only", "231", "0.45", "0.51"],
              ["sympy only", "75", "0.84", "0.57"],
              ["sphinx + pytest + seaborn", "65", "0.51", "0.57"],
              ["matplotlib mix", "65", "0.55", "0.50"],
              ["sklearn + astropy + pylint", "64", "0.35", "0.34"],
            ]}
          />
        </PaperSubsection>
      </PaperSection>

      <PaperSection id="discussion" number="6" title="Discussion">
        <p>
          RQ1 is answered in the negative. AUROC ~0.53 is a coin with a tiny
          dent, consistent with SWE-Router prompt-only embedding
          baselines.<PaperCite n={6} /> Accuracy below the 55.4% always-Qwen
          base rate means the head does not even match the majority. F1 ~0.63
          is the threshold trap of saying yes often. Brier ~0.251 is an
          uninformative 0.5 guess.
        </p>
        <p>
          This is not a join bug: labels matched published 55.4% / 67.6% at
          500/500. Truncation at 2048 tokens ({(R.truncation * 100).toFixed(1)}%)
          is not the failure mode. The remaining question is whether the router
          needs structure or a short look at the agent’s own attempt — v2 and
          v3.
        </p>
      </PaperSection>

      <PaperSection id="next" number="7" title="Future work">
        <ol className="list-decimal space-y-2 pl-6">
          <li>
            Oracle-file metrics fusion v2 is done: django 0.482 / 0.518 vs v1
            0.477 / 0.516. Did not beat this floor. See{" "}
            <a href="/journal/2026-08-26-oracle-metrics-fusion-v2">
              structural fusion v2
            </a>
            .
          </li>
          <li>
            Do not unfreeze BERT on issue text. Do not treat grouped 0.589 as a
            working router.
          </li>
          <li>
            v3: K-turn trajectory-conditioned value head, same django-holdout
            target.<PaperCite n={6} />
          </li>
        </ol>
      </PaperSection>

      <PaperReferences items={[...references]} />
    </PaperShell>
  );
}
