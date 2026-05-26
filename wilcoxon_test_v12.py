#!/usr/bin/env python3
"""
wilcoxon_test_v12.py
=====================
Post-process the JSON output of ordering_benchmark_v12.py to compute the
paired Wilcoxon signed-rank test comparing protocol-first orderings
(IDs 1-6) vs. protocol-elsewhere orderings (IDs 7-12).

This addresses Reviewer Comment 3 by providing statistical significance
testing for the ordering benchmark results.

Two run modes:
    - PAIRED MODE: requires raw per-trial values (key '_trials' inside
      each cell of results). This is the default for ordering_benchmark_v12.py
      output and computes a true Wilcoxon test with valid p-values.
    - SUMMARY MODE: falls back when only mean/std are available (older
      benchmark output). Reports ratios and effect sizes only -- p-values
      cannot be computed because paired samples are required.

Usage:
    # 1. First run the ordering benchmark
    python ordering_benchmark_v12.py --sizes 25,50,100 --trials 10 \\
        --output ordering_benchmark_v12_results.json

    # 2. Then run this post-processing script
    python wilcoxon_test_v12.py \\
        --input ordering_benchmark_v12_results.json \\
        --output wilcoxon_results.json

Requires:
    - scipy (for the Wilcoxon test); falls back to a binomial sign test
      if scipy is unavailable.
"""
from __future__ import annotations
import argparse, json, math, statistics, sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional scipy import
# ---------------------------------------------------------------------------
try:
    from scipy import stats as _scipy_stats
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False
    sys.stderr.write("[WARNING] scipy not installed; falling back to binomial sign test.\n"
                     "   For the standard Wilcoxon test, install scipy:\n"
                     "       pip install scipy\n\n")


# Metrics to test (must exist in each cell as both '_mean' and inside '_trials')
METRICS = ["tree_bytes", "n_nodes", "match_us", "conv_ms", "peak_bytes"]

PROTO_FIRST_IDS     = list(range(1, 7))    # IDs 1-6
PROTO_ELSEWHERE_IDS = list(range(7, 13))   # IDs 7-12


def normalize_input(data: dict) -> dict:
    """Detect and normalize the input JSON structure.

    The ordering_benchmark_v12.py output uses key 'results' but earlier
    benchmark scripts may use 'data'. Returns a dict with uniform structure:
        {sizes: [...], cells: {n_str: {oid_str: cell_dict}}}
    """
    if "results" in data:
        cells = data["results"]
    elif "data" in data:
        cells = data["data"]
    else:
        raise KeyError("Input JSON must contain either 'results' or 'data' key. "
                       "Got top-level keys: " + ", ".join(data.keys()))

    sizes = data.get("sizes", sorted(int(k) for k in cells.keys()))

    return {"sizes": sizes, "cells": cells, "trials": data.get("trials")}


def has_raw_trials(cells: dict) -> bool:
    """Check whether the input contains raw per-trial values needed for
    a true paired Wilcoxon test."""
    for n_str in cells:
        for oid_str in cells[n_str]:
            if "_trials" in cells[n_str][oid_str]:
                return True
            return False
    return False


def wilcoxon_or_sign(pf_per_trial, pe_per_trial):
    """Run paired Wilcoxon (one-sided H1: pf < pe) if scipy is available;
    otherwise fall back to a one-sided binomial sign test."""
    if HAVE_SCIPY and len(pf_per_trial) >= 6:
        try:
            _, p_val = _scipy_stats.wilcoxon(pf_per_trial, pe_per_trial,
                                             alternative='less')
            return p_val, "wilcoxon"
        except ValueError:
            pass
    # Sign-test fallback
    from math import comb
    wins = sum(1 for pf, pe in zip(pf_per_trial, pe_per_trial) if pf < pe)
    losses = sum(1 for pf, pe in zip(pf_per_trial, pe_per_trial) if pf > pe)
    n_eff = wins + losses
    if n_eff == 0:
        return 1.0, "sign_test_no_diffs"
    p_val = sum(comb(n_eff, k) for k in range(wins, n_eff + 1)) / 2 ** n_eff
    return p_val, "binomial_sign"


