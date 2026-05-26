#!/usr/bin/env python3
"""
scalability_benchmark_v12.py
============================
Step 3 Verification — Scalability & Speedup (v12)
Tests n = 5, 10, 25, 50, 100, 200, 400 (matching v7 for comparison)

Two modes:
  - Single ordering (default): produces the legacy speedup table.
  - --all-orderings          : runs all 12 orderings at every n and prints
                               speedup matrix + match-latency matrix +
                               best/worst-per-n summary. JSON output uses
                               a different shape (results keyed by n then
                               ordering_id).

Usage:
  python scalability_benchmark_v12.py
  python scalability_benchmark_v12.py --max-n 400 --trials 10
  python scalability_benchmark_v12.py --all-orderings --max-n 100
"""
import argparse, json, random, statistics, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    Rule, convert_policy, lrf_match, trf_match,
    PROTOCOLS, ORDERING_OPTIONS, N_ORDERINGS,
    SINGLE_HOSTS, SUBNETS_24, SUBNETS_16, COMMON_PORTS, COMMON_ICMP_TYPES,
    cidr_to_range, _size_category,
    PORT_MAX, ICMP_TYPE_MAX
)


def _make_rule(rng, rule_id):
    """Generate a random rule. ICMP rules use dst_port ∈ [0,255]."""
    src  = rng.choice(SINGLE_HOSTS+SUBNETS_24+["ANY"])
    dst  = rng.choice(SINGLE_HOSTS+SUBNETS_24+["ANY"])
    proto= rng.choices(["TCP","UDP","ICMP","IP","ANY"],weights=[40,25,10,10,15])[0]
    # Choose port from the proper domain
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
    """Generate random packets with port domain matching protocol."""
    pkts = []
    for _ in range(n):
        proto = rng.choice(PROTOCOLS)
        port_max = ICMP_TYPE_MAX if proto == "ICMP" else PORT_MAX
        pkts.append({"protocol":proto,
                     "src_ip":rng.randint(0,2**32-1),
                     "dst_ip":rng.randint(0,2**32-1),
                     "dst_port":rng.randint(0,port_max)})
    return pkts


def measure_us(func, arg, packets):
    t0 = time.perf_counter()
    for p in packets: func(arg, p)
    return (time.perf_counter()-t0)/len(packets)*1e6


def _measure_n_for_ordering(n, ordering_id, trials, packets, seed):
    """Run `trials` measurements for a single (n, ordering) pair.
    Returns aggregated stats."""
    lrf_t=[]; trf_t=[]; depths=[]; conv_ms=[]
    for trial in range(trials):
        tr = random.Random(seed+n*1000+trial)
        rules   = build_policy(n, tr)
        pkts    = gen_packets(packets, tr)

        t0 = time.perf_counter()
        trf, report, clean = convert_policy(rules, policy_id=trial,
                                            ordering_id=ordering_id)
        conv_ms.append((time.perf_counter()-t0)*1000)
        depths.append(report.trf_depth)
        lrf_t.append(measure_us(lrf_match, clean, pkts))
        trf_t.append(measure_us(trf_match, trf,   pkts))

    lm=statistics.mean(lrf_t); ls=statistics.stdev(lrf_t) if len(lrf_t)>1 else 0
    tm=statistics.mean(trf_t); ts=statistics.stdev(trf_t) if len(trf_t)>1 else 0
    dm=statistics.mean(depths)
    sp=lm/tm if tm>0 else float('inf')
    cm=statistics.mean(conv_ms)
    return {
        "depth_mean":dm,"depth_max":max(depths),
        "lrf_mean_us":lm,"lrf_std_us":ls,
        "trf_mean_us":tm,"trf_std_us":ts,
        "speedup":sp,"conv_mean_ms":cm,
    }


def _run_single_ordering(n_list, ordering_id, trials, packets, seed):
    """Original single-ordering scalability table."""
    print(f"{'n':>5} {'cat':>8} {'d':>5} {'LRF_μs':>10} {'TRF_μs':>10} "
          f"{'Speedup':>9} {'Conv_ms':>10}")
    print("─"*65)
    all_results = []
    for n in n_list:
        cat = _size_category(n)
        s = _measure_n_for_ordering(n, ordering_id, trials, packets, seed)
        print(f"{n:>5} {cat:>8} {s['depth_mean']:>5.1f}   "
              f"{s['lrf_mean_us']:>8.3f}±{s['lrf_std_us']:.2f}   "
              f"{s['trf_mean_us']:>8.3f}±{s['trf_std_us']:.2f}   "
              f"{s['speedup']:>7.2f}x   {s['conv_mean_ms']:>8.1f}")
        all_results.append({"n":n,"size_category":cat,**s})

    print()
    max_sp = max(r["speedup"] for r in all_results)
    max_sp_n = next(r["n"] for r in all_results if r["speedup"]==max_sp)
    all_d = {r["depth_max"] for r in all_results}
    print(f"Max speedup : {max_sp:.3f}x at n={max_sp_n}")
    print(f"Depths seen : {sorted(all_d)}  (d≤7: {'✅' if max(all_d)<=7 else '❌'})")
    return {"mode":"single_ordering","ordering":ordering_id,"results":all_results}


