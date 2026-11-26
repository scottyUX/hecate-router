"""KV Cache Hit For Accuracy — Gradio UI for the cache-conditioned continuation demo.

Run:  python demos/kv_cache_continuation/app.py   →  http://127.0.0.1:7860
The design sentence's KV cache is kept in memory (nothing written to disk) and shown on the page.
"""
from __future__ import annotations

import html
import math
import os
import sys

import gradio as gr
from transformers import AutoConfig

sys.path.insert(0, os.path.dirname(__file__))
from kvdemo import DEFAULT_MODEL, DEFAULT_SENTENCE, KVCacheDemo, TestResult, default_partials, layer_kv  # noqa: E402

MODEL_NAME = os.environ.get("KVDEMO_MODEL", DEFAULT_MODEL)
_CFG = AutoConfig.from_pretrained(MODEL_NAME)
N_LAYERS = _CFG.num_hidden_layers
N_KV_HEADS = getattr(_CFG, "num_key_value_heads", _CFG.num_attention_heads)
HEAD_DIM = getattr(_CFG, "head_dim", None) or _CFG.hidden_size // _CFG.num_attention_heads

TITLE = "KV Cache Hit For Accuracy"
DEMO: KVCacheDemo | None = None


def get_demo() -> KVCacheDemo:
    global DEMO
    if DEMO is None:
        DEMO = KVCacheDemo(MODEL_NAME)
    return DEMO


def esc(s: str) -> str:
    """Escape, and make leading/whitespace-only tokens visible (␣)."""
    return html.escape(s).replace(" ", "␣") if s.strip() == "" or s.startswith(" ") else html.escape(s)


def pct(x: float) -> str:
    return "—" if x != x else f"{x:.1%}"


# ----------------------------------------------------------------------------- styling
CSS = """
/* everything we render: black on white, regardless of Gradio theme */
.kv, .hero, .cachecard {background:#ffffff !important; font-family: ui-sans-serif, system-ui, sans-serif;
  font-size:14px; line-height:1.5; border-radius:12px}
.kv, .kv *, .hero, .hero *, .cachecard, .cachecard * {color:#000000 !important}
.kv {padding:14px}
.kv h3 {margin:18px 0 6px; font-size:16px}
.kv table, .cachecard table {border-collapse:collapse; font-size:13px; margin:6px 0 12px}
.kv th, .kv td, .cachecard th, .cachecard td {border:1px solid #9ca3af !important; padding:3px 8px; text-align:right; background:#fff !important}
.kv th, .cachecard th {background:#e5e7eb !important; font-weight:700}
.kv td.l, .kv th.l, .cachecard td.l, .cachecard th.l {text-align:left}
.kv .chip {display:inline-block; margin:2px 1px; padding:2px 5px; border-radius:5px; font-family:ui-monospace,monospace; font-size:12px; white-space:pre}
.kv .chip.c {background:#bfdbfe !important} .kv .chip.a {background:#fde68a !important}
.kv .chip.g {background:#bbf7d0 !important} .kv .chip.x {background:#fecaca !important}
.kv .ok, .kv .ok * {color:#166534 !important; font-weight:700} .kv .bad, .kv .bad * {color:#b91c1c !important; font-weight:700}
.kv .formula {font-family:ui-monospace,monospace; background:#f3f4f6 !important; border-left:3px solid #4f46e5;
  padding:8px 12px; margin:6px 0; white-space:pre-wrap; font-size:12.5px}
.kv details {margin:4px 0; border:1px solid #e5e7eb; border-radius:8px; padding:4px 10px}
.kv summary {cursor:pointer; font-weight:600}
.kv .bar {display:inline-block; height:9px; background:#4f46e5 !important; vertical-align:middle; border-radius:2px}
.kv .sub {font-size:13px}
.kv .testcard {border:1px solid #d1d5db; border-radius:10px; padding:4px 14px 10px; margin:12px 0}

/* header / abstract */
.hero {padding:22px 24px; border:1px solid #d1d5db}
.hero h1 {font-size:26px; margin:0 0 2px; letter-spacing:-0.01em}
.hero .tag {font-size:13px; margin-bottom:16px}
.hero .steps {display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px}
.hero .step {border:1px solid #d1d5db; border-radius:10px; padding:12px 14px; background:#f9fafb !important}
.hero .num {display:inline-flex; width:26px; height:26px; border-radius:50%; align-items:center; justify-content:center;
  background:#4f46e5 !important; color:#ffffff !important; font-weight:700; font-size:13px; margin-bottom:6px}
.hero .step b {display:block; margin-bottom:2px}
.hero .caveat {margin-top:14px; border-left:4px solid #d97706; background:#fffbeb !important; padding:10px 14px; border-radius:6px}

/* cache status */
.cachecard {padding:12px 16px; border:1px solid #d1d5db}
.cachecard .badge {display:inline-block; padding:2px 10px; border-radius:999px; font-weight:700; font-size:12px; margin-right:8px}
.cachecard .hit {background:#bbf7d0 !important} .cachecard .miss {background:#bfdbfe !important}
.cachecard .idle {background:#e5e7eb !important}
.cachecard code {font-family:ui-monospace,monospace; font-size:12px; background:#f3f4f6 !important; padding:1px 4px; border-radius:4px}
.cachecard tr.cur td {background:#eef2ff !important; font-weight:600}

/* KV tensor heatmaps */
.kv table.heat td {font-family:ui-monospace,monospace; font-size:11px; padding:2px 5px; min-width:38px}
.kv table.heat th {font-size:11px; padding:2px 5px}
"""

