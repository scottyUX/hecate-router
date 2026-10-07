# CSE 115A — Sprint Task Specifications

Fall 2026 · Section 01 and Section 02  
10 points per sprint. Submit at the end of every sprint in the [Repo Metrics app](https://cse115a-repo-metrics-production.up.railway.app/cse115a).

## Overview

Every sprint, you write two of your own tasks in full, with six fields, before you implement them.

You already break user stories into tasks in the sprint plan.

You practice splitting a story into a slice one person can finish in 2–3 days, writing pass/fail acceptance criteria, writing a test for each criterion, and leaving a git history that shows where the work started and ended.

AI coding tools are allowed under the course AI policy. You are responsible for everything you commit. You must be able to explain your code.

## Requirements

You own at least two tasks each sprint. Each task must meet all of these:

- You are the only assignee. You write the task file (you will discuss and clarify it with your team members), the tests, and the implementation. Teammates may review. They do not commit to your task branch.
- Your two tasks are different slices. A revision, rename, or follow-up fix of the first is not a second task.
- Estimated at 2 hours or more, and it changes behavior a user or another part of the system can observe.
- One person can finish it in 2–3 days.
- The task file is created before any implementation code.
- Every acceptance criterion has at least one committed test.

## Task structure

| Field | Its job | What to write |
|---|---|---|
| Title | Names the outcome | A verb and a specific result. “Reject a non-university email on login.” |
| Description | Gives context and scope | What this slice does, which story it serves, and what is out of scope. |
| Specs | Defines observable behavior | Inputs, outputs, states, and edge cases. Name every endpoint, function, file, or UI element your tests touch. |
| Requirements | Sets constraints | Data rules, auth, code that must stay intact, libraries you must use or avoid. |
| Acceptance criteria | Defines done | A numbered pass/fail list. Each item is one outcome a reviewer can check. |
| Tests | Proves each criterion | Per test: file, test name, setup, what it asserts, and which criterion it covers. |

We will cover all of these concepts in lecture. If you are not sure how to write these sections, talk to your team and your TAs.

## Worked example

Copy this shape to `docs/tasks/sprint-N/<task id>.md`, where `N` is the sprint number (for example `docs/tasks/sprint-1/US-1-T-1.md`). The `sprint:` field in the front matter must match. Keep the front matter, the headings, and their order exactly. The files are read automatically.

The task id (for example `US-1-T-1`) stays on the task: in the front matter, the filename, the branch, the tags, the test names, and the pull-request title. You do not submit the id separately.

```markdown
---
id: US-1-T-1
story: US-1
sprint: 1
assignee: A. Student
estimate_hours: 3
---

# Reject a non-university email on login

## Description
Serves US-1 (log in with a university email). This task covers the rejection path only. Successful login (US-1-T-2) and session persistence (US-1-T-3) are out of scope.

## Specs
- `POST /api/login` with `{ "email": "student@gmail.com" }` returns HTTP 400 and `{ "error": "Use your university email" }`.
- On rejection, the response sets no session cookie and the user stays signed out.
- A university email ends in `@ucsc.edu` (case-insensitive). `student@UCSC.EDU` is valid. `student@ucsc.edu.evil.com` is not.
- The check runs in the existing login handler, before any database lookup.

## Requirements
- Use the existing login handler. Do not add a second user table.
- No new runtime dependencies.
- Existing login tests must keep passing.

## Acceptance criteria
1. A non-university email is rejected with HTTP 400 and the message "Use your university email".
2. No session cookie is set on rejection.
3. A `@ucsc.edu` email, in any letter case, is not rejected by this check.
4. A lookalike domain such as `ucsc.edu.evil.com` is rejected.

## Tests
File: `tests/US-1-T-1_login_email` (use your framework’s extension)
Setup for all: start the app with an empty user store and send requests to `/api/login`.

| Test name | Setup | Asserts | Criterion |
|---|---|---|---|
| US-1-T-1 rejects a non-university email | POST `student@gmail.com` | status 400; error is "Use your university email" | 1 |
| US-1-T-1 sets no session cookie on rejection | same request | no `Set-Cookie` header | 2 |
| US-1-T-1 does not reject a ucsc.edu email in any case | POST `student@ucsc.edu`, then `student@UCSC.EDU` | status is not 400 for either | 3 |
| US-1-T-1 rejects a lookalike domain | POST `student@ucsc.edu.evil.com` | status 400 | 4 |
```

## Workflow

Steps below use `US-1-T-1` (User Story 1, Task 1) as the example task id, swap in your own.

**1. Create the task**
- Write the task file at `docs/tasks/sprint-1/US-1-T-1.md` (use your sprint number, not the letter `N`).
- Add a card for it to your Scrum board (e.g. GitHub Projects).

**2. Branch from an up-to-date `main`:**

`git switch -c task/US-1-T-1`.

**3. Commit the task file alone**
```bash
git add docs/tasks/sprint-1/US-1-T-1.md
git commit -m "US-1-T-1: task spec"
```
- No implementation code in this commit, spec only.

**4. Tag and push the spec commit, before writing any code**
```bash
git tag US-1-T-1-base
git push origin task/US-1-T-1 US-1-T-1-base
```
- This commit must stay the first commit on the branch. Do not rebase, amend, or force-push it after tagging.
- If this commit isn't first, or you changed it after tagging, see [Fixing mistakes](#fixing-mistakes).

**5. Implement**
- Add the implementation and its tests on the same branch.
- Do not weaken a test to make it pass.

**6. Open a pull request**
- Open it from your own GitHub account.
- Title: `US-1-T-1: <title>`.
- The PR changes only this task's file under `docs/tasks/`. One task file per PR.
- A teammate reviews it.
- Before merging, check that your task spec is the first commit on the branch:
  ```bash
  git fetch origin
  git log --oneline --reverse origin/main..
  ```
  The first line should be your task spec commit. If it isn't, see [Fixing mistakes](#fixing-mistakes) before you merge.
- Merge once the team's test command passes, using **Merge pull request** (a merge commit). Do not use **Squash and merge** or **Rebase and merge**. Both rewrite your commits, so the spec commit and its `-base` tag no longer appear on `main`, and the Process check fails. GitHub remembers your last choice, so check the button label before clicking.

**7. Tag the merge commit**

Find the merge commit on the pull request page ("merged commit `abc1234` into main"), or with the GitHub CLI: `gh pr view <PR number> --json mergeCommit -q .mergeCommit.oid`.
```bash
git fetch origin
git tag US-1-T-1-done <merge commit sha>
git push origin US-1-T-1-done
```

**8. Add the task in the Repo Metrics app**
- Push the `-done` tag first. The app checks the tags when you add the PR.
- See [How to submit](#how-to-submit).

## How to submit

Submit in the [Repo Metrics app](https://cse115a-repo-metrics-production.up.railway.app/cse115a). This is the submission that is graded. Repo Metrics runs automatically on each pull request you add.

**First time only**
1. Sign in with your UCSC Google account.
2. Enter the course code from your instructor.
3. Connect GitHub. If your team repository belongs to a GitHub organization, click **Grant** next to that organization on the GitHub screen, or the app cannot read your pull requests.

**Every sprint**
1. Open **Assignment N**, where `N` is the sprint number.
2. In **Task 1**, paste the first merged pull-request link and press **Submit task**. Keep the tab open while the analysis runs.
3. Do the same in **Task 2** for your second task.
4. Read the checks under each task. A check marked for review can cost the Process point. To re-check a task after fixing it (for example, after pushing a missing tag), paste the same link again and press the button under it.
5. When both tasks are analyzed, press **Submit Assignment N**. You can submit once. After that, both tasks are locked.

Your grade appears in the app after an instructor reviews it.

## Sprint Submission Checklist

Before pressing **Submit Assignment N**, check **each of the following for both tasks**:

- [ ] The task is on the team's Scrum board.
- [ ] The task file was committed alone, before any implementation code.
- [ ] The `<id>-base` tag is pushed on that commit.
- [ ] The implementation and tests are committed on the task branch.
- [ ] The pull request was opened from your account, reviewed, and merged.
- [ ] The `<id>-done` tag is pushed on the merge commit.
- [ ] The task tests and existing tests pass on `main`.
- [ ] The task is added in the Repo Metrics app and its checks have no items to review.

## Fixing mistakes

These steps cover two mistakes: your task spec isn't the first commit on the branch, or you amended, rebased, or force-pushed it after tagging.

**If your PR is not yet merged:** don't edit or delete files on that branch. Commits added later don't change which commit is first. Instead:

1. Copy your task file, code, and tests somewhere outside the repo.
2. Start a new branch from an up-to-date `main`:
   ```bash
   git switch main
   git pull
   git switch -c task/US-1-T-1-v2
   ```
3. Copy your task file back, commit it alone, and move the base tag to it:
   ```bash
   git add docs/tasks/sprint-1/US-1-T-1.md
   git commit -m "US-1-T-1: task spec"
   git tag -d US-1-T-1-base
   git push origin :refs/tags/US-1-T-1-base
   git tag US-1-T-1-base
   git push origin task/US-1-T-1-v2 US-1-T-1-base
   ```
4. Copy your code and tests back, commit, push, and open a new pull request. Close the old one.
5. Optional: delete the old branch with `git push origin --delete task/US-1-T-1`.

**If your PR is already merged:** submit the task anyway. You lose the Process point (1 of 10), but everything else is graded normally. Do not delete and re-add files to rewrite the history.

If you're unsure, ask a TA before changing anything.

## Canvas

Canvas is only for the Repo Metrics write-up. Do not submit pull-request links there.

For each sprint, write **one paragraph** that:
* briefly describes what your task implemented
* identifies the two Repo Metrics metrics you selected (from the task's **View results** page in the app)
* reports the results for those two metrics
* compares the two metrics and explains what they show about your task.

**You do not need to submit the task files, Git tags, or Scrum board separately.**

## Grading

Each task is scored out of 10. Your sprint score is the average of your two tasks. A missing task scores 0. The grader reads the task file and checks the merged pull request, and the two tags. An instructor reviews every grade before you see it.

| Criterion | Full credit | Partial | None | Pts |
|---|---|---|---|---|
| Scope — title, description, requirements | Specific outcome, clear out-of-scope, real constraints | Vague title or missing scope | Missing, or copied between fields | 1 |
| Specs | Observable behavior and edge cases; names every interface the tests use | Behavior stated, gaps remain | Describes implementation, or missing | 2 |
| Acceptance criteria | Every item pass/fail and checkable | Some items vague | Missing or not checkable | 2 |
| Tests section | Every criterion mapped to a test with setup and assertion | Some criteria unmapped | Names only, or missing | 1 |
| Test quality | Tests assert the criteria and fail without the implementation | Some weak or trivial assertions | Tests cannot fail | 1 |
| Tests pass | All task tests pass at `-done`; existing tests still pass | Some task tests still failing | Tests do not run, or missing | 2 |
| Process | Spec committed first, both tags pushed, Scrum board card present, both tasks submitted in the app | One step missing or late | Implementation committed before the task file | 1 |

Consent to the research, whether a task is later chosen for the benchmark, which AI tools you used, and how any AI tool performs on your task do not affect your grade.
