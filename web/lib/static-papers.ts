import type { ComponentType } from "react";

import { RouterV1Paper } from "@/components/journal/router-v1-paper";
import { RouterV2Paper } from "@/components/journal/router-v2-paper";
import { RouterV3Paper } from "@/components/journal/router-v3-paper";

export const STATIC_PAPERS: Record<string, ComponentType> = {
  "2026-08-25-text-only-router-v1": RouterV1Paper,
  "2026-08-26-oracle-metrics-fusion-v2": RouterV2Paper,
  "2026-08-26-v3-trajectory-router-spec": RouterV3Paper,
};

export function paperForEntry(entryId: string): ComponentType | undefined {
  return STATIC_PAPERS[entryId];
}
