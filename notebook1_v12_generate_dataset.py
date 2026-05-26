#!/usr/bin/env python3
"""
notebook1_v11_generate_dataset.py
==================================
Dataset Generation — 10,000 LRF policies (v12 size categories)
Small: 1–25 rules | Medium: 26–100 rules | Large: 101–400 rules

Usage:
  python notebook1_v11_generate_dataset.py
  python notebook1_v11_generate_dataset.py --policies 10000 --workers 8
  python notebook1_v11_generate_dataset.py --policies 100000 --workers 8   # large run
"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# ── Configuration ─────────────────────────────────────────────────────────
N_POLICIES  = 10_000
N_WORKERS   = 8
BASE_SEED   = 2025
OUTPUT_FILE = "policies_v12.jsonl"
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", type=int, default=N_POLICIES)
    parser.add_argument("--workers",  type=int, default=N_WORKERS)
    parser.add_argument("--seed",     type=int, default=BASE_SEED)
    parser.add_argument("--output",   default=OUTPUT_FILE)
    args = parser.parse_args()

    sys.argv = [
        "lrf_trf_app_v12.py", "generate",
        "--policies", str(args.policies),
        "--workers",  str(args.workers),
        "--seed",     str(args.seed),
        "--output",   args.output,
    ]
    from lrf_trf_app_v12 import main
    main()
