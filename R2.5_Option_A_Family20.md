#!/usr/bin/env python3
"""
hicuts_sensitivity_v12.py
==========================
Reviewer 2.4 -- HiCuts parameter sensitivity analysis.

The main head-to-head (Table IV / classbench_results.json) uses HiCuts with
a single fixed hyperparameter setting (binth=8, spfac=4) from the original
paper. This script sweeps binth in {4, 8, 16} and spfac in {2, 4} (6
configurations) on the same synthetic-policy generator used elsewhere in
this repository (ordering_benchmark_v12.py's policy/packet generator), to
check whether the paper's qualitative conclusions -- HiCuts' lower match
latency but variable, data-dependent depth -- are robust to the choice of
hyperparameters.

Usage:
    python hicuts_sensitivity_v12.py --sizes 100,400 --trials 5
"""
from __future__ import annotations
import argparse, gc, json, random, statistics, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    Rule, PROTOCOLS, SINGLE_HOSTS, SUBNETS_24, COMMON_PORTS,
    COMMON_ICMP_TYPES, cidr_to_range, PORT_MAX, ICMP_TYPE_MAX,
)
import hicuts_baseline_v12 as hc


def _make_rule(rng, rule_id):
    src = rng.choice(SINGLE_HOSTS + SUBNETS_24 + ["ANY"])
    dst = rng.choice(SINGLE_HOSTS + SUBNETS_24 + ["ANY"])
    proto = rng.choices(["TCP", "UDP", "ICMP", "IP", "ANY"], weights=[40, 25, 10, 10, 15])[0]
    port = rng.choice(COMMON_ICMP_TYPES) if proto == "ICMP" else rng.choice(COMMON_PORTS)
    act = rng.choice(["ALLOW", "DENY"])
    ss, se = cidr_to_range(src) if src != "ANY" else (0, 2**32 - 1)
    ds, de = cidr_to_range(dst) if dst != "ANY" else (0, 2**32 - 1)
    return Rule(proto, ss, se, ds, de, port, port, act, rule_id=rule_id)


def build_policy(n, rng):
    rules = [_make_rule(rng, i) for i in range(n)]
    rules.append(Rule("ANY", 0, 2**32 - 1, 0, 2**32 - 1, 0, PORT_MAX, "DENY", rule_id=n))
    return rules


def gen_packets(n, rng):
    pkts = []
    for _ in range(n):
        proto = rng.choice(PROTOCOLS)
        port_max = ICMP_TYPE_MAX if proto == "ICMP" else PORT_MAX
        pkts.append({"protocol": proto, "src_ip": rng.randint(0, 2**32 - 1),
                     "dst_ip": rng.randint(0, 2**32 - 1), "dst_port": rng.randint(0, port_max)})
    return pkts


def run_one(rules, packets, binth, spfac):
    """Monkey-patch hicuts_baseline_v12's module-level BINTH/SPFAC, build, measure."""
    orig_binth, orig_spfac = hc.BINTH, hc.SPFAC
    hc.BINTH, hc.SPFAC = binth, spfac
    try:
        t0 = time.perf_counter()
        root = hc.build_hicuts(rules)
        build_ms = (time.perf_counter() - t0) * 1000
        stats = hc.hicuts_stats(root)
        tree_bytes = hc.hicuts_size_bytes(root)

        t0 = time.perf_counter()
        for p in packets:
            hc.hicuts_match(root, p)
        match_us = (time.perf_counter() - t0) / len(packets) * 1e6

        return {"depth": stats["depth"], "n_internal": stats["n_internal"],
                "n_leaves": stats["n_leaves"], "build_ms": build_ms,
                "match_us": match_us, "tree_bytes": tree_bytes}
    finally:
        hc.BINTH, hc.SPFAC = orig_binth, orig_spfac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="100,400")
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--packets", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=2025)
    ap.add_argument("--output", default="hicuts_sensitivity_v12_results.json")
    args = ap.parse_args()

    sizes = [int(x) for x in args.sizes.split(",")]
    binths = [4, 8, 16]
    spfacs = [2, 4]

    results = {"sizes": sizes, "trials": args.trials, "packets": args.packets,
               "seed": args.seed, "binths": binths, "spfacs": spfacs, "by_size": {}}

    t_start = time.time()
    for n in sizes:
        print(f"\n=== n={n} ===")
        cell = {}
        for binth in binths:
            for spfac in spfacs:
                key = f"binth{binth}_spfac{spfac}"
                depths, builds, matches, trees = [], [], [], []
                for trial in range(args.trials):
                    rng = random.Random(args.seed + trial * 1000 + n)
                    rules = build_policy(n, rng)
                    packets = gen_packets(args.packets, rng)
                    gc.collect()
                    r = run_one(rules, packets, binth, spfac)
                    depths.append(r["depth"]); builds.append(r["build_ms"])
                    matches.append(r["match_us"]); trees.append(r["tree_bytes"])
                cell[key] = {
                    "binth": binth, "spfac": spfac,
                    "depth_mean": statistics.mean(depths), "depth_min": min(depths), "depth_max": max(depths),
                    "build_ms_mean": statistics.mean(builds),
                    "match_us_mean": statistics.mean(matches),
                    "tree_bytes_mean": statistics.mean(trees),
                }
                print(f"  binth={binth:<3} spfac={spfac:<2}  depth={cell[key]['depth_mean']:.1f} "
                      f"(range {min(depths)}-{max(depths)})  match_us={cell[key]['match_us_mean']:.3f}  "
                      f"build_ms={cell[key]['build_ms_mean']:.2f}")
        results["by_size"][str(n)] = cell

    results["elapsed_s"] = time.time() - t_start
    json.dump(results, open(args.output, "w"), indent=2)
    print(f"\nWrote {args.output}  (elapsed {results['elapsed_s']:.1f}s)")


if __name__ == "__main__":
    main()
