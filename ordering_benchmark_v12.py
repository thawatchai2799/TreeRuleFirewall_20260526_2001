#!/usr/bin/env python3
"""
ordering_benchmark_v12.py
==========================
Step 4 (NEW) — Attribute-Ordering Comparison Benchmark (v12)

Compares all 12 attribute orderings on the same set of synthetic policies
to quantify how ordering affects TRF size, memory, conversion time, and
matching speed.

Metrics (7):
  1. trf_depth         : depth of the TRF
  2. n_nodes           : internal nodes
  3. n_leaves          : leaves
  4. n_cells_norm      : normalized cells (after Algorithm 1)
  5. conversion_time_ms: end-to-end LRF→TRF conversion time
  6. memory_bytes      : two measurements -
       (a) tree_size_bytes  : sys.getsizeof(TRF) deep-recursive (deployed size)
       (b) peak_alloc_bytes : tracemalloc peak during conversion (working set)
  7. trf_match_us      : per-packet match time (microseconds)

Design rationale:
  Identical policies are converted under each ordering, with the same
  random-packet workload, so any difference reflects ONLY the ordering.

Usage:
  python ordering_benchmark_v12.py
  python ordering_benchmark_v12.py --n 100 --trials 5 --packets 5000
  python ordering_benchmark_v12.py --sizes 25,50,100,200 --trials 10
"""
import argparse, gc, json, random, statistics, sys, time, tracemalloc
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    Rule, convert_policy, lrf_match, trf_match,
    trf_size_bytes,
    PROTOCOLS, ORDERING_OPTIONS, N_ORDERINGS,
    SINGLE_HOSTS, SUBNETS_24, SUBNETS_16, COMMON_PORTS, COMMON_ICMP_TYPES,
    cidr_to_range, _size_category,
    PORT_MAX, ICMP_TYPE_MAX,
)


# ── Policy & packet generation (same as scalability_benchmark, ICMP-aware) ──
def _make_rule(rng, rule_id):
    src  = rng.choice(SINGLE_HOSTS+SUBNETS_24+["ANY"])
    dst  = rng.choice(SINGLE_HOSTS+SUBNETS_24+["ANY"])
    proto= rng.choices(["TCP","UDP","ICMP","IP","ANY"],weights=[40,25,10,10,15])[0]
    if proto == "ICMP":
        port = rng.choice(COMMON_ICMP_TYPES)
    else:
        port = rng.choice(COMMON_PORTS)
    act  = rng.choice(["ALLOW","DENY"])
    ss,se= cidr_to_range(src) if src!="ANY" else (0,2**32-1)
    ds,de= cidr_to_range(dst) if dst!="ANY" else (0,2**32-1)
    return Rule(proto,ss,se,ds,de,port,port,act,rule_id=rule_id)


def build_policy(n, rng):
    rules = [_make_rule(rng, i) for i in range(n)]
    rules.append(Rule("ANY",0,2**32-1,0,2**32-1,0,PORT_MAX,"DENY",rule_id=n))
    return rules


def gen_packets(n, rng):
    pkts = []
    for _ in range(n):
        proto = rng.choice(PROTOCOLS)
        port_max = ICMP_TYPE_MAX if proto == "ICMP" else PORT_MAX
        pkts.append({"protocol":proto,
                     "src_ip":rng.randint(0,2**32-1),
                     "dst_ip":rng.randint(0,2**32-1),
                     "dst_port":rng.randint(0,port_max)})
    return pkts


# ── Single trial: convert one policy under one ordering, measure 7 metrics ──
def measure_one_trial(rules, ordering_id, packets):
    """Convert + match + measure all 7 metrics. Returns dict."""
    gc.collect()  # stabilize memory baseline

    tracemalloc.start()
    t0 = time.perf_counter()
    trf, report, clean = convert_policy(rules, ordering_id=ordering_id)
    conv_ms = (time.perf_counter() - t0) * 1000
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tree_bytes = trf_size_bytes(trf)

    # Match time (per-packet microseconds), averaged over all packets
    t0 = time.perf_counter()
    for p in packets:
        trf_match(trf, p)
    match_us = (time.perf_counter() - t0) / len(packets) * 1e6

    return {
        "trf_depth":       report.trf_depth,
        "n_nodes":         report.n_nodes,
        "n_leaves":        report.n_leaves,
        "n_cells_norm":    report.n_cells_normalized,
        "conv_ms":         conv_ms,
        "tree_bytes":      tree_bytes,
        "peak_bytes":      peak_bytes,
        "match_us":        match_us,
    }


