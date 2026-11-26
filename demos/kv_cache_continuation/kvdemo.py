"""Cache-conditioned continuation demo (Experiment A) — core engine.

Flow for every test:
    1. Prefill the full design sentence once -> past_key_values (the "original cache").
    2. For each partial prompt, deep-copy the original cache (tests never contaminate
       each other), append the partial prompt's tokens, and
         a) TEACHER-FORCED scoring: feed the *expected* continuation and read, at every
            position, the probability the model assigned to the correct next token;
         b) FREE GREEDY decoding: let the model generate on its own and compare words.
    3. Sanity check: recompute the same sequence with NO cache and confirm the logits
       match the cached path (proves the cache is real and correctly appended).

The probability math (per position i, vocabulary logits z ∈ R^V, target token t):
    LSE   = log Σ_j exp(z_j)                (log-sum-exp, computed stably)
    p_i   = softmax(z)_t = exp(z_t − LSE)
    NLL_i = −ln p_i
    correct_i = [argmax_j z_j == t]
Aggregates:
    token accuracy = Σ correct_i / N
    word probability = Π_{tokens in word} p_i       (chain rule)
    word accuracy  = (# words whose tokens are all top-1 correct) / (# words)
    perplexity     = exp( (1/N) Σ NLL_i )
"""
from __future__ import annotations

import copy
import hashlib
import math
import time
from dataclasses import dataclass, field

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL = "Qwen/Qwen3-0.6B-Base"
DEFAULT_SENTENCE = "The old car has faded red paint and is parked outside the house."


# ----------------------------------------------------------------------------- in-memory store
def layer_kv(cache) -> list[tuple[torch.Tensor, torch.Tensor]]:
    """Per-layer (K, V) tensors, across transformers cache API versions."""
    if hasattr(cache, "layers") and cache.layers:
        return [(l.keys, l.values) for l in cache.layers]
    if hasattr(cache, "key_cache"):
        return list(zip(cache.key_cache, cache.value_cache))
    return [(k, v) for k, v in cache]


class KVCacheStore:
    """In-memory cache store (nothing is written to disk).

    The key is a hash of the model name + exact sentence text, so the same sentence is
    prefilled once (later runs are cache HITs), and any edit produces a new entry (MISS → store).
    Entries live for the lifetime of the process.
    """

    def __init__(self):
        self._entries: dict[str, tuple[list[int], object, torch.Tensor, dict]] = {}

    @staticmethod
    def key(model_name: str, sentence: str) -> str:
        return hashlib.sha256(f"{model_name}\n{sentence}".encode()).hexdigest()[:16]

    def exists(self, key: str) -> bool:
        return key in self._entries

    def save(self, key: str, meta: dict, ids: list[int], cache, last_logits: torch.Tensor) -> None:
        nbytes = sum(k.numel() * k.element_size() + v.numel() * v.element_size() for k, v in layer_kv(cache))
        self._entries[key] = (list(ids), copy.deepcopy(cache), last_logits.detach().clone(),
                              dict(meta, key=key, bytes=nbytes))

    def load(self, key: str):
        ids, cache, last, meta = self._entries[key]
        return ids, copy.deepcopy(cache), last, meta  # callers never mutate the stored master copy

    def peek(self, key: str):
        """Read-only access to the stored cache (for display)."""
        return self._entries.get(key)

    def list(self) -> list[dict]:
        return sorted((e[3] for e in self._entries.values()), key=lambda m: m.get("created", ""), reverse=True)


# ----------------------------------------------------------------------------- data
@dataclass
class TokenScore:
    position: int            # index within the expected continuation
    target_id: int
    target_str: str
    logit_target: float      # z_t
    logit_max: float         # max_j z_j
    lse: float               # log Σ exp(z_j)
    prob: float              # exp(z_t − LSE)
    nll: float               # −ln p
    rank: int                # 1 = model's top choice
    top1_str: str
    top1_prob: float
    correct: bool
    word_index: int
    topk: list[tuple[str, float, float]] = field(default_factory=list)  # (tok, logit, prob)


@dataclass
class WordScore:
    word: str
    token_strs: list[str]
    token_probs: list[float]
    prob: float              # product of token probs
    correct: bool            # every token top-1


