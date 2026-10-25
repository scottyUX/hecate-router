import type { ReactNode } from "react";

// Handoff design space: 2 directions x 3 modes, each a small flow drawing plus
// notes, and a side-by-side table. Rebuilt from the "Hecate Handoff Modes" diagram.

const C = {
  small: "#0f8a7e",
  smallSoft: "#d9f0ed",
  large: "#4b4fb8",
  largeSoft: "#e3e4f7",
  cost: "#c77712",
  costSoft: "#f7e6cc",
  kv: "#a23b72",
  kvSoft: "#f5dfeb",
  line: "#d5d9e2",
  muted: "#5d6577",
  fg: "#1a1f2b",
};

const MONO = "var(--font-ibm-plex-mono), ui-monospace, monospace";
const SANS = "var(--font-figtree), system-ui, sans-serif";

type Model = { size: "S" | "L"; name: string; ex: string };
type Mode = "verbatim" | "summary" | "kv";
type Cell = { tag: string; tone: "plain" | "cur" | "new"; notes: ReactNode[] };

const Num = ({ children }: { children: ReactNode }) => (
  <span className="font-mono tabular-nums">{children}</span>
);

const DIRECTIONS: {
  id: string;
  title: string;
  badge: string;
  intro: ReactNode;
  src: Model;
  tgt: Model;
  cells: Record<Mode, Cell>;
}[] = [
  {
    id: "s2l",
    title: "Small → Large",
    badge: "escalate · S→L",
    intro: (
      <>
        The weak model has been working and the policy decides to hand the run
        to the strong model. This is E7’s <b>escalate</b> action, and also what
        the K=3 router does when it sends a task to the strong model after
        reading 3 steps.
      </>
    ),
    src: { size: "S", name: "Small", ex: "Qwen3-14B" },
    tgt: { size: "L", name: "Large", ex: "Qwen3-32B" },
    cells: {
      verbatim: {
        tag: "E-full",
        tone: "plain",
        notes: [
          <><b>Cost:</b> the strong model re-prefills the whole trajectory at its own input price. Prefix caching can’t help, because the cache belongs to the other model.</>,
          <><b>Paper reference:</b> <Num>1,155 ms</Num> to re-prefill 8K tokens on 32B.</>,
          <><b>Use in Hecate:</b> the quality ceiling arm for escalation.</>,
        ],
      },
      summary: {
        tag: "E7 today",
        tone: "cur",
        notes: [
          <><b>Cost:</b> tiny, just the issue plus at most 400 summary tokens.</>,
          <><b>Risk:</b> the summary drops details the strong model needed, so it may re-explore the repo.</>,
          <><b>Use in Hecate:</b> E7’s escalate action, where the policy writes the summary.</>,
        ],
      },
      kv: {
        tag: "E-kv · new",
        tone: "new",
        notes: [
          <><b>Cost:</b> no prefill on the strong model, only the mapper’s matrix multiplies.</>,
          <><b>Paper:</b> 14B→32B keeps <Num>97.6%</Num> average accuracy; <Num>68 ms</Num> vs <Num>1,155 ms</Num> at 8K (17×), and 25× at 32K.</>,
          <><b>Use in Hecate:</b> E-full’s context at roughly E-sum’s cost, if it holds on agent runs.</>,
        ],
      },
    },
  },
  {
    id: "l2s",
    title: "Large → Small",
    badge: "hand down · L→S",
    intro: (
      <>
        A larger model passes context to a smaller one: the strong model hands
        back once the hard part is done, or a small advisor reads a larger
        model’s run. Cheaper for the receiver, but the paper’s evidence here is
        thinner.
      </>
    ),
    src: { size: "L", name: "Large", ex: "Qwen3-32B" },
    tgt: { size: "S", name: "Small", ex: "Qwen3-14B" },
    cells: {
      verbatim: {
        tag: "hand-down full",
        tone: "plain",
        notes: [
          <><b>Cost:</b> the small model re-prefills everything, but at a lower price per token.</>,
          <><b>Paper reference:</b> <Num>501 ms</Num> to re-prefill 8K tokens on 14B.</>,
          <><b>Use in Hecate:</b> the strong model plans, then the cheap model finishes.</>,
        ],
      },
      summary: {
        tag: "hand-down summary",
        tone: "plain",
        notes: [
          <><b>Cost:</b> cheapest possible handoff.</>,
          <><b>Risk:</b> the weaker model now also has less context, so this is the most likely combination to fail.</>,
          <><b>Use in Hecate:</b> the advisor’s view today, which sees only the last 5 actions, truncated.</>,
        ],
      },
      kv: {
        tag: "L→S mapper",
        tone: "new",
        notes: [
          <><b>Cost:</b> <Num>102 ms</Num> vs <Num>501 ms</Num> at 8K (5×), and 7× at 32K. Smaller gain, because the small model’s own prefill is already cheap.</>,
          <><b>Caution:</b> retention is weaker in this direction (Llama 70B→8B keeps 37% on HellaSwag, vs 94% for 8B→70B), and CoQA drift is <Num>0.33 pp/turn</Num>.</>,
          <><b>Use in Hecate:</b> an advisor that reads the full mapped cache instead of 5 truncated actions.</>,
        ],
      },
    },
  },
];