HERO = f"""
<div class="hero">
  <h1>{TITLE}</h1>
  <div class="tag">Cache-conditioned continuation · Experiment A · {DEFAULT_MODEL} on CPU · real transformer KV cache</div>
  <div class="steps">
    <div class="step"><span class="num">1</span><b>Prefill once</b>
      The design sentence is prefilled once into the KV cache, kept in memory and shown in the
      <b>KV Cache</b> tab. Edit the sentence and a new cache is stored.</div>
    <div class="step"><span class="num">2</span><b>Append to a fresh copy</b>
      Each partial prompt (one per line; a blank line = empty test) is appended to a fresh copy of that cache,
      so tests never contaminate each other.</div>
    <div class="step"><span class="num">3</span><b>Score &amp; decode</b>
      The model is scored on the expected continuation (rest of the sentence) and also decodes greedily.</div>
  </div>
  <div class="caveat"><b>Caveat.</b> The partial prompt is appended <i>after</i> the full cached sentence, so this measures
    <b>recall-from-context</b>, not ordinary prefix reconstruction.</div>
</div>
"""


# ----------------------------------------------------------------------------- cache status
def cache_html(info: dict | None, message: str = "") -> str:
    demo = DEMO
    head = ""
    if info:
        m = info["meta"]
        badge = ('<span class="badge hit">CACHE HIT</span>reused the stored cache — no prefill needed'
                 if info["hit"] else
                 '<span class="badge miss">CACHE MISS</span>prefilled and stored in memory (new or changed sentence)')
        head = f"""<div>{badge} · {info['seconds'] * 1000:.0f} ms</div>
<div style="margin-top:6px">Key <code>{info['key']}</code> · {m.get('bytes', 0) / 1e6:.2f} MB of K+V tensors ·
see the <b>KV Cache</b> tab for the values<br>Cached tokens ({m['n_tokens']}): {html.escape(' | '.join(m['tokens']))}<br>
Shape: {html.escape(m['shape'])}</div>"""
    elif message:
        head = f'<div><span class="badge idle">CACHE</span>{html.escape(message)}</div>'
    rows = ""
    if demo is not None:
        cur = info["key"] if info else None
        for e in demo.store.list():
            rows += (f"<tr class='{'cur' if e.get('key') == cur else ''}'><td class='l'><code>{e.get('key')}</code></td>"
                     f"<td class='l'>{html.escape(e.get('sentence', ''))}</td><td>{e.get('n_tokens')}</td>"
                     f"<td>{e.get('bytes', 0) / 1e6:.2f} MB</td><td>{e.get('created', '')}</td></tr>")
    table = (f"<div style='margin-top:10px'><b>Caches stored this session (in memory)</b></div><table><tr><th class='l'>key</th>"
             f"<th class='l'>design sentence</th><th>tokens</th><th>size</th><th>saved</th></tr>{rows}</table>") if rows else ""
    return f'<div class="cachecard">{head}{table}</div>'


def ensure_cache(sentence: str, layer, kind, head, ndims, progress=gr.Progress()):
    progress(0, desc="Loading model / KV cache…")
    try:
        *_, info = get_demo().get_or_build_cache(sentence.strip() or DEFAULT_SENTENCE)
    except ValueError as e:
        return cache_html(None, str(e)), None, kv_view_html(None, layer, kind, head, ndims)
    return cache_html(info), info["key"], kv_view_html(info["key"], layer, kind, head, ndims)