def sig_label(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"


def run_paired_wilcoxon(normalized: dict) -> dict:
    """Run the paired Wilcoxon test using raw per-trial values."""
    cells = normalized["cells"]
    results = {
        "test": "scipy.wilcoxon" if HAVE_SCIPY else "binomial_sign",
        "alternative": "less (H1: protocol-first < protocol-elsewhere)",
        "mode": "paired",
        "by_size": {},
    }

    print(f"{'n':>4} {'metric':>15} {'pf_mean':>14} {'pe_mean':>14} "
          f"{'ratio':>7} {'p-value':>12} {'sig':>5}")
    print("-" * 80)

    for n in normalized["sizes"]:
        n_str = str(n)
        if n_str not in cells:
            continue

        # Get number of trials from first cell
        first_oid = str(PROTO_FIRST_IDS[0])
        if first_oid not in cells[n_str]:
            continue
        trials_list = cells[n_str][first_oid].get("_trials", [])
        n_trials = len(trials_list)
        if n_trials < 3:
            print(f"  Skipping n={n}: only {n_trials} trials (need >=3)")
            continue

        sect = {"n_trials": n_trials, "metrics": {}}
        for metric in METRICS:
            # For each trial, average across IDs 1-6 vs 7-12
            pf_per_trial, pe_per_trial = [], []
            for t_idx in range(n_trials):
                pf_vals = [cells[n_str][str(o)]["_trials"][t_idx][metric]
                           for o in PROTO_FIRST_IDS]
                pe_vals = [cells[n_str][str(o)]["_trials"][t_idx][metric]
                           for o in PROTO_ELSEWHERE_IDS]
                pf_per_trial.append(sum(pf_vals) / len(pf_vals))
                pe_per_trial.append(sum(pe_vals) / len(pe_vals))

            pf_mean = sum(pf_per_trial) / len(pf_per_trial)
            pe_mean = sum(pe_per_trial) / len(pe_per_trial)
            ratio = pe_mean / pf_mean if pf_mean > 0 else float("nan")
            p_val, test_kind = wilcoxon_or_sign(pf_per_trial, pe_per_trial)
            sig = sig_label(p_val)

            sect["metrics"][metric] = {
                "pf_mean": pf_mean, "pe_mean": pe_mean, "ratio": ratio,
                "p_value": p_val, "significance": sig, "test": test_kind,
                "n_trials": n_trials,
            }
            print(f"{n:>4} {metric:>15} {pf_mean:>14.2f} {pe_mean:>14.2f} "
                  f"{ratio:>7.2f} {p_val:>12.4g} {sig:>5}")

        results["by_size"][n_str] = sect

    return results


def run_summary_only(normalized: dict) -> dict:
    """Fallback: only summary stats available (no raw trials).

    Computes ratios from cell means but cannot do a real Wilcoxon test.
    """
    cells = normalized["cells"]
    results = {
        "test": "summary_only_no_paired_test",
        "alternative": "n/a (no raw trials in input)",
        "mode": "summary",
        "warning": ("Input JSON does not contain '_trials' arrays. "
                    "Re-run ordering_benchmark_v12.py with the latest "
                    "version (v12.1+) to enable the paired Wilcoxon test."),
        "by_size": {},
    }

    print("[WARNING] Summary mode: no paired test possible.")
    print(f"{'n':>4} {'metric':>15} {'pf_mean':>14} {'pe_mean':>14} {'ratio':>7}")
    print("-" * 60)

    for n in normalized["sizes"]:
        n_str = str(n)
        if n_str not in cells:
            continue
        sect = {"metrics": {}}
        for metric in METRICS:
            pf_means = []
            pe_means = []
            for o in PROTO_FIRST_IDS:
                key = f"{metric}_mean"
                if key in cells[n_str].get(str(o), {}):
                    pf_means.append(cells[n_str][str(o)][key])
            for o in PROTO_ELSEWHERE_IDS:
                key = f"{metric}_mean"
                if key in cells[n_str].get(str(o), {}):
                    pe_means.append(cells[n_str][str(o)][key])
            if not pf_means or not pe_means:
                continue
            pf_mean = sum(pf_means) / len(pf_means)
            pe_mean = sum(pe_means) / len(pe_means)
            ratio = pe_mean / pf_mean if pf_mean > 0 else float("nan")
            sect["metrics"][metric] = {
                "pf_mean": pf_mean, "pe_mean": pe_mean, "ratio": ratio,
                "p_value": None, "significance": "n/a",
            }
            print(f"{n:>4} {metric:>15} {pf_mean:>14.2f} {pe_mean:>14.2f} {ratio:>7.2f}")
        results["by_size"][n_str] = sect

    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", "-i", default="ordering_benchmark_v12_results.json",
                    help="Path to ordering benchmark results JSON "
                         "(default: ordering_benchmark_v12_results.json)")
    ap.add_argument("--output", "-o", default="wilcoxon_results.json",
                    help="Output Wilcoxon results JSON (default: wilcoxon_results.json)")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.stderr.write(f"[FAIL] Input file not found: {in_path}\n")
        sys.stderr.write(f"   Run the ordering benchmark first:\n")
        sys.stderr.write(f"     python ordering_benchmark_v12.py "
                         f"--sizes 25,50,100 --trials 10 --output {in_path.name}\n")
        sys.exit(1)

    print(f"Reading: {in_path}")
    with in_path.open() as f:
        data = json.load(f)

    print("Normalizing input structure...")
    normalized = normalize_input(data)
    print(f"  Sizes: {normalized['sizes']}")

    if has_raw_trials(normalized["cells"]):
        print("  Raw trials found -> PAIRED WILCOXON MODE\n")
        results = run_paired_wilcoxon(normalized)
    else:
        print("  No raw trials -> SUMMARY MODE (no p-values possible)\n")
        print("  To enable paired Wilcoxon test, re-run ordering_benchmark_v12.py")
        print("  with the latest version (v12.1+) which stores per-trial values.\n")
        results = run_summary_only(normalized)

    out_path = Path(args.output)
    with out_path.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Saved -> {out_path}")


if __name__ == "__main__":
    main()
