#!/usr/bin/env python3
"""Merge chunked ordering_benchmark_v12.py outputs (same n, different seeds)
into one unified results.json with combined _trials lists and recomputed
aggregate stats (mean/std/min/max), matching the original schema so that
wilcoxon_test_v12.py / stats_strengthen_v12.py can consume it directly."""
import json, statistics

FILES = {
    50:  ["/tmp/ord_n50.json", "/tmp/ord_n50_b.json"],
    100: ["/tmp/ord_n100_a.json", "/tmp/ord_n100_b.json", "/tmp/ord_n100_c.json", "/tmp/ord_n100_d.json"],
    200: ["/tmp/ord_n200_a.json", "/tmp/ord_n200_b.json", "/tmp/ord_n200_c.json", "/tmp/ord_n200_d.json", "/tmp/ord_n200_e.json"],
    400: ["/tmp/ord_n400_a.json", "/tmp/ord_n400_b.json", "/tmp/ord_n400_c.json", "/tmp/ord_n400_d.json", "/tmp/ord_n400_e.json"],
}

FIELD_MAP = {
    "trf_depth": "trf_depth", "n_nodes": "n_nodes", "n_leaves": "n_leaves",
    "n_cells_norm": "n_cells_norm", "conv_ms": "conv_ms",
    "tree_bytes": "tree_bytes", "peak_bytes": "peak_bytes", "match_us": "match_us",
}


def aggregate(trials_data):
    out = {}
    for key in FIELD_MAP:
        vals = [t[key] for t in trials_data]
        out[f"{key}_mean"] = statistics.mean(vals)
        out[f"{key}_std"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out[f"{key}_min"] = min(vals)
        out[f"{key}_max"] = max(vals)
    out["_trials"] = trials_data
    return out


merged_results = {}
orderings_meta = None
total_elapsed = 0.0
total_trials = 0

for n, files in FILES.items():
    per_ordering_trials = {}
    for fp in files:
        d = json.load(open(fp))
        if orderings_meta is None:
            orderings_meta = d["orderings"]
        total_elapsed += d.get("elapsed_s", 0.0)
        cell = d["results"][str(n)]
        for oid_str, vals in cell.items():
            per_ordering_trials.setdefault(oid_str, [])
            per_ordering_trials[oid_str].extend(vals["_trials"])
    merged_results[str(n)] = {
        oid_str: aggregate(trials_list)
        for oid_str, trials_list in per_ordering_trials.items()
    }
    total_trials = len(next(iter(per_ordering_trials.values())))
    print(f"n={n}: merged {len(files)} chunk file(s) -> {total_trials} trials per ordering")

payload = {
    "sizes": [50, 100, 200, 400],
    "trials": "6 (merged from chunked runs, seeds 2025/3025/4025)",
    "packets": 2000,
    "seed": "chunked: 2025,3025,4025",
    "elapsed_s": total_elapsed,
    "orderings": orderings_meta,
    "results": merged_results,
    "note": "Merged from independent chunked subprocess calls (same generator, "
            "independent seeds) due to sandbox execution-time limits per call. "
            "Each chunk uses the same build_policy/gen_packets generator as the "
            "original ordering_benchmark_v12.py, so trials are statistically "
            "equivalent to a single continuous run.",
}
json.dump(payload, open("/home/claude/work/code/TreeRuleFirewall_20260526_2001-master/ordering_benchmark_v12_results_merged10.json", "w"), indent=2)
print("\nWrote ordering_benchmark_v12_results_merged10.json")
print("Total elapsed across all chunks: %.1f s (%.1f min)" % (total_elapsed, total_elapsed/60))