@dataclass
class TestResult:
    index: int
    partial: str
    expected: str
    cached_tokens: list[str]
    appended_tokens: list[str]
    generated_tokens: list[str]
    generated_text: str
    token_scores: list[TokenScore]
    word_scores: list[WordScore]
    gen_word_matches: list[tuple[str, str, bool]]  # (expected, generated, match)
    cache_len_before: int
    cache_len_after_append: int
    cache_shape: str
    sanity_max_abs_diff: float
    note: str = ""

    # aggregates ----------------------------------------------------------------
    @property
    def n_tokens(self) -> int:
        return len(self.token_scores)

    @property
    def n_correct_tokens(self) -> int:
        return sum(t.correct for t in self.token_scores)

    @property
    def token_accuracy(self) -> float:
        return self.n_correct_tokens / self.n_tokens if self.n_tokens else float("nan")

    @property
    def mean_token_prob(self) -> float:
        return sum(t.prob for t in self.token_scores) / self.n_tokens if self.n_tokens else float("nan")

    @property
    def mean_nll(self) -> float:
        return sum(t.nll for t in self.token_scores) / self.n_tokens if self.n_tokens else float("nan")

    @property
    def perplexity(self) -> float:
        return math.exp(self.mean_nll) if self.n_tokens else float("nan")

    @property
    def sequence_logprob(self) -> float:
        return -sum(t.nll for t in self.token_scores)

    @property
    def n_correct_words(self) -> int:
        return sum(w.correct for w in self.word_scores)

    @property
    def word_accuracy(self) -> float:
        return self.n_correct_words / len(self.word_scores) if self.word_scores else float("nan")

    @property
    def mean_word_prob(self) -> float:
        return sum(w.prob for w in self.word_scores) / len(self.word_scores) if self.word_scores else float("nan")

    @property
    def gen_word_accuracy(self) -> float:
        m = self.gen_word_matches
        return sum(x[2] for x in m) / len(m) if m else float("nan")


