#!/usr/bin/env python3
"""
notebook3_v11_run_benchmarks.py
================================
Run All Four Verification Benchmarks (v12)
Small: 1–25 | Medium: 26–100 | Large: 101–400 rules

Default sample sizes match a 10,000-policy dataset.

Steps:
  1. Semantic Fidelity  (Theorem 1) — semantic_verify_v12.py
  2. Anomaly Detection  (Proposition 2) — anomaly_benchmark_v12.py
  3. Scalability        (LRF vs TRF) — scalability_benchmark_v12.py
  4. Ordering Compare   (12 orders)  — ordering_benchmark_v12.py  [NEW]

Usage:
  python notebook3_v11_run_benchmarks.py --dataset policies_v12.jsonl
  python notebook3_v11_run_benchmarks.py --dataset policies_v12.jsonl --quick
  python notebook3_v11_run_benchmarks.py --dataset policies_v12.jsonl --test-large
  python notebook3_v11_run_benchmarks.py --dataset policies_v12.jsonl --skip-ordering
"""
import argparse, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import N_ORDERINGS


def run(cmd, label):
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")
    t0 = time.perf_counter()
    result = subprocess.run([sys.executable]+cmd, check=False)
    el = time.perf_counter()-t0
    ok = "✅ OK" if result.returncode==0 else "❌ ERROR"
    print(f"\n{label}: {ok}  ({el:.1f}s)")
    return result.returncode==0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",    default="policies_v12.jsonl")
    parser.add_argument("--policies",   type=int, default=None,
                        help="Number of policies in dataset to verify in Step 1 "
                             "(default: auto-detect from --dataset, fall back to 5000)")
    parser.add_argument("--anom-trials", type=int, default=None,
                        help="Trials per anomaly config (default: 500, or 100 in --quick)")
    parser.add_argument("--scale-trials", type=int, default=None,
                        help="Trials in scalability benchmark (default: 10)")
    parser.add_argument("--ord-trials", type=int, default=None,
                        help="Trials in ordering benchmark (default: 5)")
    parser.add_argument("--quick",      action="store_true",
                        help="Quick mode: fewer policies/trials")
    parser.add_argument("--test-large", action="store_true",
                        help="Include Large category in anomaly benchmark")
    parser.add_argument("--ordering",   type=int, default=4, choices=range(1, N_ORDERINGS+1))
    parser.add_argument("--skip-ordering", action="store_true",
                        help="Skip Step 4 (ordering benchmark; saves time)")
    args = parser.parse_args()

    # Auto-detect policy count from dataset file if --policies not given.
    if args.policies is None:
        try:
            with open(args.dataset) as _f:
                detected = sum(1 for _ in _f)
            args.policies = detected
            print(f"[notebook3] Auto-detected {detected:,} policies in {args.dataset}")
        except FileNotFoundError:
            args.policies = 10000
            print(f"[notebook3] Dataset not found; assuming 10000 policies")

    # Default sample sizes scale with --policies / --quick.
    if args.quick:
        sem_n     = str(min(200, args.policies))
        anom_n    = str(args.anom_trials  or 100)
        scale_n   = "100"
        pkts      = "1000"
        trials    = str(args.scale_trials or 3)
        ord_sizes = "25,50"
        ord_trials = str(args.ord_trials  or 3)
        ord_pkts  = "500"
    else:
        sem_n     = str(args.policies)                 # use full dataset
        anom_n    = str(args.anom_trials  or 500)
        scale_n   = "400"
        pkts      = "5000"
        trials    = str(args.scale_trials or 10)
        ord_sizes = "50,100,200,400"
        ord_trials = str(args.ord_trials  or 5)
        ord_pkts  = "2000"

    print(f"LRF→TRF Benchmark Suite v12 (Algorithm Only — No ML)")
    print(f"Dataset  : {args.dataset}")
    print(f"Mode     : {'QUICK' if args.quick else 'FULL'}")
    print(f"Ordering : Option {args.ordering} (single-ordering benchmarks)")
    print(f"Sizes    : Small 1–25 | Medium 26–100 | Large 101–400")

    all_ok = True

    # Step 1
    ok = run([
        "semantic_verify_v12.py",
        "--dataset",        args.dataset,
        "--policies",       sem_n,
        "--ordering",       str(args.ordering),
        "--random-packets", pkts,
    ], "Step 1: Semantic Fidelity — Theorem 1 (per size category)")
    all_ok = all_ok and ok

    # Step 2
    anom_cmd = [
        "anomaly_benchmark_v12.py",
        "--trials", anom_n,
    ]
    if args.test_large:
        anom_cmd.append("--test-large")
    ok = run(anom_cmd, "Step 2: Anomaly Detection — Proposition 2 (per size category)")
    all_ok = all_ok and ok

    # Step 3
    ok = run([
        "scalability_benchmark_v12.py",
        "--max-n",   scale_n,
        "--trials",  trials,
        "--packets", pkts,
        "--ordering",str(args.ordering),
    ], "Step 3: Scalability & Speedup (single ordering)")
    all_ok = all_ok and ok

    # Step 4 — Ordering Comparison (NEW)
    if not args.skip_ordering:
        ok = run([
            "ordering_benchmark_v12.py",
            "--sizes",   ord_sizes,
            "--trials",  ord_trials,
            "--packets", ord_pkts,
        ], "Step 4: Ordering Comparison (12 orderings × multi-metric)")
        all_ok = all_ok and ok
    else:
        print("\n[skipped] Step 4: Ordering Comparison (--skip-ordering)")

    print(f"\n{'='*65}")
    print(f"  All benchmarks: {'✅ ALL PASSED' if all_ok else '❌ SOME FAILED'}")
    print(f"{'='*65}")
    print("\nOutput files:")
    files_to_check = ["semantic_verify_v12_results.json",
                      "anomaly_benchmark_v12_results.json",
                      "scalability_v12_results.json"]
    if not args.skip_ordering:
        files_to_check.append("ordering_benchmark_v12_results.json")
    for f in files_to_check:
        e = "✅" if Path(f).exists() else "❌ (not found)"
        print(f"  {e}  {f}")

if __name__ == "__main__":
    main()