def aggregate(trials_data):
    """Compute mean ± std for each metric across trials.

    Also stores the raw per-trial values under '_trials' so that downstream
    analyses (e.g., paired Wilcoxon test in wilcoxon_test_v12.py) can
    recover individual measurements.
    """
    keys = trials_data[0].keys()
    out = {}
    for k in keys:
        vals = [t[k] for t in trials_data]
        out[k+"_mean"] = statistics.mean(vals)
        out[k+"_std"]  = statistics.stdev(vals) if len(vals)>1 else 0.0
        out[k+"_min"]  = min(vals)
        out[k+"_max"]  = max(vals)
    # Keep raw trials list for downstream paired-sample tests
    out["_trials"] = trials_data
    return out


_ATTR_ABBR = {
    "protocol": "pro",
    "src_ip":   "src",
    "dst_ip":   "dIP",
    "dst_port": "dPt",
}

def _abbrev(ordering):
    return "→".join(_ATTR_ABBR[a] for a in ordering)


# ── ASCII bar chart helpers ────────────────────────────────────────────────
def _fmt_bar(value, max_value, width=24):
    """Render a single horizontal bar of length proportional to value/max."""
    if max_value <= 0:
        return ""
    fill = int(round(width * value / max_value))
    return "█" * fill + "░" * (width - fill)

def render_bar_chart(metric_label, results_for_n, key, fmt_str="{:.1f}",
                     unit="", lower_is_better=True):
    """Render an ASCII bar chart comparing 12 orderings for one metric."""
    print(f"\n  ── {metric_label} {unit} ─────────────────────────────────────")
    max_val = max(v[key+"_mean"] for v in results_for_n.values())
    min_val = min(v[key+"_mean"] for v in results_for_n.values())

    for oid, vals in sorted(results_for_n.items()):
        v = vals[key+"_mean"]
        bar = _fmt_bar(v, max_val)
        marker = ""
        if lower_is_better and v == min_val:
            marker = "  ← BEST"
        elif (not lower_is_better) and v == max_val:
            marker = "  ← BEST"
        elif lower_is_better and v == max_val:
            marker = "  ← worst"
        elif (not lower_is_better) and v == min_val:
            marker = "  ← worst"
        order_str = _abbrev(ORDERING_OPTIONS[oid])
        val_str = fmt_str.format(v)
        print(f"  {oid:>2} {order_str:<19} {bar} {val_str:>10}{marker}")


