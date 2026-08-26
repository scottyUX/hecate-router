"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  JOURNAL_COMPONENTS,
  JOURNAL_STATUSES,
  JOURNAL_VISIBILITIES,
  makeEntryId,
  type JournalEntry,
} from "@/lib/journal";

type Props = {
  action: (formData: FormData) => Promise<void>;
  initial?: Partial<JournalEntry>;
  submitLabel: string;
};

export function JournalEntryForm({ action, initial, submitLabel }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [title, setTitle] = useState(initial?.title ?? "");
  const [date, setDate] = useState(initial?.date ?? today);
  const [entryId, setEntryId] = useState(initial?.entry_id ?? "");
  const [entryIdTouched, setEntryIdTouched] = useState(Boolean(initial?.entry_id));
  const [selectedComponents, setSelectedComponents] = useState<string[]>(
    initial?.component ?? []
  );

  const suggestedId = useMemo(
    () => makeEntryId(date, title || "entry"),
    [date, title]
  );

  const toggleComponent = (value: string) => {
    setSelectedComponents((prev) =>
      prev.includes(value) ? prev.filter((c) => c !== value) : [...prev, value]
    );
  };

  return (
    <form action={action} className="space-y-8">
      <section className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            name="title"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (!entryIdTouched) setEntryId(makeEntryId(date, e.target.value));
            }}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="date">Date</Label>
          <Input
            id="date"
            name="date"
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              if (!entryIdTouched) setEntryId(makeEntryId(e.target.value, title));
            }}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="entry_id">Entry ID</Label>
          <Input
            id="entry_id"
            name="entry_id"
            value={entryId || suggestedId}
            onChange={(e) => {
              setEntryIdTouched(true);
              setEntryId(e.target.value);
            }}
            required
          />
          <p className="text-xs text-muted-foreground">
            Stable reference for related_entries. Suggested: {suggestedId}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="status">Status</Label>
          <select
            id="status"
            name="status"
            defaultValue={initial?.status ?? "in-progress"}
            className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
          >
            {JOURNAL_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="visibility">Visibility</Label>
          <select
            id="visibility"
            name="visibility"
            defaultValue={initial?.visibility ?? "public"}
            className="h-9 w-full rounded-lg border border-input bg-background px-3 text-sm"
          >
            <option value="public">Lab (all members)</option>
            <option value="private">Author only</option>
          </select>
          <p className="text-xs text-muted-foreground">
            Lab journal entries are shared with every allowlisted member by
            default.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="commit">Commit</Label>
          <Input
            id="commit"
            name="commit"
            defaultValue={initial?.commit ?? ""}
            placeholder="git hash"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="tags">Tags</Label>
          <Input
            id="tags"
            name="tags"
            defaultValue={(initial?.tags ?? []).join(", ")}
            placeholder="hyperparameter-sweep, ablation"
          />
        </div>

        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="related_entries">Related entries</Label>
          <Input
            id="related_entries"
            name="related_entries"
            defaultValue={(initial?.related_entries ?? []).join(", ")}
            placeholder="2026-07-08-feature-vector-v2"
          />
        </div>

        <div className="space-y-3 md:col-span-2">
          <Label>Component</Label>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {JOURNAL_COMPONENTS.map((component) => (
              <label
                key={component}
                className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm"
              >
                <input
                  type="checkbox"
                  name="component"
                  value={component}
                  checked={selectedComponents.includes(component)}
                  onChange={() => toggleComponent(component)}
                />
                {component}
              </label>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        {(
          [
            ["context", "Context", initial?.context],
            ["method", "Method / What I did", initial?.method],
            ["result", "Result", initial?.result],
            ["interpretation", "Interpretation", initial?.interpretation],
            ["next_steps", "Next", initial?.next_steps],
            ["notes", "Notes", initial?.notes],
          ] as const
        ).map(([name, label, value]) => (
          <div key={name} className="space-y-2">
            <Label htmlFor={name}>{label}</Label>
            <Textarea
              id={name}
              name={name}
              defaultValue={value ?? ""}
              rows={5}
              className="min-h-28"
            />
          </div>
        ))}
      </section>

      <Button type="submit">{submitLabel}</Button>
    </form>
  );
}