# ----------------------------------------------------------------------------- KV cache tab
def _shade(x: float, scale: float, diverging: bool) -> str:
    a = min(abs(x) / scale, 1.0) * 0.6 if scale > 0 else 0.0
    if not diverging:
        return f"background:rgba(79,70,229,{a:.2f}) !important"
    rgb = "220,38,38" if x > 0 else "37,99,235"
    return f"background:rgba({rgb},{a:.2f}) !important"


def kv_view_html(key, layer, kind, head, ndims) -> str:
    entry = DEMO.store.peek(key) if (DEMO is not None and key) else None
    if entry is None:
        return '<div class="kv">No cache yet — enter a design sentence (press Enter / click away) or press <b>Run</b>.</div>'
    _, cache, _, meta = entry
    kv = layer_kv(cache)
    layer, head, ndims = int(layer), int(head), int(ndims)
    idx = 0 if kind == "K (keys)" else 1
    toks = meta["tokens"]
    t = kv[layer][idx][0]                       # [kv_heads, seq, head_dim]
    H, T, D = t.shape
    head = min(head, H - 1)
    ndims = min(ndims, D)

    # overview: ‖vector‖ per token per layer (all kv heads concatenated)
    norms = [[float(x) for x in kv[l][idx][0].permute(1, 0, 2).reshape(T, -1).norm(dim=-1)] for l in range(len(kv))]
    nmax = max(max(r) for r in norms)
    ov_head = "".join(f"<th>{esc(tk)}</th>" for tk in toks)
    sel = ' style="outline:2px solid #4f46e5"'
    ov_rows = "".join(
        f"<tr{sel if l == layer else ''}><th>L{l}</th>"
        + "".join(f"<td style='{_shade(v, nmax, False)}'>{v:.1f}</td>" for v in r) + "</tr>"
        for l, r in enumerate(norms))

    # detail: raw numbers for one layer / head
    vals = t[head, :, :ndims]
    vmax = float(vals.abs().max()) or 1.0
    full_norm = t[head].norm(dim=-1)
    det_head = "".join(f"<th>d{d}</th>" for d in range(ndims))
    det_rows = "".join(
        f"<tr><td>{i}</td><td class='l'>{esc(tk)}</td>"
        + "".join(f"<td style='{_shade(float(x), vmax, True)}'>{float(x):+.2f}</td>" for x in vals[i])
        + f"<td><b>{float(full_norm[i]):.2f}</b></td></tr>"
        for i, tk in enumerate(toks))
    name = "Key" if idx == 0 else "Value"
    return f"""<div class="kv">
<div class="sub">Stored cache <code>{key}</code> · {html.escape(meta['shape'])} · {meta.get('bytes', 0) / 1e6:.2f} MB ·
every number below is read directly from the model's <code>past_key_values</code>.</div>
<h3>{name} tensor · layer {layer} · KV head {head} · first {ndims} of {D} dims</h3>
<div class="sub">Row = cached token, column = dimension. Red = positive, blue = negative, stronger colour = larger |value|.
The last column is the length ‖{kind[0]}‖ of the whole {D}-dim vector.</div>
<div style="overflow-x:auto"><table class="heat"><tr><th>#</th><th class='l'>token</th>{det_head}<th>‖·‖</th></tr>{det_rows}</table></div>
<h3>Overview: ‖{kind[0]}‖ per token, every layer</h3>
<div class="sub">Length of each token's {name.lower()} vector (all {H} KV heads × {D} dims concatenated). The selected layer is outlined.</div>
<div style="overflow-x:auto"><table class="heat"><tr><th>layer</th>{ov_head}</tr>{ov_rows}</table></div>
</div>"""


# ----------------------------------------------------------------------------- results tab
def strip_html(r: TestResult) -> str:
    gen_ok = {i: ok for i, (_, _, ok) in enumerate(r.gen_word_matches)}
    parts = ['<div><b>Cached (prefill):</b> ']
    parts += [f'<span class="chip c">{esc(t)}</span>' for t in r.cached_tokens]
    parts.append('</div><div><b>Appended:</b> ')
    parts += [f'<span class="chip a">{esc(t)}</span>' for t in r.appended_tokens] or ['<i>(nothing — decode from the last cached token)</i>']
    parts.append('</div><div><b>Generated (greedy):</b> ')
    w = -1
    for t in r.generated_tokens:
        if t.startswith(" ") or w < 0:
            w += 1
        parts.append(f'<span class="chip {"g" if gen_ok.get(w, False) else "x"}">{esc(t)}</span>')
    parts.append("</div>")
    return "".join(parts)