const MODES: [Mode, string][] = [
  ["verbatim", "1 · Verbatim context"],
  ["summary", "2 · Summary"],
  ["kv", "3 · KV cache transfer"],
];

const CY = 88;

function Label({
  x,
  y,
  children,
  anchor = "middle",
  size = 10,
  fill = C.muted,
}: {
  x: number;
  y: number;
  children: ReactNode;
  anchor?: "start" | "middle" | "end";
  size?: number;
  fill?: string;
}) {
  return (
    <text x={x} y={y} textAnchor={anchor} fontFamily={MONO} fontSize={size} fill={fill}>
      {children}
    </text>
  );
}

function ModelBox({ m, x, side }: { m: Model; x: number; side: "left" | "right" }) {
  const big = m.size === "L";
  const w = big ? 104 : 76;
  const h = big ? 84 : 56;
  const bx = side === "left" ? x : x - w;
  const stroke = big ? C.large : C.small;
  return (
    <g>
      <rect x={bx} y={CY - h / 2} width={w} height={h} rx={6} fill={big ? C.largeSoft : C.smallSoft} stroke={stroke} strokeWidth={1.6} />
      <text x={bx + w / 2} y={CY - 4} textAnchor="middle" fontFamily={SANS} fontSize={big ? 15 : 13} fontWeight={600} fill={stroke}>
        {m.name}
      </text>
      <Label x={bx + w / 2} y={CY + 13}>{m.ex}</Label>
    </g>
  );
}

function boxEdges(m: Model, x: number, side: "left" | "right") {
  const w = m.size === "L" ? 104 : 76;
  return side === "left" ? { l: x, r: x + w } : { l: x - w, r: x };
}

function Tape({ x, y, n, u, fill, stroke }: { x: number; y: number; n: number; u: number; fill: string; stroke?: string }) {
  return (
    <g>
      {Array.from({ length: n }, (_, i) => (
        <rect key={i} x={x + i * (u + 1.5)} y={y} width={u} height={12} rx={1.5} fill={fill} stroke={stroke ?? "none"} strokeWidth={1} />
      ))}
    </g>
  );
}

function Arrow({ x1, x2, y, color }: { x1: number; x2: number; y: number; color: string }) {
  return (
    <g>
      <line x1={x1} y1={y} x2={x2 - 6} y2={y} stroke={color} strokeWidth={1.6} />
      <path d={`M${x2 - 7},${y - 4.5} L${x2},${y} L${x2 - 7},${y + 4.5} Z`} fill={color} />
    </g>
  );
}

function Grid({ x, y }: { x: number; y: number }) {
  return (
    <g>
      {[0, 1, 2].flatMap((r) =>
        [0, 1, 2].map((c) => (
          <rect key={`${r}${c}`} x={x + c * 7} y={y + r * 7} width={5.5} height={5.5} rx={1} fill={C.kv} />
        ))
      )}
    </g>
  );
}

