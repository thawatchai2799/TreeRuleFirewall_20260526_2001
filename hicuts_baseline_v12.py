#!/usr/bin/env python3
"""
hicuts_baseline_v12.py
=======================
Simplified HiCuts (Hierarchical Intelligent Cuttings) baseline implementation,
following:

    P. Gupta and N. McKeown, "Packet Classification using Hierarchical
    Intelligent Cuttings," IEEE Micro, vol. 20, no. 1, pp. 34-41, 2000.

HiCuts builds a multi-way decision tree over the 5-tuple search space.
At each internal node, one dimension is chosen and cut into k partitions.
A leaf stores up to `binth` rules and is searched linearly.

This is a SIMPLIFIED reference implementation for baseline comparison only:
- Uses the original "max-distinct-children" heuristic for dimension choice.
- Cut count k is chosen by the space-measure-function (spmf) heuristic
  with spfac = 4 (recommended in the paper).
- Leaves hold ≤ binth = 8 rules (paper's default).
- Operates on the 4-tuple (protocol, src_ip, dst_ip, dst_port) used by v12
  to enable apples-to-apples comparison.
- src_port dimension is dropped to match v12's 4-attribute model.

Caveats vs. production HiCuts:
- We do not implement HyperCuts' multi-dimension cuts at one node.
- We do not implement EffiCuts' rule-replication-aware grouping.
- Memory measurements use Python sys.getsizeof and are therefore an
  upper bound, not a tight measurement; the paper's TCAM-equivalent
  metric is approximated as (n_internal_nodes + sum_of_leaf_lists).

Metrics measured:
    n_internal_nodes, n_leaves, total_rule_storage,
    build_time_ms, match_us, tree_bytes
"""

from __future__ import annotations
import sys, time, sys as _sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import Rule, parse_policy, lrf_match, PROTO_SUPERS

# HiCuts hyperparameters from Gupta & McKeown (2000)
BINTH  = 8     # Max rules per leaf
SPFAC  = 4     # Space factor for choosing cut count
DIM_MAX = {
    "protocol": 4,         # 3 atomic + 'IP/ANY' wildcard, encoded as 0..3
    "src_ip":   2**32,
    "dst_ip":   2**32,
    "dst_port": 65536,     # Note: HiCuts treats this as 16-bit, regardless of protocol
}
DIMENSIONS = ["protocol", "src_ip", "dst_ip", "dst_port"]


@dataclass
class HiCutsNode:
    is_leaf: bool = True
    rules: list[Rule] = field(default_factory=list)
    cut_dim: Optional[str] = None      # which dim is cut (internal nodes only)
    children: list = field(default_factory=list)  # list of HiCutsNode
    range_start: int = 0
    range_end:   int = 0


def _proto_atom_id(p: str) -> set[int]:
    """Return the set of protocol-atom integer IDs covered by a rule."""
    atoms = PROTO_SUPERS[p]
    ids = set()
    if "TCP"  in atoms: ids.add(0)
    if "UDP"  in atoms: ids.add(1)
    if "ICMP" in atoms: ids.add(2)
    return ids


def _rule_range_on_dim(rule: Rule, dim: str) -> tuple[int, int]:
    """Return (lo, hi) inclusive range of a rule on the given dimension."""
    if dim == "protocol":
        ids = sorted(_proto_atom_id(rule.protocol))
        return (min(ids), max(ids)) if ids else (0, 2)
    if dim == "src_ip":
        return (rule.src_start, rule.src_end)
    if dim == "dst_ip":
        return (rule.dst_start, rule.dst_end)
    if dim == "dst_port":
        return (rule.port_start, rule.port_end)
    raise ValueError(dim)


def _packet_dim_value(pkt: dict, dim: str) -> int:
    """Extract a packet's value on a given dimension."""
    if dim == "protocol":
        return {"TCP": 0, "UDP": 1, "ICMP": 2}[pkt["protocol"]]
    return pkt[dim]


