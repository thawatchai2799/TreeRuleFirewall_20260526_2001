#!/usr/bin/env python3
"""
E1 analyzer - integrity check and first-look summary of the per-policy ordering data.

Run this after e1_runner.py to verify the dataset is complete and consistent, and
to see whether adaptive ordering selection is worth pursuing on the data collected
so far.

Usage (Windows PowerShell or cmd):

    python e1_analyze.py --in results\\e1.jsonl
    python e1_analyze.py --in results\\e1.jsonl --metric n_nodes
    python e1_analyze.py --in results\\e1.jsonl --csv results\\e1_wide.csv

Metrics available: n_nodes, tree_bytes, peak_bytes, conv_s, match_us_mean
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import statistics
import sys
from pathlib import Path

METRICS = ["n_nodes", "tree_bytes", "peak_bytes", "conv_s", "match_us_mean"]
PROTOCOL_FIRST = set(range(1, 7))
DEFAULT_ORDERING = 4


def load(path: Path) -> list[dict]:
    rows = []
    bad = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    if bad:
        print(f"WARNING: {bad} unreadable line(s) skipped.")
    return rows


def integrity(rows: list[dict]) -> dict:
    """Check completeness and the invariants the framework guarantees."""
    by_policy = collections.defaultdict(dict)
    for r in rows:
        by_policy[r["policy_id"]][r["ordering_id"]] = r

    complete, partial = [], []
    for pid, d in by_policy.items():
        (complete if len(d) == 12 else partial).append(pid)

    depth_violations = [r["policy_id"] for r in rows if r["trf_depth"] != 4]

    # Semantic invariance implies leaf count may differ, but depth must not.
    # Cost non-invariance implies node counts should differ across orderings.
    identical_cost = []
    for pid, d in by_policy.items():
        if len(d) == 12 and len({x["n_nodes"] for x in d.values()}) == 1:
            identical_cost.append(pid)

    dupes = len(rows) - len({(r["policy_id"], r["ordering_id"]) for r in rows})

    return {
        "records": len(rows),
        "policies": len(by_policy),
        "complete": len(complete),
        "partial": len(partial),
        "partial_ids": partial[:10],
        "duplicates": dupes,
        "depth_violations": depth_violations[:10],
        "identical_cost": identical_cost[:10],
        "by_policy": by_policy,
    }


def summarise(by_policy: dict, metric: str) -> None:
    """Report how often the default ordering is optimal, and the regret if it is not."""
    usable = {p: d for p, d in by_policy.items()
              if len(d) == 12 and all(x.get(metric) is not None for x in d.values())}
    if not usable:
        print(f"\nNo policies have complete data for metric '{metric}'.")
        if metric == "match_us_mean":
            print("Timing is subsampled when --timing-every is greater than 1.")
        return

    print(f"\n=== Metric: {metric} ({len(usable)} policies with complete data) ===")

    win_counts = collections.Counter()
    default_optimal = 0
    regrets = []
    pf_better = 0

    for pid, d in usable.items():
        vals = {oid: float(x[metric]) for oid, x in d.items()}
        best_oid = min(vals, key=vals.get)
        best = vals[best_oid]
        win_counts[best_oid] += 1

        if best_oid == DEFAULT_ORDERING:
            default_optimal += 1
        if best > 0:
            regrets.append((vals[DEFAULT_ORDERING] - best) / best * 100.0)

        pf_mean = statistics.mean(v for o, v in vals.items() if o in PROTOCOL_FIRST)
        pe_mean = statistics.mean(v for o, v in vals.items() if o not in PROTOCOL_FIRST)
        if pf_mean < pe_mean:
            pf_better += 1

    n = len(usable)
    print(f"  Default ordering {DEFAULT_ORDERING} is optimal for "
          f"{default_optimal}/{n} policies ({default_optimal / n * 100:.1f}%)")
    if regrets:
        regrets_sorted = sorted(regrets)
        p95 = regrets_sorted[min(len(regrets_sorted) - 1, int(0.95 * len(regrets_sorted)))]
        print(f"  Regret of always using ordering {DEFAULT_ORDERING}: "
              f"mean {statistics.mean(regrets):.2f}%, "
              f"median {statistics.median(regrets):.2f}%, "
              f"p95 {p95:.2f}%, max {max(regrets):.2f}%")
    print(f"  Protocol-first family beats protocol-elsewhere on "
          f"{pf_better}/{n} policies ({pf_better / n * 100:.1f}%)")

    print("  Wins per ordering:")
    for oid in range(1, 13):
        c = win_counts.get(oid, 0)
        bar = "#" * int(round(c / max(1, max(win_counts.values())) * 30))
        tag = "PF" if oid in PROTOCOL_FIRST else "PE"
        star = " <- default" if oid == DEFAULT_ORDERING else ""
        print(f"    {oid:>2} [{tag}] {c:>5} {bar}{star}")


def by_size(by_policy: dict, metric: str) -> None:
    """Show whether the picture changes with policy size."""
    buckets = collections.defaultdict(list)
    for pid, d in by_policy.items():
        if len(d) != 12 or any(x.get(metric) is None for x in d.values()):
            continue
        n = next(iter(d.values()))["n_rules_in"]
        band = 50 if n <= 75 else 100 if n <= 150 else 200 if n <= 300 else 400 if n <= 600 else 800
        vals = {oid: float(x[metric]) for oid, x in d.items()}
        best = min(vals.values())
        pf = statistics.mean(v for o, v in vals.items() if o in PROTOCOL_FIRST)
        pe = statistics.mean(v for o, v in vals.items() if o not in PROTOCOL_FIRST)
        buckets[band].append((vals[DEFAULT_ORDERING] / best, pe / pf if pf > 0 else float("nan")))

    if not buckets:
        return
    print(f"\n=== By size band ({metric}) ===")
    print(f"  {'band':>6} {'policies':>9} {'default/best':>13} {'PE/PF ratio':>13}")
    for band in sorted(buckets):
        rows = buckets[band]
        d_ratio = statistics.mean(r[0] for r in rows)
        fam = [r[1] for r in rows if r[1] == r[1]]
        f_ratio = statistics.mean(fam) if fam else float("nan")
        print(f"  {band:>6} {len(rows):>9} {d_ratio:>13.3f} {f_ratio:>13.3f}")


def write_csv(by_policy: dict, out_path: Path) -> None:
    """Write one row per policy with all twelve orderings side by side, plus features."""
    feature_keys: list[str] = []
    for d in by_policy.values():
        for rec in d.values():
            if "features" in rec:
                feature_keys = sorted(rec["features"].keys())
                break
        if feature_keys:
            break

    header = ["policy_id", "n_rules_in"] + feature_keys
    for m in METRICS:
        header += [f"{m}_o{o}" for o in range(1, 13)]
    header += ["best_ordering_nodes", "best_ordering_bytes"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for pid in sorted(by_policy):
            d = by_policy[pid]
            if len(d) != 12:
                continue
            any_rec = next(iter(d.values()))
            row = [pid, any_rec["n_rules_in"]]
            feats = any_rec.get("features", {})
            row += [feats.get(k, "") for k in feature_keys]
            for m in METRICS:
                for o in range(1, 13):
                    v = d[o].get(m)
                    row.append("" if v is None else v)
            nodes = {o: d[o]["n_nodes"] for o in d}
            byts = {o: d[o]["tree_bytes"] for o in d}
            row += [min(nodes, key=nodes.get), min(byts, key=byts.get)]
            w.writerow(row)
    print(f"\nWide-format CSV written: {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity check and summary for E1 output.")
    ap.add_argument("--in", dest="inp", required=True, help="E1 JSON Lines file")
    ap.add_argument("--metric", default=None,
                    help=f"Metric to summarise (default: all of {', '.join(METRICS)})")
    ap.add_argument("--csv", default=None, help="Optional wide-format CSV output path")
    args = ap.parse_args()

    path = Path(args.inp)
    if not path.exists():
        sys.stderr.write(f"ERROR: file not found: {path}\n")
        return 2

    rows = load(path)
    if not rows:
        sys.stderr.write("ERROR: no records found.\n")
        return 2

    info = integrity(rows)
    print("=== Integrity ===")
    print(f"  records:            {info['records']}")
    print(f"  policies:           {info['policies']}")
    print(f"  complete (12/12):   {info['complete']}")
    print(f"  partial:            {info['partial']}"
          + (f"  ids: {info['partial_ids']}" if info["partial"] else ""))
    print(f"  duplicate pairs:    {info['duplicates']}"
          + ("  <- rerun should not produce these" if info["duplicates"] else ""))
    print(f"  depth != 4:         {len(info['depth_violations'])}"
          + (f"  ids: {info['depth_violations']}" if info["depth_violations"] else "  (as expected)"))
    print(f"  identical cost across all 12: {len(info['identical_cost'])}"
          + (f"  ids: {info['identical_cost']}  <- investigate"
             if info["identical_cost"] else "  (as expected)"))

    metrics = [args.metric] if args.metric else METRICS
    for m in metrics:
        if m not in METRICS:
            sys.stderr.write(f"ERROR: unknown metric '{m}'. Choose from {METRICS}.\n")
            return 2
        summarise(info["by_policy"], m)

    by_size(info["by_policy"], "n_nodes")

    if args.csv:
        write_csv(info["by_policy"], Path(args.csv))

    return 0


if __name__ == "__main__":
    sys.exit(main())
