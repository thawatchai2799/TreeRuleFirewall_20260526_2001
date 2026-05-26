#!/usr/bin/env python3
"""
classbench_comparative_benchmark_v12.py
=========================================
Run TRF (v12), FDD, HiCuts, and LRF on real-world ClassBench-ng rule sets
and report build time, depth, internal nodes, leaf count, deployed memory,
and per-packet match latency for direct head-to-head comparison.

Output: classbench_results.json
"""

from __future__ import annotations
import json, random, sys, time, gc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    parse_policy, deterministic_triad, decompose_4d,
    projection_normalization, build_trf,
    trf_depth, trf_node_count, trf_size_bytes, trf_match,
    lrf_match, ORDERING_OPTIONS,
)
from fdd_baseline_v12 import build_fdd, fdd_match
from hicuts_baseline_v12 import (
    build_hicuts, hicuts_stats, hicuts_size_bytes, hicuts_match,
)
from classbench_loader_v12 import load_classbench_file


# Default location: clone https://github.com/neurocuts/neurocuts.git
# at the same level as this directory, or override via env var V12_CLASSBENCH_DIR
import os
CLASSBENCH_DIR = Path(os.environ.get("V12_CLASSBENCH_DIR",
                  str(Path(__file__).parent.parent / "neurocuts" / "classbench")))

# Subset of rule sets to test. We use 1k size since 10k+ takes hours in
# pure Python; the 1k size is sufficient to cover the n ∈ [50, 1000] range.
RULE_SETS = [
    ("acl1_1k", "ACL"),
    ("acl2_1k", "ACL"),
    ("acl3_1k", "ACL"),
    ("fw1_1k",  "FW"),
    ("fw2_1k",  "FW"),
    ("fw3_1k",  "FW"),
    ("ipc1_1k", "IPC"),
    ("ipc2_1k", "IPC"),
]

# Sub-sample sizes for the fairness comparison
SAMPLE_SIZES = [50, 100, 200, 400]  # rule counts to extract from each ruleset


def time_match(matcher, pkts) -> float:
    """Time the matcher over packets, return μs/packet (mean)."""
    t0 = time.perf_counter()
    for p in pkts:
        matcher(p)
    return (time.perf_counter() - t0) / len(pkts) * 1e6


def benchmark_one(rules_text: list[str], n_packets: int = 500,
                  seed: int = 42) -> dict:
    """Run all four matchers (LRF, TRF, FDD, HiCuts) on one rule set."""
    rules = parse_policy(rules_text)

    rng = random.Random(seed)
    protos = ["TCP", "UDP", "ICMP"]
    def mk_pkt():
        proto = rng.choice(protos)
        return {"protocol": proto,
                "src_ip":   rng.randint(0, 2**32 - 1),
                "dst_ip":   rng.randint(0, 2**32 - 1),
                "dst_port": rng.randint(0, 255 if proto == "ICMP" else 65535)}
    pkts = [mk_pkt() for _ in range(n_packets)]

    out = {"n_rules": len(rules)}

    # --- LRF baseline ---
    t0 = time.perf_counter()
    out["lrf_match_us"] = time_match(lambda p: lrf_match(rules, p), pkts)
    out["lrf_build_ms"] = 0.0  # LRF has no build phase
    out["lrf_depth"]    = None
    out["lrf_nodes"]    = len(rules)
    out["lrf_size_kb"]  = sys_recursive_size(rules) / 1024.0

    # --- TRF (v12) with default ordering 4 ---
    t0 = time.perf_counter()
    clean, _   = deterministic_triad(rules)
    cells      = decompose_4d(clean)
    norm_cells = projection_normalization(cells, ORDERING_OPTIONS[4])
    trf_root   = build_trf(norm_cells, ORDERING_OPTIONS[4])
    out["trf_build_ms"] = (time.perf_counter() - t0) * 1000.0
    n_int, n_leaf       = trf_node_count(trf_root)
    out["trf_depth"]    = trf_depth(trf_root)
    out["trf_internal"] = n_int
    out["trf_leaves"]   = n_leaf
    out["trf_size_kb"]  = trf_size_bytes(trf_root) / 1024.0
    out["trf_match_us"] = time_match(lambda p: trf_match(trf_root, p), pkts)
    out["trf_speedup"]  = out["lrf_match_us"] / out["trf_match_us"]

    # --- FDD baseline (TRF restricted to ordering 1) ---
    fdd_root, fdd_metrics = build_fdd(rules)
    out["fdd_build_ms"] = fdd_metrics["build_time_ms"]
    out["fdd_depth"]    = fdd_metrics["depth"]
    out["fdd_internal"] = fdd_metrics["n_internal"]
    out["fdd_leaves"]   = fdd_metrics["n_leaves"]
    out["fdd_size_kb"]  = fdd_metrics["size_bytes"] / 1024.0
    out["fdd_match_us"] = time_match(lambda p: fdd_match(fdd_root, p), pkts)
    out["fdd_speedup"]  = out["lrf_match_us"] / out["fdd_match_us"]

    # --- HiCuts baseline ---
    t0 = time.perf_counter()
    hi_root = build_hicuts(rules)
    out["hicuts_build_ms"] = (time.perf_counter() - t0) * 1000.0
    hi_stats = hicuts_stats(hi_root)
    out["hicuts_depth"]    = hi_stats["depth"]
    out["hicuts_internal"] = hi_stats["n_internal"]
    out["hicuts_leaves"]   = hi_stats["n_leaves"]
    out["hicuts_total_storage"] = hi_stats["total_rule_storage"]
    out["hicuts_size_kb"]  = hicuts_size_bytes(hi_root) / 1024.0
    out["hicuts_match_us"] = time_match(lambda p: hicuts_match(hi_root, p), pkts)
    out["hicuts_speedup"]  = out["lrf_match_us"] / out["hicuts_match_us"]

    return out