def result_html(r: TestResult) -> str:
    tok_rows = "".join(
        f"<tr><td>{s.position}</td><td class='l'>{esc(s.target_str)}</td><td>{s.logit_target:.3f}</td><td>{s.lse:.3f}</td>"
        f"<td>{s.prob:.2%} <span class='bar' style='width:{max(1, s.prob * 80):.0f}px'></span></td><td>{s.nll:.3f}</td><td>{s.rank}</td>"
        f"<td class='l'>{esc(s.top1_str)} ({s.top1_prob:.1%})</td><td class='{'ok' if s.correct else 'bad'}'>{'✓' if s.correct else '✗'}</td></tr>"
        for s in r.token_scores)
    word_rows = "".join(
        f"<tr><td class='l'><b>{html.escape(w.word)}</b></td><td class='l'>{' × '.join(f'{p:.2%}' for p in w.token_probs)}"
        f"  ({' + '.join(esc(t) for t in w.token_strs)})</td>"
        f"<td><b>{w.prob:.2%}</b> <span class='bar' style='width:{max(1, w.prob * 80):.0f}px'></span></td>"
        f"<td class='{'ok' if w.correct else 'bad'}'>{'✓' if w.correct else '✗'}</td></tr>"
        for w in r.word_scores)
    gen_rows = "".join(
        f"<tr><td>{i}</td><td class='l'>{html.escape(e)}</td><td class='l'>{html.escape(g)}</td>"
        f"<td class='{'ok' if ok else 'bad'}'>{'✓' if ok else '✗'}</td></tr>"
        for i, (e, g, ok) in enumerate(r.gen_word_matches))
    return f"""
<div class="testcard">
<h3>Test {r.index}: append “{html.escape(r.partial) or '∅'}”</h3>
<div class="sub">{html.escape(r.note)} · cache length {r.cache_len_before} → {r.cache_len_after_append} tokens after append ·
sanity: max |logit(cached) − logit(no cache)| = {r.sanity_max_abs_diff:.1e}</div>
{strip_html(r)}
<div><b>Expected:</b> {html.escape(r.expected)}<br><b>Greedy output:</b> {html.escape(r.generated_text)}</div>
<div class="sub" style="margin-top:4px"><b>Token acc</b> {r.n_correct_tokens}/{r.n_tokens} = {pct(r.token_accuracy)} ·
<b>Word acc</b> {r.n_correct_words}/{len(r.word_scores)} = {pct(r.word_accuracy)} ·
<b>Greedy word match</b> {pct(r.gen_word_accuracy)} · <b>PPL</b> {r.perplexity:.3f} — see the <b>Math</b> tab for the derivation</div>
<h3>Per-word prediction probability</h3>
<table><tr><th class='l'>word</th><th class='l'>token probabilities (chain rule)</th><th>P(word)</th><th>top-1?</th></tr>{word_rows}</table>
<h3>Per-token scores (teacher-forced)</h3>
<table><tr><th>#</th><th class='l'>target token</th><th>z_t</th><th>LSE</th><th>p = e^(z_t−LSE)</th><th>−ln p</th><th>rank</th><th class='l'>model's top-1</th><th>✓</th></tr>{tok_rows}</table>
<h3>Free greedy generation, word by word</h3>
<table><tr><th>k</th><th class='l'>expected</th><th class='l'>generated</th><th>match</th></tr>{gen_rows}</table>
</div>"""


def results_html(results: list[TestResult]) -> str:
    rows = "".join(
        f"<tr><td>{r.index}</td><td class='l'>{html.escape(r.partial) or '∅'}</td><td>{len(r.appended_tokens)}</td>"
        f"<td>{r.n_correct_tokens}/{r.n_tokens} = {pct(r.token_accuracy)}</td>"
        f"<td>{r.n_correct_words}/{len(r.word_scores)} = {pct(r.word_accuracy)}</td>"
        f"<td>{pct(r.mean_word_prob)}</td><td>{pct(r.gen_word_accuracy)}</td><td>{r.perplexity:.2f}</td>"
        f"<td class='l'>{html.escape(r.generated_text)}</td></tr>"
        for r in results)
    return f"""<div class="kv">
<div><span class="chip c">cached</span> <span class="chip a">appended</span>
<span class="chip g">generated, matches expected word</span> <span class="chip x">generated, differs</span></div>
<h3>Summary</h3>
<table><tr><th>test</th><th class='l'>appended</th><th>#tok</th><th>token acc</th><th>word acc</th><th>mean P(word)</th>
<th>greedy word match</th><th>PPL</th><th class='l'>greedy output</th></tr>{rows}</table>
{''.join(result_html(r) for r in results)}</div>"""


