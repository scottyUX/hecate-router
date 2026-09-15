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
    href: "/journal/2026-09-15-e02-specialist-django-smoke",
    title: "Experiment 2: django in-distribution router, seed 0",
    date: "2026-09-15",
    status: "smoke · ES rerun pending",
    summary:
      "Q2.1: K=0 LoRA 0.482 vs frozen 0.373, not a pass at n=46. Q2.2: K=3 overfit and never matches Opus quality. Q2.3: K=1 hit 33 at 26 Opus calls ($31.88, 35.9%) — diagnostic only. Cost ceiling is the same shape as leave-django-out (~60–76%). Next: early-stopped B/C/D.",
    archiveEntryId: "2026-09-15-e02-specialist-django-smoke",
  },
  {
    href: "/journal/2026-08-26-v3-trajectory-router-spec",
    title: "K-turn trajectory router v3",
    date: "2026-08-31",
    status: "H1 rejected · RQ2 yes",
    summary:
      "K=3 lost to K=0 on django (0.587 vs 0.686). A 7B LoRA still beat frozen v1/v2 (~0.48) on Route-AUC — a generalist lift, not trajectory lift.",
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
