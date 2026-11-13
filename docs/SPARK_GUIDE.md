# Working on the lab's DGX Spark

For any lab member with an account on the Spark, whatever the project. Your
project's own spec or runbook says what to run; this guide says how to use
the machine. If the two disagree, stop and ask Scott.

## The machine

| | |
|---|---|
| Host | `spark-c606`, Tailscale `100.100.25.117` |
| Hardware | NVIDIA DGX Spark: GB10 GPU (compute capability 12.1), 20 ARM cores, 128 GB memory shared by CPU and GPU |
| OS | Ubuntu 24.04, **aarch64 (ARM)** |
| Driver / CUDA | 580.126.09, CUDA 13 |
| Disk | One 3.7 TB disk, shared by everyone (~620 GB free on 13 Nov) |

Two things that differ from a usual GPU box:

- **It is ARM, not x86.** Many pip wheels and Docker images exist only for
  x86. Prefer NVIDIA NGC containers (`nvcr.io/nvidia/...`), and check that a
  package has an `aarch64` build before relying on it.
- **Memory is unified.** The GPU and CPU share the same 128 GB.
  `nvidia-smi` reports GPU memory as "Not Supported"; use `free -h` to see
  what is free.

## Logging in

1. Run Tailscale on your laptop, signed in with your UCSC account.
2. Add to `~/.ssh/config` on your laptop:
   ```
   Host spark
     HostName 100.100.25.117
     User <your-username>
   ```
3. `ssh spark`. There is no password: you sign in with your SSH key. If it
   asks for a password or times out, tell Scott; do not try to set one.
4. Check: `id` lists `docker`.

## Rules

- **Your own account only.** Never use someone else's key or login, and
  never share yours.
- **No `sudo`, reboots, sleep, firmware updates (`fwupdmgr`) or driver
  changes.** Your account has no sudo, and nothing should need it. If
  something seems to, ask Scott.
- **Run only what your project's spec authorizes.** In this lab the spec
  comes before the code and the runs; a run that is not in it, or in an
  amendment to it, waits.
- **No secrets in git, logs or shared folders.** Keep keys in a `.env` file
  in your home folder, readable only by you (`chmod 600`).

## Sharing the machine

Several people and projects use the Spark, and it has one GPU.

- **Before starting anything on the GPU,** check `free -h`, `docker ps`
  and `htop`. If a big job is running, do not start another; ask on Slack.
- **Announce long GPU jobs** (more than an hour) on Slack before starting
  them, with roughly how long and how much memory.
- **Stop what you start.** Stop servers and containers when you are done
  (`docker stop <name>`). Do not leave models loaded in memory overnight
  unless a run needs it.
- **Do not touch what is not yours:** other people's containers, images,
  tmux sessions, volumes or files. One long-running container
  (`diflh-ollama`) belongs to another project.

## Running jobs

- **Long jobs in tmux, output to a log file,** so they survive a dropped SSH
  connection:
  ```bash
  mkdir -p ~/logs
  tmux new -d -s myjob 'python train.py > ~/logs/myjob.log 2>&1'
  tail -n 50 ~/logs/myjob.log
  tmux ls
  ```
- **Docker with the GPU:** `docker run --rm --gpus all --ipc=host ...`.
  Name your containers (`--name yourname-job`) so others can tell whose they
  are.
- **Images already pulled,** usable by anyone in the `docker` group:
  `nvcr.io/nvidia/pytorch:26.04-py3`, `nvcr.io/nvidia/pytorch:25.11-py3`,
  `vllm/vllm-openai:v0.20.0`, `nvcr.io/nvidia/vllm:26.02-py3`,
  `nvcr.io/nvidia/cuda:13.0.1-devel-ubuntu24.04`. Use one of these before
  pulling another 20 GB image.
- **Python outside Docker:** the system Python is 3.12. Use a virtual
  environment in your home folder (`python3 -m venv ~/venvs/myproj`); do not
  install packages system-wide.

## Files and disk

- **Your home folder is private** (other users cannot read it). Put code in
  `~/work/`, logs in `~/logs/`.
- **Get code with git** (`git clone`). If you copy from your laptop with
  rsync, leave out virtual environments and build folders, which are useless
  on ARM: `rsync -az --exclude .git --exclude .venv --exclude node_modules
  ./ spark:~/work/myproj/`.
- **Check `df -h /` before any large download** (model weights, datasets).
  Download each model once: set `HF_HOME` to a folder in your home, or ask
  Scott whether a shared Docker volume already has it.
- **Clean up** checkpoints and images you no longer need. The disk is shared.
- **Copy results off the Spark.** It has no backups and no cloud
  credentials. Keep anything you need (results, final checkpoints) in git,
  or copy it to your laptop or the lab bucket through Scott.

## When something goes wrong

Stop, keep the log, and tell Scott on Slack: what you ran, when, and the
error. Do not work around a problem by changing a setting your spec fixes,
and do not restart anything that is not yours.
