import type { ComponentType } from "react";

import { E07Check1Paper } from "@/components/journal/e07-check1-paper";
import { E07RewardCapPaper } from "@/components/journal/e07-reward-cap-paper";
import { E07Smoke3MemoryPaper } from "@/components/journal/e07-smoke3-memory-paper";
import { E07UntrainedAdvisorPaper } from "@/components/journal/e07-untrained-advisor-paper";
import { E07Week1Paper } from "@/components/journal/e07-week1-paper";
import { RouterE02Paper } from "@/components/journal/router-e02-paper";
import { RouterV1Paper } from "@/components/journal/router-v1-paper";
import { RouterV2Paper } from "@/components/journal/router-v2-paper";
import { RouterV3Paper } from "@/components/journal/router-v3-paper";

export const STATIC_PAPERS: Record<string, ComponentType> = {
  "2026-10-24-e07-smoke3-memory": E07Smoke3MemoryPaper,
  "2026-10-24-e07-reward-cap-smokes": E07RewardCapPaper,
  "2026-10-24-e07-check1-three-pass": E07Check1Paper,
  "2026-10-23-e07-untrained-advisor": E07UntrainedAdvisorPaper,
  "2026-10-19-e07-week1-student-baselines": E07Week1Paper,
  "2026-09-15-e02-specialist-django-smoke": RouterE02Paper,
  "2026-08-25-text-only-router-v1": RouterV1Paper,
  "2026-08-26-oracle-metrics-fusion-v2": RouterV2Paper,
  "2026-08-26-v3-trajectory-router-spec": RouterV3Paper,
};

export function paperForEntry(entryId: string): ComponentType | undefined {
  return STATIC_PAPERS[entryId];
}
