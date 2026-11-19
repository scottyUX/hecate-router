# Hecate Alpha architecture explorer

Five explanatory routes, implemented entirely with local content. All routes require
the existing password-based lab login and membership allowlist, checked on every
page render as well as through the session middleware. Search indexing is disabled.
The protected journal links to the explorer, and the explorer sidebar links back.

Routes:

- `/alpha`: training execution loop, with PPO shown as a black box.
- `/alpha/ppo`: actor, critic, rollout collection, rewards and PPO updates.
- `/alpha/runtime`: frozen policy serving loop.
- `/alpha/system`: component dictionary, candidate models and open decisions.
- `/alpha/roadmap`: build order and acceptance gates.

Click diagram nodes to inspect explanations, input/output contracts and applicable
formulas. The PPO Router node on the training page navigates to the detailed PPO
page. Dialogs close with Escape, the close button or a backdrop click; detail tabs
support left/right arrow keys. Diagrams scroll horizontally on small screens.

Run from `web/` with Node >= 20.9:

```sh
npm run dev -- --port 3105
```

This is an architecture explainer, not an experiment runner or a live Spark
control surface. It follows the Alpha engineering plan v0.2 and the November 18
planning discussion. Candidate model choices, checkpoint spacing and PPO settings
are explicitly distinguished from decisions. Reusing the E7 advisor requires
assessment validation and a task-overlap audit. The local compute-cost definition
and experiment decision rules remain open.

Content is in `components/alpha/content.ts`; interactive diagrams and dialogs are
in `components/alpha/explorer.tsx`. This feature adds no dependencies, changes no
existing pages and launches no training jobs.
