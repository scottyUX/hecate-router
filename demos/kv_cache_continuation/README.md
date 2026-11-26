# KV Cache Hit For Accuracy (Experiment A)

A web demo that runs on CPU. It uses `Qwen/Qwen3-0.6B-Base`, which downloads automatically on the first run.

## Setup (one time)

Run these commands in an **Ubuntu (WSL) terminal**:

```bash
cd ~/hecate-router
python3 -m venv ~/kvdemo-venv
~/kvdemo-venv/bin/pip install --upgrade pip
~/kvdemo-venv/bin/pip install -r demos/kv_cache_continuation/requirements.txt
```

## Run the web page

```bash
cd ~/hecate-router
~/kvdemo-venv/bin/python demos/kv_cache_continuation/app.py
```

Wait for `Running on local URL: http://127.0.0.1:7860`, then open **http://127.0.0.1:7860** in your browser.

Press **Ctrl+C** in the terminal to stop the server.

## Using the page

1. **Design sentence:** type the sentence to cache, then press **Enter** or click outside the box. The status card shows **CACHE MISS** when the cache is computed and stored, and **CACHE HIT** when a stored cache is reused.
2. **Partial prompts:** enter one per line. A blank line is an empty test, where the model predicts straight from the end of the cached sentence. **Auto-fill word prefixes** fills in `∅`, `The`, `The old`, … from your sentence.
3. **Max new tokens:** how many tokens the model generates on its own. Leave it at `0` to match the length of the expected continuation.
4. Click **Run**, then look at the three tabs:

| Tab | What it shows |
|---|---|
| **Results** | A summary table for every test, then one card per test. Each card shows the tokens colored by type (cached, appended, generated), the probability of each word, scores for each token, and a word-by-word comparison of what the model generated. |
| **Math** | A dropdown to pick **Test 0 … Test n**. It shows that test's accuracy calculations with the real numbers, and the softmax worked out at every position. |
| **KV Cache** | The numbers stored in the cache. Choose K or V, a layer, a KV head and how many dimensions to show. Below that is a heatmap of each token's vector size across all layers. |

### Where the cache lives

Caches are kept **in the server's memory only**. Nothing is written to disk.
- **One entry per sentence:** each design sentence (and model) gets its own entry, so the same sentence is computed only once. Editing the sentence stores a new entry.
- **Fresh copy per test:** every test runs on its own copy of the stored cache, so tests can't affect each other or the stored original.
- **Cleared on restart:** stopping the server deletes all stored caches.

## How the scores are computed

**What happens in each test**
1. **Prefill:** compute the design sentence's KV cache once, or reuse the stored one.
2. **Append:** add the partial prompt's tokens to a **fresh copy** of that cache.
3. **Score (teacher-forced):** feed in the *expected* continuation, meaning the rest of the sentence. At every position, record the probability the model gave the correct next token. If the partial prompt isn't the start of the sentence, the whole sentence becomes the target.
4. **Generate freely:** decode greedily from the same appended cache and compare the output with the expected words, word by word.
5. **Sanity check:** recompute the same sequence **without** the cache. The largest logit difference should be around 1e-5, which shows the cache path is correct.

**Formulas.** At each position *i*, *z* is the model's score (logit) for every vocabulary entry, and *t* is the correct next token.

| Quantity | Formula |
|---|---|
| log-sum-exp | LSE = log Σⱼ exp(zⱼ) = max z + log Σⱼ exp(zⱼ − max z) |
| token probability | pᵢ = softmax(z)ₜ = exp(zₜ − LSE) |
| top-1 correct | argmax z == t |
| **token accuracy** | Σ correctᵢ / N |
| **word probability** | product of pᵢ over the word's tokens (chain rule) |
| **word accuracy** | words whose tokens are all top-1 ÷ number of words |
| greedy word match | words where generated word k == expected word k ÷ number of expected words |
| perplexity | exp(mean of −ln pᵢ); 1.0 means the model was certain every time |

**Why two kinds of accuracy?** Teacher-forced scoring always gives the model the correct previous words, so it measures how predictable each word is on its own. Greedy word match lets the model run freely. A single wrong word there can shift every later word out of place. For example, appending `The old` gives 91% teacher-forced word accuracy but only 9% greedy word match: the model writes "is" instead of "has" and then goes off course.
