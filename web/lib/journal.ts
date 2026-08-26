export const JOURNAL_STATUSES = [
  "in-progress",
  "resolved",
  "blocked",
  "abandoned",
] as const;

export const JOURNAL_VISIBILITIES = ["public", "private"] as const;

export const JOURNAL_COMPONENTS = [
  "semantic-gate",
  "structural-gate",
  "routing-gate",
  "swe-bench",
  "devbench",
  "cohort",
  "sandbox-grader",
  "infra",
  "meeting",
] as const;

export type JournalStatus = (typeof JOURNAL_STATUSES)[number];
export type JournalVisibility = (typeof JOURNAL_VISIBILITIES)[number];
export type JournalComponent = (typeof JOURNAL_COMPONENTS)[number];

export type JournalEntry = {
  id: string;
  entry_id: string;
  title: string;
  date: string;
  visibility: JournalVisibility;
  status: JournalStatus;
  component: string[];
  commit: string | null;
  related_entries: string[];
  tags: string[];
  context: string;
  method: string;
  result: string;
  interpretation: string;
  next_steps: string;
  notes: string;
  author_id: string;
  author_email: string | null;
  created_at: string;
  updated_at: string;
};

export type JournalEntryInput = {
  entry_id: string;
  title: string;
  date: string;
  visibility: JournalVisibility;
  status: JournalStatus;
  component: string[];
  commit: string;
  related_entries: string[];
  tags: string[];
  context: string;
  method: string;
  result: string;
  interpretation: string;
  next_steps: string;
  notes: string;
};

export function slugifyTitle(title: string): string {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export function makeEntryId(date: string, title: string): string {
  const slug = slugifyTitle(title) || "entry";
  return `${date}-${slug}`;
}

export function parseCsvList(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}