# ── Main benchmark ─────────────────────────────────────────────────────────
def run_benchmark(sizes, trials, packets, seed):
    rng_master = random.Random(seed)

    print(f"Ordering Benchmark v12 (Algorithm Only)")
    print(f"Orderings : 1–{N_ORDERINGS}   (constraint: protocol < dst_port)")
    print(f"Sizes     : {sizes}")
    print(f"Trials    : {trials} per (size × ordering)")
    print(f"Packets   : {packets:,} per match-time measurement")
    print(f"Total     : {len(sizes)*N_ORDERINGS*trials} conversions")

    all_results = {}  # {n: {ordering_id: aggregated_dict}}

    for n in sizes:
        cat = _size_category(n)
        print(f"\n{'='*78}")
        print(f"  n={n}  ({cat})")
        print(f"{'='*78}")

        # Generate fixed (rules, packets) per trial — shared across orderings
        # so that any per-ordering difference is purely structural.
        trial_inputs = []
        for trial in range(trials):
            tr = random.Random(rng_master.randint(0, 2**31-1))
            trial_inputs.append((build_policy(n, tr), gen_packets(packets, tr)))

        results_for_n = {}
        for oid in range(1, N_ORDERINGS+1):
            trials_data = []
            for (rules, pkts) in trial_inputs:
                m = measure_one_trial(rules, oid, pkts)
                trials_data.append(m)
            results_for_n[oid] = aggregate(trials_data)

        all_results[n] = results_for_n

        # ── Table view ──
        print(f"\n  {'ID':>3} {'Ordering':<22} {'Depth':>6} {'Nodes':>7} "
              f"{'Leaves':>8} {'Cells':>8} {'Conv_ms':>10} "
              f"{'TreeKB':>8} {'PeakKB':>9} {'Match_μs':>10}")
        print("  " + "─"*112)
        for oid in range(1, N_ORDERINGS+1):
            r = results_for_n[oid]
            order_str = _abbrev(ORDERING_OPTIONS[oid])
            print(f"  {oid:>3} {order_str:<22} "
                  f"{r['trf_depth_mean']:>6.1f} "
                  f"{r['n_nodes_mean']:>7.0f} "
                  f"{r['n_leaves_mean']:>8.0f} "
                  f"{r['n_cells_norm_mean']:>8.0f} "
                  f"{r['conv_ms_mean']:>9.1f} "
                  f"{r['tree_bytes_mean']/1024:>7.1f} "
                  f"{r['peak_bytes_mean']/1024:>8.1f} "
                  f"{r['match_us_mean']:>9.2f}")

        # ── Winners / worst (per metric) ──
        print(f"\n  ── Winners / worst (n={n}) ──────────────────────────────────")
        def _best(key, lower=True):
            ranked = sorted(results_for_n.items(),
                            key=lambda kv: kv[1][key+"_mean"])
            best  = ranked[0]  if lower else ranked[-1]
            worst = ranked[-1] if lower else ranked[0]
            return best, worst

        for label, key, lower, unit in [
                ("Smallest TRF (nodes)",   "n_nodes",     True,  "nodes"),
                ("Smallest tree (memory)", "tree_bytes",  True,  "bytes"),
                ("Lowest peak (memory)",   "peak_bytes",  True,  "bytes"),
                ("Fastest conversion",     "conv_ms",     True,  "ms"),
                ("Fastest matching",       "match_us",    True,  "μs/pkt"),
        ]:
            (b_id, b_v), (w_id, w_v) = _best(key, lower)
            ratio = w_v[key+"_mean"] / b_v[key+"_mean"] if b_v[key+"_mean"]>0 else 1
            if unit == "bytes":
                bv = f"{b_v[key+'_mean']/1024:.1f} KB"; wv = f"{w_v[key+'_mean']/1024:.1f} KB"
            else:
                bv = f"{b_v[key+'_mean']:.2f} {unit}"; wv = f"{w_v[key+'_mean']:.2f} {unit}"
            print(f"  {label:<26}  best=Ord{b_id} ({bv})   "
                  f"worst=Ord{w_id} ({wv})   ratio={ratio:.2f}x")

        # ── ASCII bar charts ──
        print(f"\n  ── ASCII bar charts (n={n}) ──")
        render_bar_chart("Tree memory",   results_for_n, "tree_bytes",
                         fmt_str="{:.0f}",  unit="(bytes, lower=better)")
        render_bar_chart("Peak memory",   results_for_n, "peak_bytes",
                         fmt_str="{:.0f}",  unit="(bytes, lower=better)")
        render_bar_chart("Match latency", results_for_n, "match_us",
                         fmt_str="{:.2f}",  unit="(μs/pkt, lower=better)")
        render_bar_chart("Conversion",    results_for_n, "conv_ms",
                         fmt_str="{:.1f}",  unit="(ms, lower=better)")

    # ── Cross-size summary ──
    print(f"\n{'='*78}")
    print(f"  CROSS-SIZE SUMMARY  (mean tree memory / ordering)")
    print(f"{'='*78}")
    print(f"  {'ID':>3} " + " ".join(f"{'n='+str(n):>10}" for n in sizes))
    for oid in range(1, N_ORDERINGS+1):
        cells = [f"{all_results[n][oid]['tree_bytes_mean']/1024:>9.1f}K" for n in sizes]
        print(f"  {oid:>3} " + " ".join(cells))

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Compare all 12 attribute orderings (Step 4 contribution)")
    parser.add_argument("--sizes",   default="50,100,200,400",
                        help="Comma-separated list of policy sizes")
    parser.add_argument("--n",       type=int, default=None,
                        help="(Shortcut) single n; overrides --sizes")
    parser.add_argument("--trials",  type=int, default=5)
    parser.add_argument("--packets", type=int, default=2000)
    parser.add_argument("--seed",    type=int, default=2025)
    parser.add_argument("--output",  default="ordering_benchmark_v12_results.json")
    args = parser.parse_args()

    if args.n is not None:
        sizes = [args.n]
    else:
        sizes = [int(s) for s in args.sizes.split(",")]

    t0 = time.perf_counter()
    results = run_benchmark(sizes, args.trials, args.packets, args.seed)
    elapsed = time.perf_counter() - t0

    # ── JSON output (for paper plots) ──
    payload = {
        "sizes": sizes,
        "trials": args.trials,
        "packets": args.packets,
        "seed": args.seed,
        "elapsed_s": elapsed,
        "orderings": {oid: ORDERING_OPTIONS[oid] for oid in range(1, N_ORDERINGS+1)},
        "results": {
            str(n): {str(oid): vals for oid, vals in res.items()}
            for n, res in results.items()
        },
    }
    Path(args.output).write_text(json.dumps(payload, indent=2))
    print(f"\n{'='*78}")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Results JSON → {args.output}")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
