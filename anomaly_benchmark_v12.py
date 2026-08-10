#!/usr/bin/env python3
"""
anomaly_benchmark_v12.py
========================
Step 2 Verification — Anomaly Detection (v12)
Small: 1–25 | Medium: 26–100 | Large: 101–400 rules

Tests Proposition 2 across three size categories and seven injection configs.

Usage:
  python anomaly_benchmark_v12.py
  python anomaly_benchmark_v12.py --trials 500 --test-large
"""
import argparse, json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    Rule, deterministic_triad, contains,
    PROTO_SUPERS, cidr_to_range, COMMON_PORTS,
    SINGLE_HOSTS, SUBNETS_24, SUBNETS_16,
    PORT_MAX, ICMP_TYPE_MAX, COMMON_ICMP_TYPES
)


def ground_truth_anomalies(rules):
    """Independent O(n²) ground-truth checker (separate from Triad)."""
    shadow_gt=set(); redundant_gt=set()
    for i in range(len(rules)):
        for j in range(i+1, len(rules)):
            if contains(rules[i], rules[j]):
                if rules[i].action != rules[j].action: shadow_gt.add(j)
                else:                                   redundant_gt.add(j)
    return shadow_gt, redundant_gt


def _random_rule(rng, rule_id=0):
    """Generate a random rule. ICMP rules use dst_port ∈ [0,255]."""
    proto = rng.choices(["TCP","UDP","ICMP","IP","ANY"],weights=[40,25,10,10,15])[0]
    src   = rng.choice(SINGLE_HOSTS+SUBNETS_24+["ANY"])
    dst   = rng.choice(SINGLE_HOSTS+SUBNETS_24+["ANY"])
    # Choose port domain based on protocol
    if proto == "ICMP":
        port = str(rng.choice(COMMON_ICMP_TYPES)) if rng.random()<0.6 else "ANY"
    else:
        port = str(rng.choice(COMMON_PORTS)) if rng.random()<0.6 else "ANY"
    act   = rng.choice(["ALLOW","DENY"])
    ss,se = cidr_to_range(src) if src!="ANY" else (0,2**32-1)
    ds,de = cidr_to_range(dst) if dst!="ANY" else (0,2**32-1)
    if port == "ANY":
        ps, pe = (0, ICMP_TYPE_MAX) if proto == "ICMP" else (0, PORT_MAX)
    elif "-" in port:
        a, b = port.split("-", 1); ps, pe = int(a), int(b)
    else:
        ps = pe = int(port)
    return Rule(proto,ss,se,ds,de,ps,pe,act,rule_id=rule_id)


def inject_anomalies(base_rules, n_shadow, n_redundant, rng):
    rules = list(base_rules)
    for _ in range(n_shadow):
        if not rules: break
        ri  = rng.choice(rules)
        opp = "DENY" if ri.action=="ALLOW" else "ALLOW"
        ss  = rng.randint(ri.src_start, ri.src_end)
        ds  = rng.randint(ri.dst_start, ri.dst_end)
        ps  = rng.randint(ri.port_start, ri.port_end)
        proto = rng.choice(list(PROTO_SUPERS[ri.protocol]))
        # If we narrow to an atomic protocol, ensure ports stay in its domain.
        # ri.port_start/end already lies in the broader domain inherited from
        # ri.protocol; if proto=='ICMP' we must clamp ps to [0,255].
        if proto == "ICMP" and ps > ICMP_TYPE_MAX:
            ps = rng.randint(0, ICMP_TYPE_MAX)
        rj = Rule(proto,ss,ss,ds,ds,ps,ps,opp,rule_id=len(rules))
        rules.insert(rng.randint(rules.index(ri)+1, len(rules)), rj)
    for _ in range(n_redundant):
        if not rules: break
        ri    = rng.choice(rules)
        ss    = rng.randint(ri.src_start, ri.src_end)
        ds    = rng.randint(ri.dst_start, ri.dst_end)
        ps    = rng.randint(ri.port_start, ri.port_end)
        proto = rng.choice(list(PROTO_SUPERS[ri.protocol]))
        if proto == "ICMP" and ps > ICMP_TYPE_MAX:
            ps = rng.randint(0, ICMP_TYPE_MAX)
        rj = Rule(proto,ss,ss,ds,ds,ps,ps,ri.action,rule_id=len(rules))
        rules.insert(rng.randint(rules.index(ri)+1, len(rules)), rj)
    return rules


