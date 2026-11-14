/**
 * Cost of each routing policy on the leave-django-out holdout (231 tasks).
 * Recorded per-instance API costs from the 2 Aug 2025 submissions, as in
 * experiments/e06-generalist-k1/results.md (Q6.1 table). Drawn on a dark surface.
 */
const policies = [
  {
    label: "Always the frontier model",
    frontier: 231,
    fixes: 163,
    cost: 260.72,
    note: "The default most teams run",
  },
  {
    label: "Best learned router so far",
    frontier: 229,
    fixes: 163,
    cost: 259.4,
    note: "Generalist router at λ=0.59: saves $1.32 (0.5%)",
    highlight: true,
  },
  {
    label: "Perfect routing, most fixes",
    frontier: 38,
    fixes: 172,
    cost: 82.01,
    note: "Hindsight: frontier only where the cheap model fails and it wins",
  },
  {
    label: "Perfect routing, frontier quality",
    frontier: 29,
    fixes: 163,
    cost: 62.43,
    note: "Hindsight: cheapest mix that still fixes 163",
  },
  {
    label: "Always the cheap model",
    frontier: 0,
    fixes: 134,
    cost: 39.28,
    note: "Cheapest, but 29 fewer fixes than the frontier model",
  },
] as const;

const max = Math.max(...policies.map((p) => p.cost));

export function CostHeadroomChart() {
  return (
    <figure className="mt-12" aria-labelledby="headroom-chart-title">
      <figcaption
        id="headroom-chart-title"
        className="flex flex-wrap items-baseline justify-between gap-2 border-t border-white/20 pt-4"
      >
        <span className="text-sm font-semibold text-white">
          API cost on 231 held-out tasks
        </span>
        <span className="text-xs text-[var(--hc-faint)]">
          Fixes = tasks whose patch passes the hidden tests
        </span>
      </figcaption>

      <ul className="mt-6 space-y-5">
        {policies.map((p) => {
          const pct = (p.cost / max) * 100;
          const highlight = "highlight" in p && p.highlight;
          return (
            <li
              key={p.label}
              tabIndex={0}
              className="group relative grid gap-2 outline-none md:grid-cols-[15rem_1fr] md:items-center md:gap-6"
            >
              <div className="text-sm leading-snug">
                <p className={highlight ? "font-semibold text-white" : "text-white/85"}>
                  {p.label}
                </p>
                <p className="text-xs text-[var(--hc-faint)]">
                  {p.fixes} fixes · {p.frontier} frontier calls
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="relative h-6 flex-1">
                  <div
                    className={`h-full rounded-r-[4px] transition-opacity group-hover:opacity-80 group-focus-visible:opacity-80 ${
                      highlight ? "bg-[var(--hc-accent)]" : "bg-[#6b6b6b]"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-sm font-semibold text-white tabular-nums">
                  ${p.cost.toFixed(2)}
                </span>
              </div>
              <div
                role="tooltip"
                className="pointer-events-none absolute -top-2 right-20 z-10 hidden -translate-y-full rounded-sm bg-[var(--hc-bg)] px-3 py-2 text-xs text-[var(--hc-ink)] shadow-lg group-hover:block group-focus-visible:block"
              >
                <p className="font-semibold">{p.label}</p>
                <p className="mt-0.5 text-[var(--hc-body)]">{p.note}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