# ----------------------------------------------------------------------------- math tab
def worked_example(s, vocab: int, open_: bool) -> str:
    m = s.logit_max
    S = math.exp(s.lse - m)  # Σ_j exp(z_j − max) over the WHOLE vocabulary
    rows = "".join(
        f"<tr><td class='l'>{esc(t)}</td><td>{z:.3f}</td><td>{z - m:.3f}</td><td>{math.exp(z - m):.4f}</td>"
        f"<td>{math.exp(z - m):.4f} / {S:.4f} = <b>{p:.2%}</b></td></tr>"
        for t, z, p in s.topk)
    if not any(t == s.target_str for t, _, _ in s.topk):
        rows += (f"<tr><td class='l'><b>{esc(s.target_str)}</b> (target, rank {s.rank})</td><td>{s.logit_target:.3f}</td>"
                 f"<td>{s.logit_target - m:.3f}</td><td>{math.exp(s.logit_target - m):.4g}</td>"
                 f"<td>{math.exp(s.logit_target - m):.4g} / {S:.4f} = <b>{s.prob:.4%}</b></td></tr>")
    verdict = "✓ top-1" if s.correct else f"✗ model preferred {esc(s.top1_str)}"
    return f"""
<details{' open' if open_ else ''}><summary>Position {s.position}: target {esc(s.target_str)} → p = {s.prob:.2%} · {verdict}</summary>
<div class="formula">softmax(z)_t = exp(z_t) / Σ_j exp(z_j)            (j runs over all {vocab:,} vocab entries)
            = exp(z_t − max) / Σ_j exp(z_j − max)  (subtract max z = {m:.3f} for numerical stability; same result)
Σ_j exp(z_j − max) = {S:.4f}     ⇒  LSE = max + ln(Σ) = {m:.3f} + {math.log(S):.4f} = {s.lse:.4f}
p(target) = exp(z_t − LSE) = exp({s.logit_target:.3f} − {s.lse:.3f}) = exp({s.logit_target - s.lse:.4f}) = {s.prob:.4%}
NLL = −ln p = {s.nll:.4f}       rank of target = {s.rank}  →  top-1 correct: {s.correct}</div>
<table><tr><th class='l'>candidate token</th><th>logit z</th><th>z − max</th><th>exp(z − max)</th><th>÷ Σ = probability</th></tr>{rows}</table>
</details>"""


def math_html(results: list[TestResult] | None, idx) -> str:
    if not results:
        return '<div class="kv">Run the experiment first; then pick a test here.</div>'
    r = results[int(idx or 0)]
    n, W = r.n_tokens, len(r.word_scores)
    tok_sum = " + ".join("1" if s.correct else "0" for s in r.token_scores)
    word_terms = " + ".join(f"{w.prob:.3f}" for w in r.word_scores)
    nll_terms = " + ".join(f"{s.nll:.3f}" for s in r.token_scores)
    gen_hits = sum(x[2] for x in r.gen_word_matches)
    vocab = get_demo().model.config.vocab_size
    worked = "".join(worked_example(s, vocab, s.position == 0) for s in r.token_scores)
    return f"""<div class="kv">
<h3>Test {r.index}: append “{html.escape(r.partial) or '∅'}” → expected “{html.escape(r.expected)}”</h3>
<h3>Headline numbers, with the values plugged in</h3>
<div class="formula">Token top-1 accuracy  = Σ correct_i / N = ({tok_sum}) / {n} = {r.n_correct_tokens}/{n} = <b>{pct(r.token_accuracy)}</b>
Word top-1 accuracy   = words whose tokens are all top-1 / words = {r.n_correct_words}/{W} = <b>{pct(r.word_accuracy)}</b>
Mean word probability = (1/W) Σ_w Π_(i∈w) p_i = ({word_terms}) / {W} = <b>{pct(r.mean_word_prob)}</b>
Greedy word match     = generated word k == expected word k = {gen_hits}/{len(r.gen_word_matches)} = <b>{pct(r.gen_word_accuracy)}</b>
Mean NLL              = ({nll_terms}) / {n} = {r.mean_nll:.4f}
Perplexity            = exp(mean NLL) = exp({r.mean_nll:.4f}) = <b>{r.perplexity:.3f}</b>   (1.0 = certain of every token)
P(whole continuation) = Π_i p_i = exp(Σ ln p_i) = exp({r.sequence_logprob:.4f}) = {math.exp(r.sequence_logprob):.3e}</div>
<h3>Worked softmax for each position</h3>
{worked}</div>"""


