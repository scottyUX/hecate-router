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
    href: "/experiments/router-v2",
    title: "Structural fusion v2",
    date: "2026-08-26",
    status: "missed target",
    summary:
      "Oracle AST on gold-patch files does not beat the text floor. Django holdout still chance.",
    archiveEntryId: "2026-08-26-oracle-metrics-fusion-v2",
  },
];

export function reportForEntry(entryId: string): ExperimentReport | undefined {
  return EXPERIMENT_REPORTS.find((item) => item.archiveEntryId === entryId);
}
