#!/usr/bin/env bash
# E10 A2 toolchain check: 3 GRPO steps with LoRA (rank 32, alpha 32) of the upstream
# SkyRL GSM8K example, Qwen2.5-0.5B-Instruct, one GB10. Not an E10 arm.
set -euxo pipefail
cd /opt/SkyRL
D=/w/toolchain/data
python examples/train/gsm8k/gsm8k_dataset.py --output_dir $D/full
python - <<PY
import pandas as pd
pd.read_parquet("$D/full/train.parquet").head(48).to_parquet("$D/train48.parquet")
pd.read_parquet("$D/full/validation.parquet").head(32).to_parquet("$D/val32.parquet")
PY
python -m skyrl.train.entrypoints.main_base \
  data.train_data="['$D/train48.parquet']" data.val_data="['$D/val32.parquet']" \
  trainer.algorithm.advantage_estimator=grpo \
  trainer.policy.model.path=Qwen/Qwen2.5-0.5B-Instruct \
  trainer.policy.model.lora.rank=32 trainer.policy.model.lora.alpha=32 \
  trainer.placement.colocate_all=true trainer.strategy=fsdp \
  trainer.placement.policy_num_gpus_per_node=1 trainer.placement.ref_num_gpus_per_node=1 \
  generator.inference_engine.num_engines=1 generator.inference_engine.tensor_parallel_size=1 \
  trainer.flash_attn=false trainer.remove_microbatch_padding=false \
  trainer.epochs=1 trainer.train_batch_size=16 trainer.policy_mini_batch_size=16 \
  trainer.micro_forward_batch_size_per_gpu=8 trainer.micro_train_batch_size_per_gpu=8 \
  trainer.update_epochs_per_batch=1 trainer.eval_before_train=false trainer.eval_interval=-1 \
  trainer.ckpt_interval=3 trainer.ckpt_path=/w/toolchain/ckpt trainer.export_path=/w/toolchain/export \
  trainer.max_prompt_length=512 generator.sampling_params.max_generate_length=512 \
  trainer.policy.optimizer_config.lr=3.0e-5 trainer.algorithm.use_kl_loss=true \
  generator.inference_engine.backend=vllm generator.inference_engine.run_engines_locally=true \
  generator.inference_engine.weight_sync_backend=nccl generator.batched=true \
  generator.inference_engine.gpu_memory_utilization=0.4 \
  environment.env_class=gsm8k generator.n_samples_per_prompt=4 \
  trainer.logger=console trainer.project_name=e10_toolchain trainer.run_name=gsm8k_0.5b_lora_grpo \
  trainer.resume_mode=null
