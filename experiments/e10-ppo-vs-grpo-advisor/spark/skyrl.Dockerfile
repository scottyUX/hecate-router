# E10 G0d: SkyRL (advisor-models fork) on the Spark, on top of vLLM 0.20.0
# (torch 2.11 + CUDA 13, built for GB10). The x86 pins in SkyRL (torch 2.7/cu128,
# vLLM 0.9.2, flash-attn and flashinfer wheels) are not used.
FROM vllm/vllm-openai:v0.20.0
RUN pip install --no-cache-dir loguru tqdm tensorboard func_timeout hydra-core==1.3.2 accelerate \
    torchdata omegaconf "ray[default]==2.48.0" peft debugpy==1.8.0 hf_transfer wandb datasets \
    tensordict jaxtyping polars
COPY skyrl-gym /opt/skyrl/skyrl-gym
COPY skyrl-train /opt/skyrl/skyrl-train
RUN pip install --no-cache-dir --no-deps -e /opt/skyrl/skyrl-gym -e /opt/skyrl/skyrl-train
ENTRYPOINT []
CMD ["/bin/bash"]