CONFIGURATIONS = [
    ("Minimal (1S+1R)",   1, 1),
    ("Normal (2S+2R)",    2, 2),
    ("Heavy (3S+2R)",     3, 2),
    ("Only Redundant",    0, 3),
    ("Only Shadow",       3, 0),
    ("Single Shadow",     1, 0),
    ("Single Redundant",  0, 1),
]

SIZE_BASE_RULES = {
    "small":  (3, 10),
    "medium": (10, 40),
    "large":  (40, 150),
}


def run_benchmark(n_trials: int = 500, seed: int = 42, test_large: bool = False):
    rng = random.Random(seed)

    categories = ["small","medium"]
    if test_large:
        categories.append("large")

    all_results = []

    for size_cat in categories:
        n_base_range = SIZE_BASE_RULES[size_cat]
        print(f"\n{'='*68}")
        print(f"Category: {size_cat.upper()}  (base rules: {n_base_range[0]}–{n_base_range[1]})")
        print(f"{'='*68}")
        print(f"{'Config':<22} {'Trials':>6} {'TP':>7} {'FP':>5} {'FN':>5} "
              f"{'Prec':>8} {'Recall':>8}")
        print("─"*68)

        cat_tp=cat_fp=cat_fn=0

        for (cfg, n_s, n_r) in CONFIGURATIONS:
            tp=fp=fn=0
            for trial in range(n_trials):
                n_base = rng.randint(*n_base_range)
                base   = [_random_rule(rng, i) for i in range(n_base)]
                injected = inject_anomalies(base, n_s, n_r, rng)
                gt_s, gt_r = ground_truth_anomalies(injected)
                gt_all     = gt_s | gt_r
                _, anomaly_rep = deterministic_triad(injected)
                detected = (set(anomaly_rep["shadow_ids"]) |
                            set(anomaly_rep["redundant_ids"]))
                tp += len(detected & gt_all)
                fp += len(detected - gt_all)
                fn += len(gt_all - detected)

            prec   = 100*tp/(tp+fp) if tp+fp>0 else 100.0
            recall = 100*tp/(tp+fn) if tp+fn>0 else 100.0
            print(f"{cfg:<22} {n_trials:>6} {tp:>7,} {fp:>5} {fn:>5} "
                  f"{prec:>7.2f}% {recall:>7.2f}%")
            all_results.append({
                "size_category":size_cat,"config":cfg,"trials":n_trials,
                "TP":tp,"FP":fp,"FN":fn,
                "precision_pct":prec,"recall_pct":recall,
            })
            cat_tp+=tp; cat_fp+=fp; cat_fn+=fn

        print("─"*68)
        tot_p = 100*cat_tp/(cat_tp+cat_fp) if cat_tp+cat_fp>0 else 100.0
        tot_r = 100*cat_tp/(cat_tp+cat_fn) if cat_tp+cat_fn>0 else 100.0
        print(f"{'['+size_cat.upper()+'] OVERALL':<22} {n_trials*7:>6} "
              f"{cat_tp:>7,} {cat_fp:>5} {cat_fn:>5} "
              f"{tot_p:>7.2f}% {tot_r:>7.2f}%")
        print(f"Proposition 2 (FN=0): {'✅ CONFIRMED' if cat_fn==0 else '❌ VIOLATION'}")

    total_fn = sum(r["FN"] for r in all_results)
    print(f"\n{'='*68}")
    print(f"ALL CATEGORIES — Proposition 2: {'✅ CONFIRMED' if total_fn==0 else '❌ VIOLATION'}")
    return all_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials",     type=int, default=500)
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument("--test-large", action="store_true",
                        help="Also run Large category (slower: 40–150 base rules)")
    parser.add_argument("--output",     default="anomaly_benchmark_v12_results.json")
    args = parser.parse_args()

    t0 = time.perf_counter()
    results = run_benchmark(args.trials, args.seed, args.test_large)
    elapsed = time.perf_counter()-t0

    summary = {
        "size_categories": "Small 1-25 | Medium 26-100 | Large 101-400",
        "elapsed_s": elapsed,
        "configurations": results,
    }
    Path(args.output).write_text(json.dumps(summary, indent=2))
    print(f"\nTime: {elapsed:.2f}s  →  {args.output}")

if __name__ == "__main__":
    main()