# ----------------------------------------------------------------------------- run
def run(sentence: str, partials_text: str, max_new: float, layer, kind, head, ndims, progress=gr.Progress()):
    progress(0, desc="Loading model / KV cache…")
    demo = get_demo()
    sentence = sentence.strip() or DEFAULT_SENTENCE
    lines = partials_text.split("\n")
    while lines and lines[-1].strip() == "" and len(lines) > 1:
        lines.pop()  # trailing blank lines are not tests
    partials = [("" if ln.strip() in ("", "∅", "<empty>") else ln.strip()) for ln in lines] or default_partials(sentence)
    progress(0.2, desc="Appending partial prompts + scoring…")
    info, results = demo.run(sentence, partials, int(max_new) or None)
    choices = [(f"Test {r.index} — {r.partial or '∅ (empty)'}", r.index) for r in results]
    return (cache_html(info), results_html(results), results,
            gr.Dropdown(choices=choices, value=0, interactive=True), math_html(results, 0),
            info["key"], kv_view_html(info["key"], layer, kind, head, ndims))


FORCE_LIGHT = """() => {
  const u = new URL(window.location.href);
  if (u.searchParams.get('__theme') !== 'light') { u.searchParams.set('__theme', 'light'); window.location.replace(u.href); }
}"""

with gr.Blocks(title=TITLE, theme=gr.themes.Default(), css=CSS, js=FORCE_LIGHT) as ui:
    gr.HTML(HERO)
    with gr.Row():
        with gr.Column(scale=3):
            sent = gr.Textbox(label="Design sentence (cached once in memory — press Enter or click away to store)",
                              value=DEFAULT_SENTENCE, lines=2)
            parts = gr.Textbox(label="Partial prompts to append (one per line, blank line = empty test)",
                               value="\n".join(default_partials(DEFAULT_SENTENCE)), lines=7)
        with gr.Column(scale=1):
            mx = gr.Number(label="Max new tokens (0 = length of expected continuation)", value=0, precision=0)
            auto = gr.Button("Auto-fill word prefixes")
            go = gr.Button("Run", variant="primary")
    cache_box = gr.HTML(cache_html(None, "Not loaded yet — click away from the sentence box or press Run."))
    state = gr.State(None)
    cur_key = gr.State(None)
    with gr.Tabs():
        with gr.Tab("Results"):
            out = gr.HTML('<div class="kv">Press <b>Run</b>.</div>')
        with gr.Tab("Math"):
            pick = gr.Dropdown(label="Show the math for test", choices=[], interactive=True)
            math_out = gr.HTML(math_html(None, 0))
        with gr.Tab("KV Cache"):
            with gr.Row():
                kv_kind = gr.Radio(["K (keys)", "V (values)"], value="K (keys)", label="Tensor")
                kv_layer = gr.Slider(0, N_LAYERS - 1, value=0, step=1, label=f"Layer (0–{N_LAYERS - 1})")
                kv_head = gr.Slider(0, N_KV_HEADS - 1, value=0, step=1, label=f"KV head (0–{N_KV_HEADS - 1})")
                kv_dims = gr.Slider(8, HEAD_DIM, value=16, step=8, label=f"Dims shown (of {HEAD_DIM})")
            kv_out = gr.HTML(kv_view_html(None, 0, "K (keys)", 0, 16))

    kv_ctl = [kv_layer, kv_kind, kv_head, kv_dims]
    sent.submit(ensure_cache, [sent, *kv_ctl], [cache_box, cur_key, kv_out])
    sent.blur(ensure_cache, [sent, *kv_ctl], [cache_box, cur_key, kv_out])
    auto.click(lambda s: "\n".join(default_partials(s.strip() or DEFAULT_SENTENCE)), sent, parts)
    go.click(run, [sent, parts, mx, *kv_ctl], [cache_box, out, state, pick, math_out, cur_key, kv_out])
    pick.change(math_html, [state, pick], math_out)
    for c in kv_ctl:
        c.change(kv_view_html, [cur_key, *kv_ctl], kv_out)

if __name__ == "__main__":
    ui.queue().launch(server_name=os.environ.get("KVDEMO_HOST", "127.0.0.1"),
                      server_port=int(os.environ.get("KVDEMO_PORT", "7860")))
