# KV Cache Hit For Accuracy (Experiment A)

This demo is separate from the Hecate router experiments. It runs on CPU with `Qwen/Qwen3-0.6B-Base`, which is about 1.2 GB of weights.

```bash
python3 -m venv ~/kvdemo-venv
~/kvdemo-venv/bin/pip install -r demos/kv_cache_continuation/requirements.txt
~/kvdemo-venv/bin/python demos/kv_cache_continuation/app.py        # UI at http://127.0.0.1:7860
~/kvdemo-venv/bin/python demos/kv_cache_continuation/kvdemo.py     # same experiment, text output
~/kvdemo-venv/bin/python demos/kv_cache_continuation/kvdemo.py --sentence "..." --partial "The" --partial "The old"
```

## What it does
1. It prefills the design sentence once and keeps the cache in memory. Nothing is written to disk.
   - The key is a hash of the model name and the exact sentence. Running the same sentence again reuses the stored cache (**CACHE HIT**). Any edit to the sentence prefills and stores a new entry (**CACHE MISS**).
   - The UI stores it as soon as you press Enter or click away from the sentence box.
   - The **KV Cache** tab shows the actual numbers. Pick K or V, a layer, a KV head and how many dimensions to show. It also includes an overview heatmap of each token's vector length across all layers.
2. For each partial prompt, it takes a deep copy of that cache and appends the prompt's tokens to it.
3. It scores the expected continuation, which is the rest of the sentence. If the partial prompt is not a word-prefix of the sentence, the whole sentence is the target.
4. It runs greedy decoding from the same appended cache.
5. As a sanity check, it recomputes everything with no cache and reports the largest logit difference. Expect a value around 1e-5.

## The math
For each position *i*, take the logits *z* over the vocabulary and the correct next token *t*.

| quantity | formula |
|---|---|
| log-sum-exp | LSE = log Σⱼ exp(zⱼ) = max z + log Σⱼ exp(zⱼ − max z) |
| token probability | pᵢ = softmax(z)ₜ = exp(zₜ − LSE) |
| top-1 correct | argmax z == t |
| **token accuracy** | Σ correctᵢ / N |
| **word probability** | Π of pᵢ over the word's tokens (chain rule) |
| **word accuracy** | words whose tokens are all top-1 / number of words |
| greedy word match | generated word k == expected word k, divided by the number of expected words |
| perplexity | exp(mean of −ln pᵢ) |

Scoring is **teacher-forced**: at every position the model receives the *correct* previous tokens. That isolates per-word predictability. Greedy match is the free-running counterpart. One wrong word there can shift every later word, so it can drop sharply even when teacher-forced accuracy is high.
