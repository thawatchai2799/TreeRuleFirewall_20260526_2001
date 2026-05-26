#!/usr/bin/env python3
"""
classbench_loader_v12.py
========================
Load ClassBench-ng generated rule sets and convert them to the v12 LRF format.

ClassBench-ng line format (tab-separated):
    @src_ip/prefix  dst_ip/prefix  sport_lo : sport_hi  dport_lo : dport_hi  protocol/mask  flags/mask

Example:
    @176.19.181.33/32  90.145.23.162/32  0 : 65535  1550 : 1550  0x06/0xFF  0x0000/0x0200

This file maps:
- protocol byte 0x06 → TCP, 0x11 → UDP, 0x01 → ICMP, 0x00 with /0x00 mask → IP/ANY
- src_ip range → first matching CIDR (we use prefix as-is)
- dst_ip range → same
- dst_port range → ρ
- src_port is dropped (v12 still uses 4-tuple {protocol, src_ip, dst_ip, dst_port})
- ICMP type: ClassBench encodes ICMP "ports" identically; we clamp to [0, 255]

ClassBench rules have no action field, so we synthesise actions:
- 80% ALLOW, 20% DENY (configurable via --deny-ratio)
- This matches the typical ALLOW-heavy production firewall pattern.
"""

from __future__ import annotations
import argparse, json, random, sys
from dataclasses import dataclass
from pathlib import Path

# Protocol byte → name mapping (IANA)
PROTO_BYTE = {
    0x01: "ICMP",
    0x06: "TCP",
    0x11: "UDP",
}


@dataclass
class CBRule:
    """A ClassBench rule, parsed but not yet converted to LRF format."""
    src_cidr: str
    dst_cidr: str
    sport_lo: int
    sport_hi: int
    dport_lo: int
    dport_hi: int
    proto_byte: int
    proto_mask: int


def parse_classbench_line(line: str) -> CBRule | None:
    """Parse one line of a ClassBench file. Returns None for empty/invalid lines."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Lines start with '@'
    if line.startswith("@"):
        line = line[1:]
    # Split by tab; ClassBench uses TAB as primary separator
    parts = line.split("\t")
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) < 5:
        return None
    src_cidr, dst_cidr = parts[0], parts[1]
    # sport range "lo : hi"
    sport_parts = parts[2].split(":")
    sport_lo, sport_hi = int(sport_parts[0].strip()), int(sport_parts[1].strip())
    # dport range
    dport_parts = parts[3].split(":")
    dport_lo, dport_hi = int(dport_parts[0].strip()), int(dport_parts[1].strip())
    # protocol: "0x06/0xFF"
    proto_parts = parts[4].split("/")
    proto_byte = int(proto_parts[0].strip(), 16)
    proto_mask = int(proto_parts[1].strip(), 16) if len(proto_parts) > 1 else 0xFF
    return CBRule(
        src_cidr=src_cidr, dst_cidr=dst_cidr,
        sport_lo=sport_lo, sport_hi=sport_hi,
        dport_lo=dport_lo, dport_hi=dport_hi,
        proto_byte=proto_byte, proto_mask=proto_mask,
    )


def cb_to_lrf_rule(rule: CBRule, action: str) -> str:
    """Convert a CBRule to the textual LRF format expected by lrf_trf_app_v12.py.

    Format expected: 'PROTO src_cidr dst_cidr port_lo-port_hi ACTION'
    (See parse_policy() in lrf_trf_app_v12.py for the canonical format.)
    """
    # Determine protocol specifier
    if rule.proto_mask == 0:
        # No protocol restriction → IP (covers all)
        proto = "IP"
    elif rule.proto_byte in PROTO_BYTE:
        proto = PROTO_BYTE[rule.proto_byte]
    else:
        # Unknown protocol byte (e.g., GRE 0x2F, ESP 0x32) → treat as ANY
        proto = "ANY"

    # Clamp dst_port range for ICMP rules
    if proto == "ICMP":
        dport_hi = min(rule.dport_hi, 255)
        dport_lo = min(rule.dport_lo, dport_hi)
    else:
        dport_lo = rule.dport_lo
        dport_hi = rule.dport_hi

    return f"{proto} {rule.src_cidr} {rule.dst_cidr} {dport_lo}-{dport_hi} {action}"


def load_classbench_file(path: Path, max_rules: int | None = None,
                         deny_ratio: float = 0.20, seed: int = 42) -> list[str]:
    """Load a ClassBench rule file and convert it to LRF text lines.

    Returns:
        List of LRF rule lines, ready for parse_policy() in v12.
    """
    rng = random.Random(seed)
    rules = []
    skipped = 0
    with path.open() as f:
        for line in f:
            cb = parse_classbench_line(line)
            if cb is None:
                skipped += 1
                continue
            # Synthesise action (deny ratio configurable)
            action = "DENY" if rng.random() < deny_ratio else "ALLOW"
            try:
                lrf_line = cb_to_lrf_rule(cb, action)
                rules.append(lrf_line)
            except (ValueError, KeyError):
                skipped += 1
                continue
            if max_rules and len(rules) >= max_rules:
                break
    # Always end with a deny-all
    rules.append("ANY 0.0.0.0/0 0.0.0.0/0 0-65535 DENY")
    return rules


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to ClassBench rule file (e.g., acl1_1k)")
    ap.add_argument("-o", "--output", help="Output JSONL file with LRF rules", required=True)
    ap.add_argument("--max-rules", type=int, default=None,
                    help="Take at most N rules from the input file")
    ap.add_argument("--deny-ratio", type=float, default=0.20,
                    help="Fraction of rules to assign DENY action (default: 0.20)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rules = load_classbench_file(
        Path(args.input), max_rules=args.max_rules,
        deny_ratio=args.deny_ratio, seed=args.seed,
    )
    with open(args.output, "w") as f:
        # JSONL with one policy
        policy = {
            "policy_id": Path(args.input).stem,
            "n_rules": len(rules) - 1,  # exclude deny-all
            "source": "ClassBench-ng (NeuroCuts redistribution)",
            "rules": rules,
        }
        f.write(json.dumps(policy) + "\n")

    print(f"✅ Loaded {len(rules)-1} rules from {args.input}")
    print(f"   Output → {args.output}")


if __name__ == "__main__":
    main()
