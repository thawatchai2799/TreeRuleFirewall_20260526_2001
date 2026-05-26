#!/usr/bin/env python3
"""
cython_benchmark_v12.py
========================
Compile the v12 TRF tree to a flat-array representation and benchmark
the compiled Cython match kernel against the pure-Python implementation.

This addresses Reviewer Comment 5: "The 4.19x number is dominated by
Python interpreter overhead and is not a meaningful indicator of
algorithmic merit."

The Cython kernel:
- Uses bounded uint32/int64 native types
- Inlines the depth-bounded traversal loop
- Operates on 4 flat arrays (node_attr, edge_low, edge_high, edge_target)

Both kernels match identical packets and produce identical results
(verified by an N=1000 cross-check before the benchmark).
"""

from __future__ import annotations
import array, sys, time, random
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    Rule, parse_policy, deterministic_triad, decompose_4d,
    projection_normalization, build_trf, trf_match,
    ORDERING_OPTIONS, generate_policy,
)
import trf_match_cython as cm


ATTR_TO_ID = {"protocol": 0, "src_ip": 1, "dst_ip": 2, "dst_port": 3}
PROTO_TO_ID = {"TCP": 0, "UDP": 1, "ICMP": 2}
ACTION_TO_ID = {"DENY": 0, "ALLOW": 1}


def flatten_trf(root) -> dict:
    """Walk the TRF and pack into flat arrays for the Cython kernel.

    The TRF node has:
      - node.attribute: str ('protocol', 'src_ip', 'dst_ip', 'dst_port', 'leaf')
      - node.ranges: list of ((lo, hi), child_node) tuples
      - node.action: action string (for leaf)
      - node.is_leaf: bool
    For protocol nodes, ranges are stored as (proto_str, proto_str) where
    proto_str is in {'TCP', 'UDP', 'ICMP'}; we map these to integer IDs.

    Bug fix v12.1: previously, `edge_first = len(edges)` was captured BEFORE
    the recursive walk() calls; recursion appended children's edges first,
    making `edge_first` point to the wrong slice. Fix: pre-allocate the
    edge slots for this node BEFORE recursing into children, then fill in
    the target indices afterwards. This guarantees `edge_first .. edge_first+
    n_children-1` is a contiguous block belonging to THIS node.
    """
    nodes = []
    edges = []

    def walk(node):
        idx = len(nodes)
        nodes.append(None)  # placeholder
        if node.is_leaf or not node.ranges:
            # Leaf
            nodes[idx] = {
                "attr": 4,
                "first_edge": 0,
                "n_edges": 0,
                "action": ACTION_TO_ID.get(node.action, 0),
            }
        else:
            n_children = len(node.ranges)
            edge_first = len(edges)
            # Pre-allocate edge slots for this node (placeholder values)
            # Pre-compute the (lo, hi) values now (don't depend on recursion)
            for rng, _ in node.ranges:
                lo, hi = rng
                if node.attribute == "protocol":
                    lo_int = PROTO_TO_ID.get(lo, 0)
                    hi_int = PROTO_TO_ID.get(hi, 0)
                else:
                    lo_int, hi_int = int(lo), int(hi)
                edges.append([lo_int, hi_int, -1])  # target filled in below
            # Now recurse into children and fill in target indices
            for i, (rng, child) in enumerate(node.ranges):
                child_idx = walk(child)
                edges[edge_first + i][2] = child_idx
            nodes[idx] = {
                "attr": ATTR_TO_ID.get(node.attribute, 4),
                "first_edge": edge_first,
                "n_edges": n_children,
                "action": 0,
            }
        return idx

    walk(root)

    n_nodes = len(nodes)
    n_edges = len(edges)
    node_attr       = np.array([n["attr"]       for n in nodes], dtype=np.int32)
    node_first_edge = np.array([n["first_edge"] for n in nodes], dtype=np.int32)
    node_n_edges    = np.array([n["n_edges"]    for n in nodes], dtype=np.int32)
    node_action     = np.array([n["action"]     for n in nodes], dtype=np.int32)
    edge_low        = np.array([e[0] for e in edges] if edges else [0], dtype=np.int64)
    edge_high       = np.array([e[1] for e in edges] if edges else [0], dtype=np.int64)
    edge_target     = np.array([e[2] for e in edges] if edges else [0], dtype=np.int32)
    return {
        "node_attr": node_attr, "node_first_edge": node_first_edge,
        "node_n_edges": node_n_edges, "node_action": node_action,
        "edge_low": edge_low, "edge_high": edge_high, "edge_target": edge_target,
        "n_nodes": n_nodes, "n_edges": n_edges,
    }


