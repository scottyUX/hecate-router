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
    href: "/journal/2026-10-24-e07-reward-cap-smokes",
    title: "Experiment 7: the released config zeroes most resolved training rollouts",
    date: "2026-10-24",
    status: "smokes · training not started",
    summary:
      "One-step GRPO smokes before training. Released settings (max_turns 1): 30/32 rollouts hit a 4,096-token cap on the whole conversation and 8 of 10 resolved rollouts scored 0. With max_turns 9: 11 rewarded, 0 zeroed, but CUDA out of memory in the update. Next: sequence parallelism across the two A100s.",
    archiveEntryId: "2026-10-24-e07-reward-cap-smokes",
  },
  {
    href: "/journal/2026-10-24-e07-check1-three-pass",
    title: "Experiment 7: three passes per arm clear the step gate",
    date: "2026-10-24",
    status: "check 1 pass · train next",
    summary:
      "Three passes per arm, joined on 47 of 49 issues: Flash-Lite alone 34.0%, 25.7 steps; untrained advisor 13.5%, 22.0 steps. Step gap 3.7 [+0.6, +6.7], resolve gap 20.6 points. Check 1 passes on the point estimate; the three-pass rule was recorded after the one-pass 1.94. Next: GRPO on 2×A100 on-demand.",
    archiveEntryId: "2026-10-24-e07-check1-three-pass",
  },
  {
    href: "/journal/2026-10-23-e07-untrained-advisor",
    title: "Experiment 7: untrained advisor does not clear the step gate",
    date: "2026-10-23",
    status: "one pass · superseded by 24 Oct",
    summary:
      "Untrained Qwen2.5-7B on Flash-Lite, 49 test issues: 7/49 (14.3%), 21.86 steps, 0 errors. Gap versus Flash-Lite alone (22/49, 23.8 steps) is 1.94 steps, under the cutoff of 2. GRPO was not started.",
    archiveEntryId: "2026-10-23-e07-untrained-advisor",
  },
  {
    href: "/journal/2026-10-19-e07-week1-student-baselines",
    title: "Experiment 7: Flash-Lite baselines and an efficiency prompt",
    date: "2026-10-19",
    status: "student rows done · advisor not started",
    summary:
      "Flash-Lite alone 22/49 (44.9%), 23.8 steps. The efficiency sentence solved 14/49 (28.6%) in 26.6 steps, and 16.5 steps on the issues it still solved. Flash harness check 31/49, 19.4 steps. Training probe 17/56 passes. Tuesday compares the untrained advisor with 23.8, not 26.6.",
    archiveEntryId: "2026-10-19-e07-week1-student-baselines",
  },
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
