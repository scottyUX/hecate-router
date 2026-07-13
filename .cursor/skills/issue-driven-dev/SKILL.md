---
name: issue-driven-dev
description: Implement work from a tracked issue by reading Scope, Done when, and constraints, then verifying completion. Use when the user asks to work on an issue, ticket, backlog item, or GitHub issue number.
---

# Issue-driven development

## Workflow

1. **Load the issue** with `gh issue view <N> --json title,body,state,labels,comments` (or the tracker equivalent).
2. Extract and restate:
   - **Scope** — what to build
   - **Done when** — acceptance criteria
   - **Constraints / invariants** — what must not change
   - **Dependencies** — blockers that must already be done
3. If dependencies are open, stop and report that before coding.
4. Implement **only** the Scope. Do not pull in adjacent tickets.
5. Map each acceptance criterion to evidence (file, test, or command output).
6. When done, summarize:
   - What changed
   - How “Done when” is satisfied
   - Whether the issue is ready to close (ask before closing unless the user already said to close it)

## Checklist

```
- [ ] Issue loaded and acceptance criteria listed
- [ ] Dependencies confirmed done or unblocked
- [ ] Implementation stays within Scope
- [ ] Acceptance criteria verified with evidence
- [ ] Close/commit/PR only if the user asked
```

## Anti-patterns

- Coding from the title alone without reading the body
- “While we’re here” changes from other issues
- Closing an issue without checking Done when
