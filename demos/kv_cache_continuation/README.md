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
