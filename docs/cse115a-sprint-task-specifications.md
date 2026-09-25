# CSE 115A — Sprint Task Specifications

Fall 2026 · Section 01 and Section 02  
10 points per sprint. Submit at the end of every sprint.

## Overview

Every sprint, you write at least two of your own tasks in full, with six fields, before you implement them.

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

Copy this shape to `docs/tasks/sprint-N/<task id>.md`. Keep the front matter, the headings, and their order exactly. The files are read automatically.

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

1. Create the task and add it to your Scrum board. Most teams use a digital board such as GitHub Projects.
2. Branch from an up-to-date `main`: `git switch -c task/US-1-T-1`.
3. Commit the task file alone, message `US-1-T-1: task spec`.
4. Tag and push that commit before you implement: `git tag US-1-T-1-base && git push origin task/US-1-T-1 US-1-T-1-base`.
5. Implement the task and add its tests in later commits on the same branch. Do not weaken a test to make it pass.
6. Open a pull request titled `US-1-T-1: <title>`. A teammate reviews it. Merge when the team’s test command passes.
7. On the merge commit: `git tag US-1-T-1-done <merge commit> && git push origin US-1-T-1-done`.
8. Run Repo Metrics on the merged pull request.
   - Section 01: https://repo-metrics-dashboard.vercel.app/course/CSE115A-Fall26-S01/analyze
   - Section 02: https://repo-metrics-dashboard.vercel.app/course/CSE115A-Fall26-S02/analyze

   Sign in with GitHub, enter your team name, and select the team repository. In **Choose what to analyze**, open **Closed pull requests** and select this task’s pull request. That run scores the TypeScript and TSX files the pull request changed. The team name is for Repo Metrics only. It is not part of the Canvas submission.

## How to submit

Everything is due at the end of the sprint. Paste two merged pull-request links on Canvas, one per task.

On the repository, each task is on the Scrum board, the task file is committed before the implementation, the `<id>-base` and `<id>-done` tags are pushed, the tests pass on `main`, and Repo Metrics has been run on the merged pull request.

## Sprint Submission Checklist

Before submitting to Canvas, check **each of the following for both tasks**:

- [ ] The task is on the team's Scrum board.
- [ ] The task file is committed before any implementation code.
- [ ] The `<id>-base` tag is pushed.
- [ ] The task implementation and tests are committed.
- [ ] The pull request has been reviewed and merged.
- [ ] The `<id>-done` tag is pushed on the completed/merged commit.
- [ ] The task tests and existing tests pass on `main`.
- [ ] Repo Metrics has been run on the **merged pull request**.
- [ ] I have the link to the **merged pull request**.

## Canvas

Submit **two merged pull-request links**, one for each task:

1. Task 1: `<merged PR link>`
2. Task 2: `<merged PR link>`

**You do not need to submit the task files, Git tags, Scrum board, or Repo Metrics separately.**

## Grading

Each task is scored out of 10. Your sprint score is the average of your two best tasks. A missing task scores 0. The grader reads the task file and checks the merged pull request and the two tags.

| Criterion | Full credit | Partial | None | Pts |
|---|---|---|---|---|
| Scope — title, description, requirements | Specific outcome, clear out-of-scope, real constraints | Vague title or missing scope | Missing, or copied between fields | 1 |
| Specs | Observable behavior and edge cases; names every interface the tests use | Behavior stated, gaps remain | Describes implementation, or missing | 2 |
| Acceptance criteria | Every item pass/fail and checkable | Some items vague | Missing or not checkable | 2 |
| Tests section | Every criterion mapped to a test with setup and assertion | Some criteria unmapped | Names only, or missing | 1 |
| Test quality | Tests assert the criteria and fail without the implementation | Some weak or trivial assertions | Tests cannot fail | 1 |
| Tests pass | All task tests pass at `-done`; existing tests still pass | Some task tests still failing | Tests do not run, or missing | 2 |
| Process | Spec committed first, both tags pushed, Scrum board card present, merged PR link submitted | One step missing or late | Implementation committed before the task file | 1 |

Consent to the research, whether a task is later chosen for the benchmark, which AI tools you used, and how any AI tool performs on your task do not affect your grade.