def sys_recursive_size(obj):
    """Recursive sizeof for LRF rules list."""
    import sys as _sys
    seen = set()
    def s(x):
        if id(x) in seen: return 0
        seen.add(id(x))
        sz = _sys.getsizeof(x)
        if isinstance(x, list):
            sz += sum(s(i) for i in x)
        return sz
    return s(obj)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--classbench-dir", type=Path, default=CLASSBENCH_DIR,
                        help=f"Directory containing ClassBench-ng rule files "
                             f"(default: {CLASSBENCH_DIR}). Override with env "
                             f"variable V12_CLASSBENCH_DIR.")
    parser.add_argument("--sizes", default="50,100,200,400",
                        help="Comma-separated rule-count samples per ruleset "
                             "(default: '50,100,200,400')")
    parser.add_argument("--packets", type=int, default=500,
                        help="Test packets per case (default: 500)")
    parser.add_argument("--output", default=None,
                        help="Output JSON file (default: classbench_results.json next to script)")
    args = parser.parse_args()

    cb_dir = args.classbench_dir
    sample_sizes = [int(s) for s in args.sizes.split(",")]
    n_packets = args.packets
    out_path = args.output or str(Path(__file__).parent / "classbench_results.json")

    if not cb_dir.exists():
        print(f"❌ ClassBench directory not found: {cb_dir}")
        print(f"   Either:")
        print(f"   1. git clone https://github.com/neurocuts/neurocuts.git")
        print(f"      at the same level as this directory, or")
        print(f"   2. set V12_CLASSBENCH_DIR=/path/to/neurocuts/classbench, or")
        print(f"   3. pass --classbench-dir /path/to/classbench")
        sys.exit(1)

    results = {"by_ruleset": {}, "config": {
        "classbench_dir": str(cb_dir), "sizes": sample_sizes, "packets": n_packets,
    }}

    for fname, category in RULE_SETS:
        fpath = cb_dir / fname
        if not fpath.exists():
            print(f"⚠ Skipping {fname}, not found at {fpath}")
            continue
        results["by_ruleset"][fname] = {"category": category, "by_size": {}}

        for size in sample_sizes:
            print(f"=== {fname} (n={size}) ===")
            try:
                rules_text = load_classbench_file(
                    fpath, max_rules=size, deny_ratio=0.20, seed=42)
                out = benchmark_one(rules_text, n_packets=n_packets)
                results["by_ruleset"][fname]["by_size"][str(size)] = out
                print(f"  TRF: build={out['trf_build_ms']:.1f}ms, "
                      f"depth={out['trf_depth']}, match={out['trf_match_us']:.2f}μs "
                      f"(speedup={out['trf_speedup']:.2f}×)")
                print(f"  FDD: build={out['fdd_build_ms']:.1f}ms, "
                      f"depth={out['fdd_depth']}, match={out['fdd_match_us']:.2f}μs "
                      f"(speedup={out['fdd_speedup']:.2f}×)")
                print(f"  HiCuts: build={out['hicuts_build_ms']:.1f}ms, "
                      f"depth={out['hicuts_depth']}, match={out['hicuts_match_us']:.2f}μs "
                      f"(speedup={out['hicuts_speedup']:.2f}×)")
            except Exception as e:
                print(f"  ❌ Error: {e}")
                import traceback; traceback.print_exc()
            gc.collect()

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results → {out_path}")


if __name__ == "__main__":
    main()
