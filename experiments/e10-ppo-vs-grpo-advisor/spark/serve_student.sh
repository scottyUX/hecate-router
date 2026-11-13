#!/usr/bin/env bash
# E10 G0c: serve the FP8 student on the Spark (port 8100, model name "student").
exec docker run --rm --name e10-student --gpus all --ipc=host -p 127.0.0.1:8100:8000 \
  -v e10-hf:/root/.cache/huggingface \
  vllm/vllm-openai:v0.20.0 \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  --served-model-name student --max-model-len 65536 \
  --gpu-memory-utilization 0.40 --seed 0