function Flow({ src, tgt, mode }: { src: Model; tgt: Model; mode: Mode }) {
  const s = boxEdges(src, 12, "left");
  const t = boxEdges(tgt, 368, "right");
  const mx = (s.r + t.l) / 2;
  return (
    <svg viewBox="0 0 380 228" role="img" aria-label={`${src.name} to ${tgt.name}, ${mode} handoff`} className="block h-auto w-full">
      <ModelBox m={src} x={12} side="left" />
      <ModelBox m={tgt} x={368} side="right" />
      <Label x={12} y={166} anchor="start">sender trajectory · T tokens</Label>
      <Tape x={12} y={172} n={12} u={6.5} fill={src.size === "L" ? C.large : C.small} />
      <Label x={368} y={166} anchor="end">receiver prefill</Label>
      {mode === "verbatim" ? (
        <g>
          <Tape x={368 - 12 * 8} y={172} n={12} u={6.5} fill={C.cost} />
          <Label x={mx} y={CY - 22}>full trajectory text</Label>
          <Arrow x1={s.r + 4} x2={mx - 54} y={CY} color={C.muted} />
          <Tape x={mx - 50} y={CY - 6} n={10} u={8.5} fill={C.costSoft} stroke={C.cost} />
          <Arrow x1={mx + 52} x2={t.l - 4} y={CY} color={C.muted} />
          <Label x={mx} y={CY + 24}>re-read: T tokens</Label>
          <Label x={12} y={212} anchor="start" size={11} fill={C.fg}>fidelity: lossless</Label>
          <Label x={368} y={212} anchor="end" size={11} fill={C.cost}>cost: high</Label>
        </g>
      ) : mode === "summary" ? (
        <g>
          <Tape x={368 - 2 * 8} y={172} n={2} u={6.5} fill={C.cost} />
          <Label x={mx} y={CY - 22}>summary</Label>
          <path d={`M${s.r + 6},${CY - 12} L${mx - 26},${CY - 7} L${mx - 26},${CY + 7} L${s.r + 6},${CY + 12} Z`} fill={C.line} />
          <rect x={mx - 26} y={CY - 9} width={52} height={18} rx={3} fill={C.costSoft} stroke={C.cost} strokeWidth={1} />
          <Label x={mx} y={CY + 4} fill={C.fg}>≤400 tok</Label>
          <Arrow x1={mx + 28} x2={t.l - 4} y={CY} color={C.muted} />
          <Label x={mx} y={CY + 26}>+ issue text</Label>
          <Label x={12} y={212} anchor="start" size={11} fill={C.fg}>fidelity: lossy</Label>
          <Label x={368} y={212} anchor="end" size={11} fill={C.cost}>cost: low</Label>
        </g>
      ) : (
        <g>
          <Label x={368} y={184} anchor="end" size={10.5} fill={C.kv}>0 · decode starts</Label>
          <Grid x={s.r + 10} y={CY - 10} />
          <Arrow x1={s.r + 32} x2={mx - 26} y={CY} color={C.kv} />
          <rect x={mx - 26} y={CY - 17} width={52} height={34} rx={4} fill={C.kvSoft} stroke={C.kv} strokeWidth={1.4} />
          <Label x={mx} y={CY - 2} fill={C.fg}>mapper</Label>
          <Label x={mx} y={CY + 10} size={8.5}>W per head</Label>
          <Arrow x1={mx + 26} x2={t.l - 30} y={CY} color={C.kv} />
          <Grid x={t.l - 28} y={CY - 10} />
          <Label x={s.r + 20} y={CY - 20}>KV</Label>
          <Label x={t.l - 18} y={CY - 20}>KV′</Label>
          <Label x={190} y={CY + 56}>strip RoPE → ridge → re-apply RoPE</Label>
          <Label x={12} y={212} anchor="start" size={11} fill={C.fg}>fidelity: near-lossless (mapper error)</Label>
          <Label x={368} y={212} anchor="end" size={11} fill={C.kv}>cost: ~0</Label>
        </g>
      )}
    </svg>
  );
}

const TAG_BG = { plain: C.costSoft, cur: C.largeSoft, new: C.kvSoft };

function Legend() {
  const items: [string, string][] = [
    [C.small, "Small model"],
    [C.large, "Large model"],
    [C.cost, "Tokens the receiver must prefill (cost)"],
    [C.kv, "KV cache / mapper"],
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 font-sans text-[13px] text-[var(--paper-muted)]">
      {items.map(([color, text]) => (
        <span key={text} className="inline-flex items-center gap-1.5">
          <i className="inline-block size-3 rounded-[2px]" style={{ background: color }} />
          {text}
        </span>
      ))}
    </div>
  );
}

export function HandoffModesFigure() {
  return (
    <figure id="figure-handoff" className="my-6 space-y-6 font-sans">
      <Legend />
      {DIRECTIONS.map((d) => (
        <section key={d.id} className="space-y-3">
          <div>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h3 className="text-lg font-semibold text-[var(--paper-ink)]">{d.title}</h3>
              <span className="rounded border border-[var(--paper-line)] px-2 py-0.5 font-mono text-[12px]">
                {d.badge}
              </span>
            </div>
            <p className="mt-1 text-[14px] leading-[1.5] text-[var(--paper-muted)]">{d.intro}</p>
          </div>
          <div className="space-y-3">
            {MODES.map(([mode, title]) => {
              const cell = d.cells[mode];
              return (
                <article
                  key={mode}
                  className="grid gap-3 rounded-md border border-[var(--paper-line)] bg-white p-3.5 md:grid-cols-[minmax(0,380px)_minmax(0,1fr)]"
                >
                  <Flow src={d.src} tgt={d.tgt} mode={mode} />
                  <div className="min-w-0 space-y-2">
                    <header className="flex flex-wrap items-baseline justify-between gap-2">
                      <h4 className="text-[15px] font-semibold text-[var(--paper-ink)]">{title}</h4>
                      <span
                        className="rounded-full px-2 py-px font-mono text-[11.5px] text-[var(--paper-ink)]"
                        style={{ background: TAG_BG[cell.tone] }}
                      >
                        {cell.tag}
                      </span>
                    </header>
                    <ul className="list-disc space-y-1 pl-4 text-[13.5px] leading-[1.45] text-[var(--paper-muted)] [&_b]:font-semibold [&_b]:text-[var(--paper-ink)]">
                      {cell.notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      ))}
      <figcaption className="text-[13px] leading-[1.45] text-[var(--paper-muted)]">
        Figure 1. Three ways to hand a run between models, in both directions.
        The receiver needs the context so far: it can re-read the trajectory as
        text, read a short summary, or receive the sender’s KV cache mapped
        into its own format. Model pairs and numbers are the paper’s (Qwen3
        14B↔32B; latency at 8K tokens on H100). E8 tests the small → large row
        with Qwen3-8B → Qwen3-14B.
      </figcaption>
    </figure>
  );
}
