# Hecate — GitHub Project Board Setup

Manual fallback if `gh auth refresh -s project` has not been completed.

## 1. Authorize GitHub Projects scope

```bash
gh auth refresh -h github.com -s project
```

Complete the device flow in your browser, then run:

```bash
bash scripts/setup_project.sh
```

## 2. Manual board setup (if CLI fails)

1. Open https://github.com/users/scottyUX/projects
2. **New project** → Board → Title: **Hecate — Stage 1**
3. Link repository: `scottyUX/hecate`
4. Edit **Status** field options to:
   - Backlog → Ready → In progress → Review → Done
5. **Add items** → search and add issues #1–#20

## 3. Column mapping

| Status | Use |
|--------|-----|
| Backlog | All new issues (default) |
| Ready | Scoped and unblocked |
| In progress | Active work |
| Review | PR open or awaiting review |
| Done | Merged or completed |

## 4. Milestones (already created)

- M0 — Project setup (S1–S4)
- M1 — Pilot (20 tasks) — **day-2 go/no-go gate**
- M2 — Full sweep (1,200 patches)
- M3–M6 — Downstream epics (E-M3–E-M6)

## 5. Issue index

| ID | Issue | Milestone |
|----|-------|-----------|
| S1 | #1 Initialize repository | M0 |
| S2 | #2 Environment & dependencies | M0 |
| S3 | #3 Data loading & canonical schema | M0 |
| S4 | #4 Confirm model slugs & pricing | M0 |
| S5 | #5 Oracle/BM25 context builder | M1 |
| S6 | #6 Prompt template | M1 |
| S7 | #7 OpenRouter client wrapper | M1 |
| S8 | #8 Patch extraction & normalization | M1 |
| S9 | #9 Caching layer | M1 |
| S10 | #10 Cost tracker & budget guard | M1 |
| S11 | #11 Generation runner | M1 |
| S12 | #12 Run the pilot | M1 |
| S13 | #13 Pilot report & go/no-go | M1 |
| S14 | #14 Full generation sweep | M2 |
| S15 | #15 Output validation | M2 |
| S16 | #16 Stage-1 handoff artifact | M2 |
| E-M3 | #17 Execution & labels (epic) | M3 |
| E-M4 | #18 Router training (epic) | M4 |
| E-M5 | #19 Evaluation (epic) | M5 |
| E-M6 | #20 SDLC adaptation (epic) | M6 |
