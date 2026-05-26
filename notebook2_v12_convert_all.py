#!/usr/bin/env python3
"""
notebook2_v11_convert_all.py
============================
Batch LRF→TRF Conversion (v12)
Small: 1–25 | Medium: 26–100 | Large: 101–400 rules

Worker strategy:
  - Small  policies: use full worker count (fast)
  - Medium policies: reduce workers to avoid RAM pressure
  - Large  policies: single-worker or 2-worker to prevent OOM

Usage:
  python notebook2_v11_convert_all.py
  python notebook2_v11_convert_all.py --dataset policies_v12.jsonl
"""
import argparse, json, sys, time
from dataclasses import asdict
from multiprocessing import Pool, cpu_count
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import convert_policy, N_ORDERINGS

# ── Configuration ─────────────────────────────────────────────────────────
DATASET_FILE  = "policies_v12.jsonl"
OUTPUT_REPORT = "conversion_reports_v12.jsonl"
ORDERING_ID   = 4
WORKERS_SMALL  = min(8, cpu_count())
WORKERS_MEDIUM = min(4, cpu_count())
WORKERS_LARGE  = min(2, cpu_count())   # Large policies need more RAM
# ─────────────────────────────────────────────────────────────────────────

def _get_category(n_rules):
    if n_rules <= 25:  return "small"
    if n_rules <= 100: return "medium"
    return "large"

def _convert_one(args):
    policy_dict, ordering_id = args
    lines = policy_dict["lines"]
    pid   = policy_dict["policy_id"]
    try:
        _, report, _ = convert_policy(lines, policy_id=pid, ordering_id=ordering_id)
        return asdict(report)
    except Exception as e:
        return {"policy_id": pid, "error": str(e),
                "size_category": _get_category(len(lines))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",  default=DATASET_FILE)
    parser.add_argument("--output",   default=OUTPUT_REPORT)
    parser.add_argument("--ordering", type=int, default=ORDERING_ID, choices=range(1, N_ORDERINGS+1))
    args = parser.parse_args()

    print(f"Batch Conversion v12 (Algorithm Only — No ML)")
    print(f"Dataset : {args.dataset}")
    print(f"Ordering: Option {args.ordering}")
    print(f"Workers : Small={WORKERS_SMALL}, Medium={WORKERS_MEDIUM}, Large={WORKERS_LARGE}")

    with open(args.dataset) as fh:
        all_policies = [json.loads(l) for l in fh]

    # Split by category
    cats = {"small":[], "medium":[], "large":[]}
    for p in all_policies:
        n = p.get("n_rules", len(p["lines"]))
        cats[_get_category(n)].append(p)

    print(f"\nDataset: {len(all_policies):,} total")
    for cat, pols in cats.items():
        print(f"  {cat.capitalize():8s}: {len(pols):,} policies")
    print()

    t0 = time.perf_counter()
    n_ok = n_err = 0

    with open(args.output, "w") as out:
        for cat, workers in [("small", WORKERS_SMALL),
                              ("medium", WORKERS_MEDIUM),
                              ("large", WORKERS_LARGE)]:
            pols = cats[cat]
            if not pols:
                continue
            print(f"Converting {cat} policies ({len(pols):,}) with {workers} workers...")
            task_args = [(p, args.ordering) for p in pols]
            chunk = max(1, len(pols)//(workers*4))
            with Pool(processes=workers) as pool:
                for i, rep in enumerate(
                        pool.imap(_convert_one, task_args, chunksize=chunk)):
                    out.write(json.dumps(rep)+"\n")
                    if "error" in rep: n_err += 1
                    else: n_ok += 1
                    if (i+1) % max(1, len(pols)//10) == 0:
                        el = time.perf_counter()-t0
                        print(f"  [{cat}] {i+1}/{len(pols)}  "
                              f"OK={n_ok:,}  ERR={n_err}  {el:.0f}s elapsed",
                              flush=True)
            print(f"  [{cat}] done ✅")

    elapsed = time.perf_counter()-t0
    print(f"\nTotal: {n_ok:,} OK, {n_err} errors in {elapsed:.1f}s")
    print(f"Reports → {args.output}")

if __name__ == "__main__":
    main()