def _max_distinct_children(rules: list[Rule], dim: str, k: int,
                           range_lo: int, range_hi: int) -> float:
    """Heuristic from the paper: number of distinct rule-subsets across k cuts.

    Rough approximation: count how many different "rule signatures" the k
    sub-ranges produce. Higher is better — more separation = more reduction.
    """
    if k <= 1 or range_hi <= range_lo:
        return 1.0
    cut_size = max(1, (range_hi - range_lo + 1) // k)
    signatures = set()
    for i in range(k):
        sub_lo = range_lo + i * cut_size
        sub_hi = min(range_hi, sub_lo + cut_size - 1)
        sig = tuple(sorted(
            id(r) for r in rules
            if _rule_range_on_dim(r, dim)[0] <= sub_hi
            and _rule_range_on_dim(r, dim)[1] >= sub_lo
        ))
        signatures.add(sig)
    return len(signatures)


def _choose_cut(rules: list[Rule], range_lo: dict, range_hi: dict) -> tuple[str, int]:
    """Choose which dimension to cut and how many cuts (k).

    Heuristic: pick the (dim, k) maximising max-distinct-children
    subject to the spmf budget: total cells ≤ spfac × len(rules).
    """
    best = ("dst_ip", 2, 0.0)  # default
    budget = SPFAC * max(1, len(rules))

    for dim in DIMENSIONS:
        lo, hi = range_lo[dim], range_hi[dim]
        if hi <= lo:
            continue
        # Try k = 2, 4, 8, 16, 32 (powers of 2 — the paper uses these)
        for k in (2, 4, 8, 16, 32):
            if k > budget:
                break
            if k > (hi - lo + 1):
                continue
            score = _max_distinct_children(rules, dim, k, lo, hi)
            if score > best[2]:
                best = (dim, k, score)
    return best[0], best[1]


def build_hicuts(rules: list[Rule],
                 range_lo: dict | None = None,
                 range_hi: dict | None = None,
                 depth: int = 0,
                 max_depth: int = 12) -> HiCutsNode:
    """Recursively build a HiCuts tree over the given rule set."""
    if range_lo is None:
        range_lo = {"protocol": 0, "src_ip": 0, "dst_ip": 0, "dst_port": 0}
        range_hi = {"protocol": 2,
                    "src_ip":   2**32 - 1,
                    "dst_ip":   2**32 - 1,
                    "dst_port": 65535}

    # Leaf condition
    if len(rules) <= BINTH or depth >= max_depth:
        return HiCutsNode(is_leaf=True, rules=list(rules))

    # Choose cut dimension and k
    dim, k = _choose_cut(rules, range_lo, range_hi)

    if k <= 1:
        return HiCutsNode(is_leaf=True, rules=list(rules))

    # Cut the chosen dimension into k partitions
    lo, hi = range_lo[dim], range_hi[dim]
    cut_size = max(1, (hi - lo + 1) // k)

    children = []
    node = HiCutsNode(is_leaf=False, cut_dim=dim, children=children,
                      range_start=lo, range_end=hi)

    for i in range(k):
        sub_lo = lo + i * cut_size
        sub_hi = min(hi, sub_lo + cut_size - 1) if i < k - 1 else hi
        sub_rules = [
            r for r in rules
            if _rule_range_on_dim(r, dim)[0] <= sub_hi
               and _rule_range_on_dim(r, dim)[1] >= sub_lo
        ]
        new_lo = dict(range_lo); new_hi = dict(range_hi)
        new_lo[dim] = sub_lo; new_hi[dim] = sub_hi
        child = build_hicuts(sub_rules, new_lo, new_hi, depth + 1, max_depth)
        children.append((sub_lo, sub_hi, child))

    return node


def hicuts_match(node: HiCutsNode, pkt: dict) -> str:
    """Match a packet against a HiCuts tree."""
    while not node.is_leaf:
        v = _packet_dim_value(pkt, node.cut_dim)
        # Find the child whose range contains v
        next_node = None
        for sub_lo, sub_hi, child in node.children:
            if sub_lo <= v <= sub_hi:
                next_node = child
                break
        if next_node is None:
            return "DENY"  # implicit deny
        node = next_node
    # Leaf: linear scan
    return lrf_match(node.rules, pkt)


def hicuts_stats(root: HiCutsNode) -> dict:
    """Walk the HiCuts tree and return summary statistics."""
    n_int = 0
    n_leaf = 0
    total_rule_storage = 0
    max_depth = [0]

    def walk(node, d=0):
        nonlocal n_int, n_leaf, total_rule_storage
        max_depth[0] = max(max_depth[0], d)
        if node.is_leaf:
            n_leaf += 1
            total_rule_storage += len(node.rules)
        else:
            n_int += 1
            for _, _, c in node.children:
                walk(c, d + 1)
    walk(root)
    return {
        "n_internal":         n_int,
        "n_leaves":           n_leaf,
        "total_rule_storage": total_rule_storage,
        "depth":              max_depth[0],
    }


def hicuts_size_bytes(root: HiCutsNode) -> int:
    """Approximate memory of the HiCuts tree using sys.getsizeof recursively."""
    seen = set()

    def sizeof(o):
        if id(o) in seen:
            return 0
        seen.add(id(o))
        s = _sys.getsizeof(o)
        if isinstance(o, HiCutsNode):
            s += sizeof(o.rules) + sizeof(o.children)
        elif isinstance(o, (list, tuple)):
            s += sum(sizeof(x) for x in o)
        elif isinstance(o, dict):
            s += sum(sizeof(k) + sizeof(v) for k, v in o.items())
        return s
    return sizeof(root)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, json, random

    ap = argparse.ArgumentParser()
    ap.add_argument("policy_jsonl")
    ap.add_argument("--packets", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    with open(args.policy_jsonl) as f:
        policy = json.loads(f.readline())

    rules = parse_policy(policy["rules"])
    print(f"Loaded {len(rules)} rules from {policy['policy_id']}")

    t0 = time.perf_counter()
    root = build_hicuts(rules)
    build_ms = (time.perf_counter() - t0) * 1000

    stats = hicuts_stats(root)
    sz = hicuts_size_bytes(root)
    print(f"\nHiCuts build:")
    print(f"  build_time_ms: {build_ms:.1f}")
    print(f"  internal:      {stats['n_internal']}")
    print(f"  leaves:        {stats['n_leaves']}")
    print(f"  rules in leaves (sum): {stats['total_rule_storage']}")
    print(f"  depth:         {stats['depth']}")
    print(f"  size:          {sz/1024:.1f} KB")

    rng = random.Random(args.seed)
    protos = ["TCP", "UDP", "ICMP"]
    def mk_pkt():
        proto = rng.choice(protos)
        return {"protocol": proto,
                "src_ip": rng.randint(0, 2**32 - 1),
                "dst_ip": rng.randint(0, 2**32 - 1),
                "dst_port": rng.randint(0, 255 if proto == "ICMP" else 65535)}
    pkts = [mk_pkt() for _ in range(args.packets)]
    t0 = time.perf_counter()
    for p in pkts:
        hicuts_match(root, p)
    t_hi = (time.perf_counter() - t0) / args.packets * 1e6

    t0 = time.perf_counter()
    for p in pkts:
        lrf_match(rules, p)
    t_lrf = (time.perf_counter() - t0) / args.packets * 1e6

    print(f"\nMatch latency: HiCuts={t_hi:.2f} μs, LRF={t_lrf:.2f} μs, "
          f"speedup={t_lrf/t_hi:.2f}×")
