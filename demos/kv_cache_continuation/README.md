# KV Cache Hit For Accuracy (Experiment A)

This demo shows how well a small language model predicts the rest of a sentence when that sentence is already in its KV cache. You type a **design sentence**, and the demo computes its KV cache once. Then it appends **partial prompts** such as `The old car has` to a fresh copy of that cache. For each one it shows how accurately the model predicts the remaining words, with the math written out using the real numbers.

- **Model:** `Qwen/Qwen3-0.6B-Base`, about 1.2 GB, downloaded automatically on the first run.
- **Hardware:** CPU only, no GPU needed. Plan for about 3 GB of free RAM.
- **Relationship to Hecate:** this demo is separate from the Hecate router experiments and doesn't use the project's `pyproject.toml` dependencies.

> **Caveat:** each partial prompt is appended *after* the full cached sentence. So this measures **recall from context**: can the model repeat what it has just seen? It is not ordinary prefix completion.

---

## 1. One-time setup

Run these commands in an **Ubuntu (WSL) terminal**. They need Python 3.10 or newer and internet access for the first install and the model download.

```bash
cd ~/hecate-router

# Create a separate environment that won't touch other Python installs
python3 -m venv ~/kvdemo-venv

# Install CPU-only PyTorch, transformers and gradio (~1 GB download)
~/kvdemo-venv/bin/pip install --upgrade pip
~/kvdemo-venv/bin/pip install -r demos/kv_cache_continuation/requirements.txt
```

If `python3 -m venv` fails with "ensurepip is not available", run `sudo apt install python3-venv` and try again.

To check that the install worked:

```bash
~/kvdemo-venv/bin/python -c "import torch, transformers, gradio; print('OK', torch.__version__, transformers.__version__, gradio.__version__)"
```

---

## 2. Run the web demo

```bash
cd ~/hecate-router
~/kvdemo-venv/bin/python demos/kv_cache_continuation/app.py
```

Wait until the terminal prints `Running on local URL: http://127.0.0.1:7860`, then open **http://127.0.0.1:7860** in your browser. With WSL2, a Windows browser can open this address directly. Press **Ctrl+C** in the terminal to stop the server.

The first **Run** takes longer because the model is downloaded and loaded. Later runs take a few seconds.

**Starting it from Windows PowerShell** instead of an Ubuntu terminal:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd ~/hecate-router && ~/kvdemo-venv/bin/python demos/kv_cache_continuation/app.py"
```

### Using the page

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

---

## 3. Run from the terminal (no web page)

This runs the same experiment and prints tables:

```bash
cd ~/hecate-router

# Default sentence, partial prompts ∅, The, The old, … (first 5 words)
~/kvdemo-venv/bin/python demos/kv_cache_continuation/kvdemo.py

# Your own sentence and prompts (repeat --partial; use --partial "" for an empty test)
~/kvdemo-venv/bin/python demos/kv_cache_continuation/kvdemo.py \
  --sentence "The old car has faded red paint and is parked outside the house." \
  --partial "" --partial "The old" --partial "The old car has"
```

| Option | Default | Meaning |
|---|---|---|
| `--sentence` | the old-car sentence | design sentence to cache |
| `--partial` | the sentence's first 0–5 words | partial prompt to append (repeatable) |
| `--max-new-tokens` | length of the expected continuation | how many tokens to generate |
| `--model` | `Qwen/Qwen3-0.6B-Base` | any Hugging Face causal language model |

---

## 4. Settings

Set these environment variables in front of the command to change the defaults, for example `KVDEMO_PORT=7861 ~/kvdemo-venv/bin/python demos/kv_cache_continuation/app.py`.

| Variable | Default | Purpose |
|---|---|---|
| `KVDEMO_PORT` | `7860` | port for the web page |
| `KVDEMO_HOST` | `127.0.0.1` | use `0.0.0.0` to open the page from another machine |
| `KVDEMO_MODEL` | `Qwen/Qwen3-0.6B-Base` | model used by the web page |
| `HF_HUB_OFFLINE` | unset | set to `1` to use only models already downloaded |

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot find empty port` / `address already in use` | A demo server is already running. Stop it with `pkill -f kv_cache_continuation/app.py`, or use `KVDEMO_PORT=7861`. |
| `requires the protobuf library` or a tokenizer error when loading the model | The downloaded copy of the model is incomplete. Run without `HF_HUB_OFFLINE=1` so the missing files download again. |
| The page shows light text on a dark background | Open `http://127.0.0.1:7860/?__theme=light`. The page normally switches to the light theme by itself. |
| The page doesn't load in a Windows browser | Make sure the server printed `Running on local URL`. With WSL1 or unusual network setups, start it with `KVDEMO_HOST=0.0.0.0` and open the WSL IP address shown by `hostname -I`. |
| `ModuleNotFoundError: torch` | You're using the wrong Python. Run with `~/kvdemo-venv/bin/python`, not plain `python3`. |

---

## 6. How the scores are computed

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

---

## Files

| File | Role |
|---|---|
| `app.py` | the web page |
| `kvdemo.py` | the engine: prefill, in-memory cache store, append, scoring, greedy decoding, sanity check; also the terminal version |
| `requirements.txt` | CPU-only PyTorch, transformers, gradio |
