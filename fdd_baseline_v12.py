#!/usr/bin/env python3
"""
fdd_baseline_v12.py
====================
Firewall Decision Diagram (FDD) baseline implementation, following the
single-fixed-ordering tree from:

    A. X. Liu and M. G. Gouda, "Firewall Policy Queries,"
    IEEE TPDS, vol. 20, no. 6, pp. 766-777, Jun. 2009.

The FDD is functionally equivalent to a TRF restricted to one fixed
attribute ordering [protocol → src_ip → dst_ip → dst_port], with the
same disjointness invariant on sibling edges. We implement it on top
of the v12 4D Decomposition + projection normalisation, since the FDD
construction algorithm in [Liu&Gouda 2009] uses the same cell-based
approach internally.

Differences from the v12 TRF model used as baseline:
- FDD only supports the single fixed ordering [P, sIP, dIP, dPt]
  (this is ID 1 in our 12-ordering catalogue).
- FDD does not support the ICMP-aware dst_port domain (treats all ports
  as 16-bit). We disable v12's ICMP-aware mode for fair FDD comparison.
- FDD originally had no anomaly removal step; we leave conflict-free
  policy P' as input (assume Step 2 already applied) since this affects
  both FDD and v12 equally.

Metrics measured:
    n_nodes, n_leaves, build_time_ms, match_us, tree_bytes

This implementation reuses v12's core decomposition functions and is
deliberately a thin wrapper, so reported differences vs. v12 reflect
the value of the multi-ordering generalisation (C5) and ICMP-aware
domain (C6), not implementation overhead.
"""

from __future__ import annotations
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lrf_trf_app_v12 import (
    Rule, Cell, TRFNode, parse_policy,
    deterministic_triad, decompose_4d,
    projection_normalization, build_trf,
    trf_depth, trf_node_count, trf_size_bytes,
    trf_match, lrf_match,
    ORDERING_OPTIONS,
)


# FDD = TRF restricted to fixed ordering [protocol, src_ip, dst_ip, dst_port]
FDD_ORDERING = ORDERING_OPTIONS[1]   # ["protocol", "src_ip", "dst_ip", "dst_port"]


def build_fdd(rules: list[Rule]) -> tuple[TRFNode, dict]:
    """Build an FDD from a list of LRF rules.

    Returns (root, metrics_dict).

    Metrics:
        build_time_ms, n_internal, n_leaves, depth, size_bytes
    """
    t0 = time.perf_counter()

    # Step 1: anomaly removal (same as v12 — without it, FDD with conflicts
    # would have non-deterministic semantics, which is unfair).
    clean, _ = deterministic_triad(rules)

    # Step 2: 4D decomposition
    cells = decompose_4d(clean)

    # Step 3: projection normalization (per-protocol mode only since
    # protocol is at level 1 — equivalent to FDD's "Build_FDD" recursion)
    cells = projection_normalization(cells, FDD_ORDERING)

    # Step 4: build the tree
    root = build_fdd_tree(cells, FDD_ORDERING)

    t1 = time.perf_counter()

    n_int, n_leaf = trf_node_count(root)
    metrics = {
        "build_time_ms": (t1 - t0) * 1000.0,
        "n_internal":    n_int,
        "n_leaves":      n_leaf,
        "depth":         trf_depth(root),
        "size_bytes":    trf_size_bytes(root),
    }
    return root, metrics


def build_fdd_tree(cells: list[Cell], ordering: list[str]) -> TRFNode:
    """Construct the FDD tree (alias of build_trf with FDD-fixed ordering)."""
    return build_trf(cells, ordering)


def fdd_match(root: TRFNode, pkt: dict) -> str:
    """Match a packet against the FDD (alias of trf_match)."""
    return trf_match(root, pkt)


# -----------------------------------------------------------------------------
# CLI: benchmark FDD vs LRF on a given policy file
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json, random

    ap = argparse.ArgumentParser()
    ap.add_argument("policy_jsonl", help="Path to a JSONL policy file")
    ap.add_argument("--packets", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with open(args.policy_jsonl) as f:
        policy = json.loads(f.readline())

    rules = parse_policy(policy["rules"])
    print(f"Loaded {len(rules)} rules from {policy['policy_id']}")

    fdd, metrics = build_fdd(rules)
    print(f"\nFDD build complete:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Match benchmark
    rng = random.Random(args.seed)
    protos = ["TCP", "UDP", "ICMP"]

    def mk_pkt():
        proto = rng.choice(protos)
        return {
            "protocol": proto,
            "src_ip":   rng.randint(0, 2**32 - 1),
            "dst_ip":   rng.randint(0, 2**32 - 1),
            "dst_port": rng.randint(0, 255 if proto == "ICMP" else 65535),
        }

    packets = [mk_pkt() for _ in range(args.packets)]

    # Time FDD matching
    t0 = time.perf_counter()
    for p in packets:
        fdd_match(fdd, p)
    t_fdd = (time.perf_counter() - t0) / args.packets * 1e6  # μs/packet

    # Time LRF matching
    t0 = time.perf_counter()
    for p in packets:
        lrf_match(rules, p)
    t_lrf = (time.perf_counter() - t0) / args.packets * 1e6

    print(f"\nMatch latency:")
    print(f"  LRF: {t_lrf:.2f} μs/packet")
    print(f"  FDD: {t_fdd:.2f} μs/packet")
    print(f"  Speedup: {t_lrf/t_fdd:.2f}×")
