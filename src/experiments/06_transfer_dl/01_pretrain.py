"""Pretrain the shared cross-home backbone (experiment 06, milestone M2/M3 input).

One seq2seq net per device, trained on the 20 development homes' PRE-SPLIT spans
only. The 7 holdout houses are never loaded here.

Usage:
  uv run python3 src/experiments/06_transfer_dl/01_pretrain.py
      [--devices kettle,...] [--homes tag,...] [--epochs N]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import transfer_lib as tl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--devices", default=",".join(tl.DEVICES))
    ap.add_argument("--homes", default="", help="donor subset (tags)")
    ap.add_argument("--epochs", type=int, default=0, help="0 = S2S default")
    a = ap.parse_args()

    if a.epochs:
        tl.S2S["epochs"] = a.epochs
    torch.set_num_threads(4)  # the box is shared; 8 threads oversubscribe it

    recs = tl.donor_homes()
    if a.homes:
        want = set(a.homes.split(","))
        recs = [h for h in recs if h["tag"] in want]
    print(f"pretrain: {len(recs)} donor homes (dev group), "
          f"{tl.S2S['epochs']} epochs, seed {tl.S2S['seed']}", flush=True)
    t0 = time.time()
    homes = tl.load_homes(recs)
    print(f"loaded {len(homes)} homes in {time.time() - t0:.0f}s", flush=True)

    for dev in a.devices.split(","):
        t1 = time.time()
        got = tl.build_windows(homes, dev, tl.S2S["seed"])
        if got is None:
            print(f"  {dev}: no donor windows, skipped", flush=True)
            continue
        X, Y, used = got
        net = tl.s2s_train(X, Y)
        path = tl.save_net(net, dev)
        print(f"  saved {path.name} ({len(used)} homes) "
              f"in {time.time() - t1:.0f}s", flush=True)
    print(f"pretrain done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
