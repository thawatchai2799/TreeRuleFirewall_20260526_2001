#!/usr/bin/env python3
"""
stats_strengthen_v12.py
========================
Strengthen the ordering-benchmark statistics beyond the plain binomial
sign test.

Reads ordering_benchmark_v12_results.json (paired per-trial data, PF =
orderings 1-6 vs PE = orderings 7-12) and computes, for each of the 5
metrics x 4 policy sizes (20 comparisons total):

  1. Wilcoxon signed-rank p-value (already in wilcoxon_test_v12.py; we
     recompute it here so this script is self-contained)
  2. Matched-pairs rank-biserial correlation effect size r_rb
     (Kerby 2014 simple-difference formula: r_rb = (W+ - W-) / (W+ + W-))
  3. Holm-Bonferroni-adjusted p-value across the family of 20 tests
  4. TOST (two one-sided tests) equivalence test against a +-10% relative
     equivalence bound on the PF mean, for the "parity" claims
     (match_us and conv_ms at n=100 and n=200)

Usage:
    python stats_strengthen_v12.py \
        --input ordering_benchmark_v12_results.json \
        --output stats_strengthen_v12_results.json
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path

try:
    from scipy import stats as _st
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False

METRICS = ["tree_bytes", "n_nodes", "match_us", "conv_ms", "peak_bytes"]
METRIC_LABELS = {
    "tree_bytes": "Tree memory (bytes)",
    "n_nodes": "Internal nodes",
    "match_us": "Match latency (us)",
    "conv_ms": "Conversion time (ms)",
    "peak_bytes": "Peak memory (bytes, tracemalloc)",
}
PF_IDS = list(range(1, 7))
PE_IDS = list(range(7, 13))

TOST_REL_BOUND = 0.10  # +-10% of PF mean, our chosen equivalence margin
TOST_TARGETS = {("match_us", 100), ("match_us", 200), ("conv_ms", 100), ("conv_ms", 200)}


def rank_biserial(pf, pe):
    """Matched-pairs rank-biserial correlation (Kerby 2014).
    H1 framing: pf < pe (protocol-first is 'better' i.e. smaller).
    d_i = pe_i - pf_i ; positive d favors PF-wins.
    r_rb = (W_pos - W_neg) / (W_pos + W_neg), range [-1, 1].
    """
    diffs = [pe_i - pf_i for pf_i, pe_i in zip(pf, pe) if pe_i != pf_i]
    if not diffs:
        return 0.0
    absd = [abs(d) for d in diffs]
    order = sorted(range(len(diffs)), key=lambda i: absd[i])
    ranks = [0.0] * len(diffs)
    # average ranks for ties
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and absd[order[j + 1]] == absd[order[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    w_pos = sum(r for r, d in zip(ranks, diffs) if d > 0)
    w_neg = sum(r for r, d in zip(ranks, diffs) if d < 0)
    return (w_pos - w_neg) / (w_pos + w_neg)


def wilcoxon_p(pf, pe):
    if HAVE_SCIPY and len(pf) >= 6:
        try:
            _, p = _st.wilcoxon(pf, pe, alternative="less")
            return p, "wilcoxon"
        except ValueError:
            pass
    from math import comb
    wins = sum(1 for a, b in zip(pf, pe) if a < b)
    losses = sum(1 for a, b in zip(pf, pe) if a > b)
    n_eff = wins + losses
    if n_eff == 0:
        return 1.0, "sign_test_no_diffs"
    p = sum(comb(n_eff, k) for k in range(wins, n_eff + 1)) / 2 ** n_eff
    return p, "binomial_sign"


def holm_bonferroni(pvals):
    """Return Holm-Bonferroni-adjusted p-values, same order as input."""
    m = len(pvals)
    idx_sorted = sorted(range(m), key=lambda i: pvals[i])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, idx in enumerate(idx_sorted):
        adj = (m - rank) * pvals[idx]
        running_max = max(running_max, adj)
        adjusted[idx] = min(running_max, 1.0)
    return adjusted


def tost_equivalence(pf, pe, rel_bound=TOST_REL_BOUND):
    """Two one-sided t-tests for paired samples.
    Equivalence bound = +-rel_bound * mean(pf) (absolute units).
    diff_i = pe_i - pf_i ; test H0: |mean(diff)| >= bound  vs  H1: |mean(diff)| < bound
    Returns (p_tost, bound_abs, mean_diff, ci90).
    """
    n = len(pf)
    diffs = [b - a for a, b in zip(pf, pe)]
    mean_diff = sum(diffs) / n
    if n < 2:
        return None
    sd = math.sqrt(sum((d - mean_diff) ** 2 for d in diffs) / (n - 1))
    se = sd / math.sqrt(n) if sd > 0 else 1e-12
    pf_mean = sum(pf) / n
    bound = rel_bound * pf_mean

    df = n - 1
    t_upper = (mean_diff - bound) / se   # H0: mean_diff >= bound
    t_lower = (mean_diff + bound) / se   # H0: mean_diff <= -bound
    if HAVE_SCIPY:
        p_upper = _st.t.cdf(t_upper, df)       # test 1: mean_diff < bound
        p_lower = 1 - _st.t.cdf(t_lower, df)   # test 2: mean_diff > -bound
        t90 = _st.t.ppf(0.95, df)
    else:
        # crude normal approximation fallback
        from math import erf
        def norm_cdf(x):
            return 0.5 * (1 + erf(x / math.sqrt(2)))
        p_upper = norm_cdf(t_upper)
        p_lower = 1 - norm_cdf(t_lower)
        t90 = 1.645
    p_tost = max(p_upper, p_lower)
    ci90 = (mean_diff - t90 * se, mean_diff + t90 * se)
    return {
        "mean_diff": mean_diff, "bound_abs": bound, "rel_bound": rel_bound,
        "p_tost": p_tost, "ci90_low": ci90[0], "ci90_high": ci90[1],
        "equivalent_at_0.05": bool(p_tost < 0.05),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", default="ordering_benchmark_v12_results.json")
    ap.add_argument("--output", "-o", default="stats_strengthen_v12_results.json")
    args = ap.parse_args()

    data = json.load(open(args.input))
    cells = data["results"]
    sizes = data["sizes"]

    all_tests = []  # flat list for Holm-Bonferroni across whole family
    by_size = {}

    for n in sizes:
        n_str = str(n)
        if n_str not in cells:
            continue
        first_oid = str(PF_IDS[0])
        trials_list = cells[n_str][first_oid].get("_trials", [])
        n_trials = len(trials_list)
        if n_trials < 3:
            continue

        sect = {"n_trials": n_trials, "metrics": {}}
        for metric in METRICS:
            pf_per_trial, pe_per_trial = [], []
            for t_idx in range(n_trials):
                pf_vals = [cells[n_str][str(o)]["_trials"][t_idx][metric] for o in PF_IDS]
                pe_vals = [cells[n_str][str(o)]["_trials"][t_idx][metric] for o in PE_IDS]
                pf_per_trial.append(sum(pf_vals) / len(pf_vals))
                pe_per_trial.append(sum(pe_vals) / len(pe_vals))

            p_val, test_kind = wilcoxon_p(pf_per_trial, pe_per_trial)
            r_rb = rank_biserial(pf_per_trial, pe_per_trial)
            pf_mean = sum(pf_per_trial) / n_trials
            pe_mean = sum(pe_per_trial) / n_trials
            ratio = pe_mean / pf_mean if pf_mean else float("nan")

            entry = {
                "pf_mean": pf_mean, "pe_mean": pe_mean, "ratio": ratio,
                "p_raw": p_val, "test": test_kind,
                "effect_size_rank_biserial": r_rb,
            }

            if (metric, n) in TOST_TARGETS:
                tost = tost_equivalence(pf_per_trial, pe_per_trial)
                entry["tost"] = tost

            sect["metrics"][metric] = entry
            all_tests.append((n, metric, entry))

        by_size[n_str] = sect

    # Holm-Bonferroni across the full family (20 tests: 5 metrics x 4 sizes)
    pvals = [e["p_raw"] for (_, _, e) in all_tests]
    adjusted = holm_bonferroni(pvals)
    for (n, metric, e), p_adj in zip(all_tests, adjusted):
        e["p_holm"] = p_adj
        e["sig_holm"] = "*" if p_adj < 0.05 else "ns"

    out = {
        "family_size": len(all_tests),
        "correction": "Holm-Bonferroni (step-down), family = 5 metrics x 4 sizes = 20 tests",
        "effect_size": "matched-pairs rank-biserial correlation (Kerby 2014)",
        "tost_equivalence_bound": f"+-{int(TOST_REL_BOUND*100)}% of PF mean (two one-sided t-tests, alpha=0.05)",
        "by_size": by_size,
    }
    json.dump(out, open(args.output, "w"), indent=2)

    # ---- print human-readable summary table ----
    print(f"{'n':>4} {'metric':>12} {'ratio':>7} {'r_rb':>7} {'p_raw':>10} {'p_holm':>10} {'sig':>5}")
    print("-" * 65)
    for n, metric, e in all_tests:
        print(f"{n:>4} {metric:>12} {e['ratio']:>7.3f} {e['effect_size_rank_biserial']:>7.3f} "
              f"{e['p_raw']:>10.4g} {e['p_holm']:>10.4g} {e['sig_holm']:>5}")
    print()
    print("TOST equivalence results (parity claims):")
    for n, metric, e in all_tests:
        if "tost" in e and e["tost"]:
            t = e["tost"]
            print(f"  n={n:<4} {metric:<10} mean_diff={t['mean_diff']:.4g}  "
                  f"bound=+-{t['bound_abs']:.4g}  p_tost={t['p_tost']:.4g}  "
                  f"equivalent@.05={t['equivalent_at_0.05']}")
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
