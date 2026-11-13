# E10 (amendment A2): upstream SkyRL 3e8700f on the DGX Spark (aarch64, GB10, CUDA 13).
# Locked stack from upstream uv.lock (torch 2.14+cu130, vLLM 0.33, flashinfer sm121a).
# flash-attn has no aarch64 wheel: installed without its CUDA kernels, because SkyRL
# needs only its pure-PyTorch padding helpers; training runs with flash_attn=false (SDPA).
FROM nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3.12 python3.12-dev python3.12-venv \
    git curl ca-certificates build-essential libnuma-dev && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/0.9.4/install.sh | sh
ENV PATH=/root/.local/bin:$PATH UV_LINK_MODE=copy UV_PYTHON=python3.12
COPY SkyRL /opt/SkyRL
WORKDIR /opt/SkyRL
RUN uv sync --frozen --extra fsdp --no-install-package flash-attn
RUN cd / && FLASH_ATTENTION_SKIP_CUDA_BUILD=TRUE uv pip install --python /opt/SkyRL/.venv/bin/python --no-deps --no-build-isolation flash-attn==2.8.3.post1
ENV PATH=/opt/SkyRL/.venv/bin:$PATH
CMD ["/bin/bash"]
COPY flash_attn_2_cuda.py /opt/SkyRL/.venv/lib/python3.12/site-packages/flash_attn_2_cuda.py
