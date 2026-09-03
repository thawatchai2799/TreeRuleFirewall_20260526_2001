"""
Two-rule counterexample for Proposition 4 (non-invariance of structural cost).

Policy P:
    r1: TCP ANY ANY 80  -> ALLOW
    r2: deny-all

Stage 4 yields five cells under every admissible ordering:
    TCP  [0,79] DENY, TCP [80,80] ALLOW, TCP [81,65535] DENY,
    UDP  [0,65535] DENY, ICMP [0,255] DENY.

BuildTRF then produces
    Ordering 1 (protocol, src_ip, dst_ip, dst_port): 1 + 3 + 3 + 3 = 10 internal nodes
    Ordering 5 (protocol, dst_port, src_ip, dst_ip): 1 + 3 + 5 + 5 = 14 internal nodes
with five leaves in both cases.  Since 14 != 10, node count is not constant
on the admissible set.

Run:  python tests/test_proposition4_counterexample.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from lrf_trf_app_v12 import convert_policy, ORDERING_OPTIONS  # noqa: E402

POLICY = ["TCP ANY ANY 80 ALLOW", "ANY ANY ANY ANY DENY"]
EXPECTED_INTERNAL = {1: 10, 5: 14}
EXPECTED_LEAVES = 5
EXPECTED_CELLS = 5


def main() -> int:
    ok = True
    print("Proposition 4 counterexample: two-rule policy under all 12 orderings")
    print(f"{'ID':>2}  {'ordering':<45} {'cells':>5} {'internal':>8} {'leaves':>6}")
    for oid in range(1, 13):
        _, rep, _ = convert_policy(POLICY, ordering_id=oid)
        print(f"{oid:>2}  {'->'.join(ORDERING_OPTIONS[oid]):<45} "
              f"{rep.n_cells_normalized:>5} {rep.n_nodes:>8} {rep.n_leaves:>6}")
        if rep.n_cells_normalized != EXPECTED_CELLS or rep.n_leaves != EXPECTED_LEAVES:
            ok = False
        if oid in EXPECTED_INTERNAL and rep.n_nodes != EXPECTED_INTERNAL[oid]:
            ok = False
    print()
    print("PASS: ordering 1 -> 10 internal nodes, ordering 5 -> 14 internal nodes, 5 leaves each"
          if ok else "FAIL: counts differ from the values stated in the paper")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
