"""Placeholder for flash-attn CUDA kernels, which are not built for the GB10 (E10, A2).

SkyRL imports flash_attn only for its pure-PyTorch padding helpers; training runs
with trainer.flash_attn=false (PyTorch SDPA). Any call into the real kernels fails
here loudly instead of running something else silently.
"""


def __getattr__(name):
    raise RuntimeError(
        f"flash_attn_2_cuda.{name} called, but flash-attn CUDA kernels are not built on this "
        "image (E10 Spark setup). Set trainer.flash_attn=false or build flash-attn for sm_120."
    )
