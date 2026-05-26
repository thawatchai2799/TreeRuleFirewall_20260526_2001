#!/usr/bin/env python3
"""
semantic_verify_v12.py
=====================
Step 1 Verification — Semantic Fidelity (v12)
Small: 1–25 | Medium: 26–100 | Large: 101–400 rules

Usage:
  python semantic_verify_v12.py --dataset policies_v12.jsonl --policies 5000
  python semantic_verify_v12.py --policy-file my_policy.txt
"""
import argparse, json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lrf_trf_app_v12 import (
    parse_policy, convert_policy, lrf_match, trf_match,
    PROTOCOLS, ORDERING_OPTIONS, N_ORDERINGS,
    PORT_MAX, ICMP_TYPE_MAX
)


def boundary_packets(rules) -> list[dict]:
    """Boundary packets targeting range endpoints (off-by-one stress test).

    v12: For ICMP rules, dst_port stores ICMP type (0-255). Boundary packets
    are clamped to the appropriate domain so we don't waste evaluations on
    impossible packets (e.g. ICMP type 8080).
    """
    packets = []
    for r in rules:
        protos = ["TCP","UDP","ICMP"] if r.protocol in ("IP","ANY") else [r.protocol]
        for proto in protos:
            # Per-protocol port domain
            port_max = ICMP_TYPE_MAX if proto == "ICMP" else PORT_MAX
            for src in {r.src_start, (r.src_start+r.src_end)//2, r.src_end,
                        max(0,r.src_start-1), min(2**32-1,r.src_end+1)}:
                for dst in {r.dst_start, r.dst_end}:
                    raw_ports = {r.port_start, r.port_end,
                                 max(0,r.port_start-1), min(port_max,r.port_end+1)}
                    for port in raw_ports:
                        if 0 <= port <= port_max:
                            packets.append({"protocol":proto,"src_ip":src,
                                            "dst_ip":dst,"dst_port":port})
    return packets


def _rand_pkt(rng) -> dict:
    """Generate a random packet with port domain matching protocol."""
    proto = rng.choice(PROTOCOLS)
    port_max = ICMP_TYPE_MAX if proto == "ICMP" else PORT_MAX
    return {"protocol": proto,
            "src_ip":   rng.randint(0, 2**32-1),
            "dst_ip":   rng.randint(0, 2**32-1),
            "dst_port": rng.randint(0, port_max)}


def verify_policy(pol: dict, ordering_id: int, n_random: int, rng) -> dict:
    lines = pol["lines"]
    pid   = pol["policy_id"]
    try:
        trf, report, clean = convert_policy(lines, policy_id=pid,
                                             ordering_id=ordering_id)
    except Exception as e:
        return {"policy_id":pid,"error":str(e),"ok":0,"fail":0}

    ok = fail = 0

    # Random packets (ICMP-aware port domain)
    for _ in range(n_random):
        pkt = _rand_pkt(rng)
        if lrf_match(clean, pkt)==trf_match(trf, pkt): ok+=1
        else: fail+=1

    # Boundary packets
    for pkt in boundary_packets(clean):
        if lrf_match(clean, pkt)==trf_match(trf, pkt): ok+=1
        else: fail+=1

    return {"policy_id":pid, "ok":ok, "fail":fail,
            "trf_depth":report.trf_depth, "n_rules":report.n_rules_clean,
            "size_category":report.size_category}


def main():
    parser = argparse.ArgumentParser()
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dataset",     help=".jsonl dataset file")
    grp.add_argument("--policy-file", help="Single .txt policy file")
    parser.add_argument("--policies",       type=int, default=10000)
    parser.add_argument("--ordering",       type=int, default=4, choices=range(1, N_ORDERINGS+1))
    parser.add_argument("--random-packets", type=int, default=500)
    parser.add_argument("--seed",           type=int, default=42)
    parser.add_argument("--output",         default="semantic_verify_v12_results.json")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    t0  = time.perf_counter()

    if args.policy_file:
        text = Path(args.policy_file).read_text()
        policies = [{"policy_id":0,"lines":text.splitlines(),"injected_anomalies":[]}]
    else:
        with open(args.dataset) as fh:
            all_lines = fh.readlines()
        idx = rng.sample(range(len(all_lines)), k=min(args.policies,len(all_lines)))
        policies = [json.loads(all_lines[i]) for i in sorted(idx)]

    print(f"Semantic Fidelity Verification v12")
    print(f"Policies  : {len(policies):,}")
    print(f"Rand pkts : {args.random_packets}/policy")
    print(f"Ordering  : Option {args.ordering}")
    print(f"Size cats : Small 1–25 | Medium 26–100 | Large 101–400")
    print("─" * 60)

    total_ok=total_fail=0
    results=[]
    cat_stats={"small":{"ok":0,"fail":0},"medium":{"ok":0,"fail":0},"large":{"ok":0,"fail":0}}

    for i, pol in enumerate(policies):
        res = verify_policy(pol, args.ordering, args.random_packets, rng)
        results.append(res)
        total_ok   += res.get("ok",0)
        total_fail += res.get("fail",0)
        cat = res.get("size_category","small")
        if cat in cat_stats:
            cat_stats[cat]["ok"]   += res.get("ok",0)
            cat_stats[cat]["fail"] += res.get("fail",0)

        if (i+1) % max(1,len(policies)//10)==0:
            fid = 100*total_ok/(total_ok+total_fail) if (total_ok+total_fail) else 0
            print(f"  {i+1:>6}/{len(policies)}  OK={total_ok:,}  "
                  f"FAIL={total_fail}  Fidelity={fid:.4f}%", flush=True)

    elapsed  = time.perf_counter()-t0
    fidelity = 100*total_ok/(total_ok+total_fail) if (total_ok+total_fail) else 0

    print("─" * 60)
    print(f"Total evaluations : {total_ok+total_fail:,}")
    print(f"OK                : {total_ok:,}")
    print(f"FAIL              : {total_fail}")
    print(f"Fidelity          : {fidelity:.6f}%")
    print(f"Theorem 1 status  : {'✅ CONFIRMED' if total_fail==0 else '❌ VIOLATION'}")
    print(f"Time              : {elapsed:.2f}s")
    print("\nPer-category fidelity:")
    for cat, st in cat_stats.items():
        tot = st["ok"]+st["fail"]
        fid = 100*st["ok"]/tot if tot>0 else 0
        print(f"  {cat.capitalize():8s}: {fid:.4f}%  ({tot:,} evals, {st['fail']} fail)")

    summary = {
        "n_policies": len(policies),
        "ordering": args.ordering,
        "size_categories": "Small 1-25 | Medium 26-100 | Large 101-400",
        "random_packets_per_policy": args.random_packets,
        "total_evaluations": total_ok+total_fail,
        "total_ok": total_ok, "total_fail": total_fail,
        "fidelity_pct": fidelity,
        "theorem1_confirmed": total_fail==0,
        "elapsed_s": elapsed,
        "per_category": cat_stats,
        "per_policy": results,
    }
    Path(args.output).write_text(json.dumps(summary, indent=2))
    print(f"\nResults → {args.output}")

if __name__ == "__main__":
    main()