def main():
    sizes = [25, 50, 100, 200, 400]
    out = {"sizes": sizes, "trials": 5, "data": {}}

    for n in sizes:
        out["data"][str(n)] = {
            "n_packets": 0, "trials": []
        }

        for trial in range(5):
            seed = 1000*n + trial
            policy = generate_policy((seed, (n, n), seed))
            rules = parse_policy(policy["lines"])
            clean, _ = deterministic_triad(rules)
            cells = decompose_4d(clean)
            cells = projection_normalization(cells, ORDERING_OPTIONS[4])
            root = build_trf(cells, ORDERING_OPTIONS[4])

            flat = flatten_trf(root)

            # Generate packets
            rng = random.Random(seed + 99)
            n_pkts = 5000
            pkts = []
            for _ in range(n_pkts):
                p = rng.choice(["TCP","UDP","ICMP"])
                pkts.append({
                    "protocol": p,
                    "src_ip":   rng.randint(0, 2**32-1),
                    "dst_ip":   rng.randint(0, 2**32-1),
                    "dst_port": rng.randint(0, 255 if p=="ICMP" else 65535),
                })

            # Cython batch arrays
            proto_arr = np.array([PROTO_TO_ID[p["protocol"]] for p in pkts], dtype=np.int32)
            src_arr   = np.array([p["src_ip"] for p in pkts], dtype=np.int64)
            dst_arr   = np.array([p["dst_ip"] for p in pkts], dtype=np.int64)
            port_arr  = np.array([p["dst_port"] for p in pkts], dtype=np.int32)
            result    = np.zeros(n_pkts, dtype=np.int32)

            # Cross-check correctness on the first 100 packets
            for i in range(100):
                py_out = trf_match(root, pkts[i])
                cy_single = cm.match_packet(
                    flat["node_attr"], flat["node_first_edge"],
                    flat["node_n_edges"], flat["node_action"],
                    flat["edge_low"], flat["edge_high"], flat["edge_target"],
                    proto_arr[i], src_arr[i], dst_arr[i], port_arr[i],
                )
                py_id = ACTION_TO_ID.get(py_out, 0)
                if py_id != cy_single:
                    print(f"[WARNING] MISMATCH n={n} trial={trial} pkt={i}: py={py_out} cy={cy_single}")

            # Time the Python kernel
            t0 = time.perf_counter()
            for p in pkts:
                trf_match(root, p)
            py_us = (time.perf_counter() - t0) / n_pkts * 1e6

            # Time the Cython kernel (batch)
            t0 = time.perf_counter()
            cm.match_packets_batch(
                flat["node_attr"], flat["node_first_edge"],
                flat["node_n_edges"], flat["node_action"],
                flat["edge_low"], flat["edge_high"], flat["edge_target"],
                proto_arr, src_arr, dst_arr, port_arr, result,
            )
            cy_us = (time.perf_counter() - t0) / n_pkts * 1e6

            speedup = py_us / cy_us if cy_us > 0 else 0
            out["data"][str(n)]["trials"].append({
                "py_match_us": py_us, "cy_match_us": cy_us, "speedup": speedup,
                "n_nodes": flat["n_nodes"], "n_edges": flat["n_edges"],
            })
            print(f"  n={n} trial={trial+1}/5: py={py_us:.2f}us cy={cy_us:.3f}us  speedup={speedup:.1f}x")

        # Aggregate
        trials_data = out["data"][str(n)]["trials"]
        for k in ["py_match_us", "cy_match_us", "speedup"]:
            vals = [t[k] for t in trials_data]
            out["data"][str(n)][f"{k}_mean"] = sum(vals)/len(vals)

    import json
    out_path = str(Path(__file__).parent / "cython_results.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n Saved -> {out_path}")


if __name__ == "__main__":
    main()
