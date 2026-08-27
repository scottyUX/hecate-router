export const PAPER_GLOSSARY = {
  "Route-AUC":
    "Routing quality as you sweep the cheap-vs-expensive threshold: resolved rate versus cost. 0.5 is random ordering; 1 is perfect. This lab’s ship metric.",
  AUROC: "Area under the ROC curve. How often a true cheap-model success ranks above a failure. 0.5 is a coin flip. Diagnostic here — we do not gate on it.",
  AST: "Abstract syntax tree: a parse of source code into structure (functions, classes, complexity) rather than raw text.",
  LoRA: "Low-Rank Adaptation. Trains a thin set of extra weights instead of the whole network, so a 7B model can be specialized cheaply.",
  "value head":
    "A small classifier on the last token that scores P(cheap model resolves). That score is what we threshold to route cheap or escalate.",
  Brier:
    "Mean squared error of predicted probabilities. 0 is perfect; a constant 0.5 guess scores 0.25. Lower is better.",
  CLS: "The classification-token embedding from a BERT-style encoder. Here, frozen ModernBERT’s 768-d summary of the issue text.",
  MLP: "Multilayer perceptron: a small nonlinear network. Here, an alternative to logistic regression on the same embeddings.",
  QLoRA:
    "Quantized LoRA: 4-bit base weights plus full-precision adapters, so 7B training fits on one L4 GPU.",
  "K-turn":
    "The first K user/observation turns of the cheap agent’s trace. K=0 is issue text alone; K=3 packs the first three turns.",
} as const;

export type GlossaryTerm = keyof typeof PAPER_GLOSSARY;

export type GlossaryEntry = { term: string; definition: string };

export function glossaryEntries(...keys: GlossaryTerm[]): GlossaryEntry[] {
  return keys.map((term) => ({ term, definition: PAPER_GLOSSARY[term] }));
}
