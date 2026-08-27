export type ExperimentReport = {
  href: string;
  title: string;
  date: string;
  status: string;
  summary: string;
  archiveEntryId?: string;
};

export const EXPERIMENT_REPORTS: ExperimentReport[] = [
  {
    href: "/journal/2026-08-26-v3-trajectory-router-spec",
    title: "K-turn trajectory router v3",
    date: "2026-08-27",
    status: "missed target",
    summary:
      "K=3 django Route-AUC 0.587 lost to K=0 LoRA 0.686 (1 seed). Extra turns did not help on repo holdout.",
    archiveEntryId: "2026-08-26-v3-trajectory-router-spec",
  },
  {
    href: "/journal/2026-08-26-oracle-metrics-fusion-v2",
    title: "Structural fusion v2",
    date: "2026-08-26",
    status: "missed target",
    summary:
      "Oracle AST on gold-patch files does not beat the text floor. Django holdout fusion Route-AUC 0.482 — still chance.",
    archiveEntryId: "2026-08-26-oracle-metrics-fusion-v2",
  },
  {
    href: "/journal/2026-08-25-text-only-router-v1",
    title: "Text-only router v1",
    date: "2026-08-25",
    status: "missed target",
    summary:
      "Frozen issue text is chance on django holdout (Route-AUC 0.477). Grouped 0.589 is the trap.",
    archiveEntryId: "2026-08-25-text-only-router-v1",
  },
];

export function reportForEntry(entryId: string): ExperimentReport | undefined {
  return EXPERIMENT_REPORTS.find((item) => item.archiveEntryId === entryId);
}
