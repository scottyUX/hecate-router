"""Drop the Linux file cache of E10's model weights, so CUDA on the GB10 can use that memory.

On the DGX Spark the GPU allocates from the same memory as Linux, but CUDA can
only use memory that is free, not memory Linux holds as file cache. After the
student and the advisor load, their weight files (about 45 GB) sit in that
cache, and G1 attempt 6 failed to create a CUDA context with 1.4-3.8 GB free
and 34-48 GB cached. posix_fadvise(DONTNEED) asks the kernel to drop a file's
clean cached pages; it needs only read access to the file, not sudo, and it
touches nothing but these files' cache (they are read again from disk if
needed).

  python3 trim_weight_cache.py <dir>            once
  python3 trim_weight_cache.py <dir> --every 10 every 10 s until stopped
"""

import argparse
import os
import time


def trim(root: str) -> int:
    n = 0
    for dirpath, _, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            try:
                fd = os.open(path, os.O_RDONLY)
            except OSError:
                continue
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                n += 1
            except OSError:
                pass
            finally:
                os.close(fd)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--every", type=float, default=0)
    args = ap.parse_args()
    while True:
        n = trim(args.root)
        if not args.every:
            print(f"trimmed the cache of {n} files under {args.root}", flush=True)
            return
        time.sleep(args.every)


if __name__ == "__main__":
    main()