def _run_all_orderings(n_list, trials, packets, seed):
    """Multi-ordering scalability comparison: speedup table across 12 orderings."""
    print(f"All-orderings comparison: speedup (LRF_μs / TRF_μs) for each (n, ordering)")
    print()

    # Collect: results[n][ordering_id] = stats
    grid = {n: {} for n in n_list}
    for n in n_list:
        for oid in range(1, N_ORDERINGS+1):
            grid[n][oid] = _measure_n_for_ordering(n, oid, trials, packets, seed)

    # ── Speedup table ──
    print(f"  Speedup matrix (LRF_μs / TRF_μs)")
    header = "  " + f"{'n':>5} | " + " ".join(f"{'O'+str(oid):>7}" for oid in range(1, N_ORDERINGS+1))
    print(header)
    print("  " + "─"*len(header))
    for n in n_list:
        row = "  " + f"{n:>5} | " + " ".join(
            f"{grid[n][oid]['speedup']:>6.2f}x" for oid in range(1, N_ORDERINGS+1))
        print(row)

    # ── TRF match latency table ──
    print()
    print(f"  TRF match latency (μs/packet)")
    print(header)
    print("  " + "─"*len(header))
    for n in n_list:
        row = "  " + f"{n:>5} | " + " ".join(
            f"{grid[n][oid]['trf_mean_us']:>7.2f}" for oid in range(1, N_ORDERINGS+1))
        print(row)

    # ── Per-n best/worst ──
    print()
    print(f"  Best/worst ordering per n (by TRF match latency, lower=better)")
    print(f"  {'n':>5}   {'best':<24}   {'worst':<24}   ratio")
    print("  " + "─"*70)
    for n in n_list:
        ranked = sorted(grid[n].items(), key=lambda kv: kv[1]['trf_mean_us'])
        bid, bv = ranked[0];  wid, wv = ranked[-1]
        ratio = wv['trf_mean_us'] / bv['trf_mean_us'] if bv['trf_mean_us']>0 else 1
        print(f"  {n:>5}   Ord{bid:<2}: {bv['trf_mean_us']:.3f} μs        "
              f"Ord{wid:<2}: {wv['trf_mean_us']:.3f} μs        {ratio:.2f}x")

    return {"mode":"all_orderings",
            "results":{str(n):{str(oid):s for oid,s in row.items()}
                       for n,row in grid.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials",   type=int, default=10)
    parser.add_argument("--packets",  type=int, default=5000)
    parser.add_argument("--ordering", type=int, default=4, choices=range(1, N_ORDERINGS+1),
                        help="Ordering (single-mode only)")
    parser.add_argument("--all-orderings", action="store_true",
                        help="Compare all 12 orderings instead of single")
    parser.add_argument("--max-n",    type=int, default=400)
    parser.add_argument("--seed",     type=int, default=2025)
    parser.add_argument("--output",   default="scalability_v12_results.json")
    args = parser.parse_args()

    N_LIST = [n for n in [5,10,25,50,100,200,400] if n<=args.max_n]

    print(f"Scalability Benchmark v12 (Algorithm Only)")
    print(f"Size cats: Small 1–25 | Medium 26–100 | Large 101–400")
    print(f"Trials={args.trials}  Pkts/trial={args.packets:,}  max_n={args.max_n}")
    if args.all_orderings:
        print(f"Mode    : ALL 12 ORDERINGS")
    else:
        print(f"Mode    : single ordering (Option {args.ordering})")
    print()

    if args.all_orderings:
        payload = _run_all_orderings(N_LIST, args.trials, args.packets, args.seed)
    else:
        payload = _run_single_ordering(N_LIST, args.ordering, args.trials,
                                        args.packets, args.seed)
        # Keep legacy "results" array shape for backward compat
        payload["ordering"] = args.ordering

    payload["size_categories"] = "Small 1-25 | Medium 26-100 | Large 101-400"
    Path(args.output).write_text(json.dumps(payload, indent=2))
    print(f"\nResults → {args.output}")

if __name__ == "__main__":
    main()