# ----------------------------------------------------------------------------- engine
class KVCacheDemo:
    def __init__(self, model_name: str = DEFAULT_MODEL, threads: int | None = None,
                 store: KVCacheStore | None = None):
        if threads:
            torch.set_num_threads(threads)
        self.model_name = model_name
        self.store = store or KVCacheStore()
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.float32)
        self.model.eval()

    # helpers -------------------------------------------------------------------
    def encode(self, text: str) -> list[int]:
        return self.tok(text, add_special_tokens=False)["input_ids"] if text else []

    def tstr(self, tid: int) -> str:
        return self.tok.decode([tid])

    @torch.no_grad()
    def forward(self, ids: list[int], cache):
        out = self.model(
            input_ids=torch.tensor([ids]),
            past_key_values=cache,
            use_cache=True,
        )
        return out.logits[0], out.past_key_values

    @staticmethod
    def cache_len(cache) -> int:
        return int(cache.get_seq_length()) if hasattr(cache, "get_seq_length") else int(cache[0][0].shape[-2])

    @staticmethod
    def cache_shape(cache) -> str:
        try:
            if hasattr(cache, "layers") and cache.layers:
                k = cache.layers[0].keys
                n = len(cache.layers)
            elif hasattr(cache, "key_cache"):
                k = cache.key_cache[0]
                n = len(cache.key_cache)
            else:
                k = cache[0][0]
                n = len(cache)
            return f"{n} layers × K,V each [batch={k.shape[0]}, kv_heads={k.shape[1]}, seq={k.shape[2]}, head_dim={k.shape[3]}]"
        except Exception as e:  # pragma: no cover - display only
            return f"(shape unavailable: {e})"

    # target construction ---------------------------------------------------------
    @staticmethod
    def expected_continuation(sentence: str, partial: str) -> tuple[str, str]:
        """If `partial` is a word-prefix of the sentence, the target is the rest of the
        sentence; otherwise the target is the whole sentence (can the model recall it?)."""
        s_words, p_words = sentence.split(), partial.split()
        if p_words and s_words[: len(p_words)] == p_words:
            return " ".join(s_words[len(p_words):]), "partial is a prefix → target = rest of sentence"
        if not p_words:
            return " ".join(s_words), "empty partial → target = whole sentence"
        return " ".join(s_words), "partial is NOT a prefix of the sentence → target = whole sentence"

    # one test ------------------------------------------------------------------------
    @torch.no_grad()
    def run_test(self, index: int, sentence: str, partial: str, base_cache, base_last_logits,
                 cached_ids: list[int], max_new_tokens: int | None = None, topk: int = 5) -> TestResult:
        partial = partial.strip()
        expected, note = self.expected_continuation(sentence, partial)

        # Leading space: the appended text comes *after* the cached sentence.
        app_ids = self.encode(" " + partial) if partial else []
        tgt_ids = self.encode(" " + expected) if expected else []

        # --- Step B: append partial prompt to a FRESH copy of the original cache
        cache = copy.deepcopy(base_cache)
        len_before = self.cache_len(cache)
        if app_ids:
            logits, cache = self.forward(app_ids, cache)
            next_logits = logits[-1]
        else:
            next_logits = base_last_logits
        len_after = self.cache_len(cache)
        shape = self.cache_shape(cache)

        # --- (a) teacher-forced scoring of the expected continuation
        scores: list[TokenScore] = []
        if tgt_ids:
            tf_cache = copy.deepcopy(cache)
            if len(tgt_ids) > 1:
                tf_logits, _ = self.forward(tgt_ids[:-1], tf_cache)
                all_logits = torch.cat([next_logits[None], tf_logits], dim=0)
            else:
                all_logits = next_logits[None]
            word_idx = -1
            for i, (z, t) in enumerate(zip(all_logits, tgt_ids)):
                z = z.float()
                lse = torch.logsumexp(z, dim=-1).item()
                zt = z[t].item()
                p = math.exp(zt - lse)
                rank = int((z > z[t]).sum().item()) + 1
                top_vals, top_ids = torch.topk(z, topk)
                ts = self.tstr(t)
                if i == 0 or ts.startswith(" ") or word_idx < 0:
                    word_idx += 1
                scores.append(TokenScore(
                    position=i, target_id=t, target_str=ts,
                    logit_target=zt, logit_max=top_vals[0].item(), lse=lse,
                    prob=p, nll=-(zt - lse), rank=rank,
                    top1_str=self.tstr(int(top_ids[0])),
                    top1_prob=math.exp(top_vals[0].item() - lse),
                    correct=(rank == 1), word_index=word_idx,
                    topk=[(self.tstr(int(j)), v.item(), math.exp(v.item() - lse))
                          for v, j in zip(top_vals, top_ids)],
                ))

        words: list[WordScore] = []
        for w in range(scores[-1].word_index + 1 if scores else 0):
            toks = [s for s in scores if s.word_index == w]
            prob = math.prod(s.prob for s in toks)
            words.append(WordScore(
                word="".join(s.target_str for s in toks).strip(),
                token_strs=[s.target_str for s in toks],
                token_probs=[s.prob for s in toks],
                prob=prob, correct=all(s.correct for s in toks)))

        # --- (b) free greedy decoding from the appended cache (Step C)
        n_new = max_new_tokens or max(len(tgt_ids), 1)
        gen_cache = copy.deepcopy(cache)
        gen_ids: list[int] = []
        z = next_logits
        for _ in range(n_new):
            nid = int(torch.argmax(z))
            gen_ids.append(nid)
            if nid == self.tok.eos_token_id:
                break
            lg, gen_cache = self.forward([nid], gen_cache)
            z = lg[-1]
        gen_text = self.tok.decode(gen_ids)
        exp_words, gen_words = expected.split(), gen_text.split()
        gen_matches = [(e, gen_words[i] if i < len(gen_words) else "∅",
                        i < len(gen_words) and gen_words[i] == e) for i, e in enumerate(exp_words)]

        # --- sanity: no-cache recompute of [cached + appended + target[:-1]]
        full = cached_ids + app_ids + tgt_ids[:-1]
        diff = float("nan")
        if tgt_ids:
            ref = self.model(input_ids=torch.tensor([full]), use_cache=False).logits[0]
            ref_tail = ref[len(cached_ids) + len(app_ids) - 1:]
            diff = (ref_tail - all_logits).abs().max().item()

        return TestResult(
            index=index, partial=partial, expected=expected,
            cached_tokens=[self.tstr(i) for i in cached_ids],
            appended_tokens=[self.tstr(i) for i in app_ids],
            generated_tokens=[self.tstr(i) for i in gen_ids],
            generated_text=gen_text, token_scores=scores, word_scores=words,
            gen_word_matches=gen_matches, cache_len_before=len_before,
            cache_len_after_append=len_after, cache_shape=shape,
            sanity_max_abs_diff=diff, note=note)

    # full experiment ---------------------------------------------------------------------
    @torch.no_grad()
    def get_or_build_cache(self, sentence: str):
        """Step A, memoised in memory: reuse the stored cache for this exact sentence (HIT),
        or prefill it and store it (MISS). Returns (ids, cache, last_logits, info)."""
        sentence = sentence.strip()
        if not sentence:
            raise ValueError("Design sentence is empty.")
        key = self.store.key(self.model_name, sentence)
        t0 = time.perf_counter()
        if self.store.exists(key):
            ids, cache, last, meta = self.store.load(key)
            return ids, cache, last, dict(hit=True, key=key, seconds=time.perf_counter() - t0, meta=meta)
        ids = self.encode(sentence)
        logits, cache = self.forward(ids, None)
        last = logits[-1]
        meta = dict(sentence=sentence, model=self.model_name, n_tokens=len(ids),
                    tokens=[self.tstr(i) for i in ids], shape=self.cache_shape(cache),
                    created=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.store.save(key, meta, ids, cache, last)
        return ids, cache, last, dict(hit=False, key=key, seconds=time.perf_counter() - t0,
                                      meta=self.store.peek(key)[3])

    @torch.no_grad()
    def run(self, sentence: str, partials: list[str], max_new_tokens: int | None = None):
        cached_ids, base_cache, base_last, info = self.get_or_build_cache(sentence)
        results = [self.run_test(i, sentence, p, base_cache, base_last, cached_ids, max_new_tokens)
                   for i, p in enumerate(partials)]
        return info, results


def default_partials(sentence: str, n: int = 5) -> list[str]:
    """Empty, then the first 1..n words of the sentence."""
    words = sentence.split()
    return [""] + [" ".join(words[:k]) for k in range(1, min(n, len(words)) + 1)]


# ----------------------------------------------------------------------------- CLI
def _print_result(r: TestResult) -> None:
    print(f"\n=== Test {r.index}: append {r.partial!r} ({r.note})")
    print(f"cache seq len: {r.cache_len_before} → {r.cache_len_after_append} after append")
    print(f"expected : {r.expected!r}")
    print(f"generated: {r.generated_text!r}")
    print(f"{'#':>2} {'target':<12} {'z_t':>8} {'LSE':>8} {'p=e^(z_t-LSE)':>14} {'-ln p':>7} {'rank':>5}  top-1")
    for s in r.token_scores:
        print(f"{s.position:>2} {s.target_str!r:<12} {s.logit_target:8.3f} {s.lse:8.3f} "
              f"{s.prob:14.4%} {s.nll:7.3f} {s.rank:>5}  {s.top1_str!r} ({s.top1_prob:.1%}){'' if s.correct else '  ✗'}")
    print("words:", ", ".join(f"{w.word}={w.prob:.1%}{'✓' if w.correct else '✗'}" for w in r.word_scores))
    print(f"token accuracy = {r.n_correct_tokens}/{r.n_tokens} = {r.token_accuracy:.1%}")
    print(f"word accuracy  = {r.n_correct_words}/{len(r.word_scores)} = {r.word_accuracy:.1%}")
    print(f"greedy word match = {r.gen_word_accuracy:.1%}   perplexity = {r.perplexity:.3f}")
    print(f"sanity |cached − uncached| max logit diff = {r.sanity_max_abs_diff:.2e}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sentence", default=DEFAULT_SENTENCE)
    ap.add_argument("--partial", action="append", help="partial prompt (repeatable); default = word prefixes")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-new-tokens", type=int, default=None)
    a = ap.parse_args()
    demo = KVCacheDemo(a.model)
    info, results = demo.run(a.sentence, a.partial or default_partials(a.sentence), a.max_new_tokens)
    print(f"KV cache {'HIT (reused)' if info['hit'] else 'MISS (prefilled + stored in memory)'}"
          f"  [{info['meta']['shape']}]  {info['seconds']:.2f}s")
    for r in results:
        _print_result(r)
