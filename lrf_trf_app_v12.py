#!/usr/bin/env python3
"""
lrf_trf_app_v12.py
=================
LRF-to-TRF Firewall Policy Conversion Framework — Version 10
Algorithm-Only (No ML) | Default scale: 5,000 policies
Policy sizes: Small (1–25 rules), Medium (26–100 rules), Large (101–400 rules)

Changes from v7 → v8:
  - Size categories: Small 1–25, Medium 26–100, Large 101–400
  - Chunked/streaming cell processing to handle Large policies (n=400, N=O(n³))
  - Per-policy memory cleanup after conversion
  - Progress reporting for long-running conversions
  - Worker count auto-tuned by category (fewer workers for Large)
  - Timeout protection per policy in batch mode

Changes from v8 → v12:
  - ORDERING_OPTIONS expanded: 6 → 12 (constraint: protocol must precede dst_port)
    * IDs 1–6   : original orderings (protocol first)         — backward compatible
    * IDs 7–12  : new orderings (protocol not first, but still before dst_port)
  - ICMP semantics for dst_port:
    * When protocol ∈ {ICMP}, the dst_port field stores ICMP type (0–255)
    * Validation enforces 0 ≤ icmp_type ≤ 255 at parse time
    * Decomposition uses 256 as the upper bound for ICMP atoms (was 65536)
    * Generators and benchmark packet samplers respect the ICMP type range
  - Default dataset size : 100,000 → 5,000 policies (faster end-to-end runs)
  - Default benchmark sample sizes scaled accordingly

Authors : Thawatchai Chomsiri (algorithm design & proofs)
          AI-assisted implementation (Claude, Anthropic, 2025)
License : MIT
"""

import argparse, gc, json, os, random, sys, time
from dataclasses import dataclass, field, asdict
from ipaddress import IPv4Address, IPv4Network
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════
# 1. CONSTANTS & DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

PROTOCOLS    = ["TCP", "UDP", "ICMP"]
PROTO_SUPERS = {
    "IP":   {"TCP","UDP","ICMP"}, "ANY": {"TCP","UDP","ICMP"},
    "TCP":  {"TCP"},  "UDP": {"UDP"},  "ICMP": {"ICMP"},
}
ACTIONS = ["ALLOW", "DENY"]

# v12 size categories
SIZE_CATEGORIES = {
    "small":  (1,   25),
    "medium": (26,  100),
    "large":  (101, 400),
}

# ── Port / ICMP-type bounds ──────────────────────────────────────────────
# For TCP/UDP : dst_port ∈ [0, 65535]
# For ICMP    : dst_port stores ICMP type ∈ [0, 255]
PORT_MAX      = 65535
ICMP_TYPE_MAX = 255

def _port_max_for_proto(proto: str) -> int:
    """Return the maximum allowed dst_port value for an atomic protocol."""
    return ICMP_TYPE_MAX if proto == "ICMP" else PORT_MAX

# ── Attribute orderings (12 valid permutations) ──────────────────────────
# Constraint: 'protocol' must appear BEFORE 'dst_port' in every ordering.
# This is a semantic requirement — dst_port has different domains depending
# on protocol (0–65535 for TCP/UDP, 0–255 for ICMP), so we must know the
# protocol before branching on dst_port.
#
# IDs 1–6  : protocol is the first attribute (original orderings, kept from v8).
# IDs 7–12 : protocol is NOT first, but still precedes dst_port.
ORDERING_OPTIONS = {
    # ── Original 6 (protocol first) ──────────────────────────────────────
    1: ["protocol","src_ip","dst_ip","dst_port"],
    2: ["protocol","src_ip","dst_port","dst_ip"],
    3: ["protocol","dst_ip","src_ip","dst_port"],
    4: ["protocol","dst_ip","dst_port","src_ip"],   # default
    5: ["protocol","dst_port","src_ip","dst_ip"],
    6: ["protocol","dst_port","dst_ip","src_ip"],
    # ── New 6 (protocol not first, but still before dst_port) ────────────
    7:  ["src_ip","protocol","dst_ip","dst_port"],
    8:  ["src_ip","protocol","dst_port","dst_ip"],
    9:  ["src_ip","dst_ip","protocol","dst_port"],
    10: ["dst_ip","protocol","src_ip","dst_port"],
    11: ["dst_ip","protocol","dst_port","src_ip"],
    12: ["dst_ip","src_ip","protocol","dst_port"],
}

N_ORDERINGS = len(ORDERING_OPTIONS)  # 12


def validate_ordering(ordering: list) -> None:
    """Verify that 'protocol' precedes 'dst_port' in the given ordering."""
    if "protocol" not in ordering or "dst_port" not in ordering:
        raise ValueError(f"Ordering must contain 'protocol' and 'dst_port': {ordering}")
    if ordering.index("protocol") >= ordering.index("dst_port"):
        raise ValueError(
            f"Invalid ordering {ordering!r}: 'protocol' must precede 'dst_port'."
        )

COMMON_PORTS  = [22,80,443,3306,5432,8080,8443,25,53,110,143,993,3389,6379,27017]
SUBNETS_24    = ["10.0.1.0/24","10.0.2.0/24","192.168.1.0/24","192.168.2.0/24",
                 "172.16.0.0/24","172.16.1.0/24","10.10.0.0/24","10.10.1.0/24",
                 "10.20.0.0/24","10.30.0.0/24","192.168.10.0/24","192.168.20.0/24"]
SUBNETS_16    = ["10.0.0.0/16","192.168.0.0/16","172.16.0.0/16","10.10.0.0/16",
                 "10.20.0.0/16","172.31.0.0/16"]
SINGLE_HOSTS  = ["10.0.1.5","10.0.2.10","192.168.1.100","172.16.0.50",
                 "10.0.1.200","192.168.2.55","10.10.0.1","10.10.1.1",
                 "10.20.0.5","172.16.1.10","192.168.10.50","10.30.0.1"]


@dataclass
class Rule:
    protocol:   str
    src_start:  int
    src_end:    int
    dst_start:  int
    dst_end:    int
    port_start: int
    port_end:   int
    action:     str
    rule_id:    int = 0


@dataclass
class Cell:
    proto:      str
    src_start:  int; src_end:   int
    dst_start:  int; dst_end:   int
    port_start: int; port_end:  int
    action:     str


@dataclass
class TRFNode:
    attribute: str
    ranges:    list = field(default_factory=list)
    action:    Optional[str] = None
    is_leaf:   bool = False


@dataclass
class ConversionReport:
    policy_id:          int
    n_rules_in:         int
    n_anomalies_shadow: int
    n_anomalies_redund: int
    n_rules_clean:      int
    n_cells_raw:        int
    n_cells_normalized: int
    trf_depth:          int
    n_leaves:           int
    n_nodes:            int
    attribute_ordering: int
    conversion_time_s:  float
    size_category:      str = "unknown"
    # ── v12 ICMP statistics ──────────────────────────────────────────────
    n_icmp_rules:       int = 0   # rules whose protocol set includes ICMP
    n_icmp_pure_rules:  int = 0   # rules with protocol == 'ICMP' exactly
    icmp_type_min:      int = -1  # smallest ICMP type seen (-1 if none)
    icmp_type_max:      int = -1  # largest  ICMP type seen (-1 if none)


# ═══════════════════════════════════════════════════════════════════════════
# 2. UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def ip_to_int(s: str) -> int:
    return int(IPv4Address(s))

def cidr_to_range(cidr: str):
    if "/" in cidr:
        net = IPv4Network(cidr, strict=False)
        return int(net.network_address), int(net.broadcast_address)
    return ip_to_int(cidr), ip_to_int(cidr)

def int_to_ip(n: int) -> str:
    return str(IPv4Address(n))

def contains(ri: Rule, rj: Rule) -> bool:
    """C1–C4 containment test (exact integer arithmetic, no approximation)."""
    return (PROTO_SUPERS[rj.protocol] <= PROTO_SUPERS[ri.protocol] and
            ri.src_start  <= rj.src_start  and rj.src_end  <= ri.src_end  and
            ri.dst_start  <= rj.dst_start  and rj.dst_end  <= ri.dst_end  and
            ri.port_start <= rj.port_start and rj.port_end <= ri.port_end)

def _size_category(n_rules: int) -> str:
    if n_rules <= 25:   return "small"
    if n_rules <= 100:  return "medium"
    return "large"


# ═══════════════════════════════════════════════════════════════════════════
# 3. STEP 1 — PARSE + DENY-ALL NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def parse_policy(lines) -> list[Rule]:
    rules = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 5:
            raise ValueError(f"Line {i+1}: expected 5 fields, got {len(parts)}")
        proto, src, dst, port_s, action = parts
        proto = proto.upper(); action = action.upper()
        if proto not in PROTO_SUPERS:
            raise ValueError(f"Unknown protocol {proto!r} on line {i+1}")
        if action not in ACTIONS:
            raise ValueError(f"Unknown action {action!r} on line {i+1}")
        ss, se = cidr_to_range(src)  if src  != "ANY" else (0, 2**32-1)
        ds, de = cidr_to_range(dst)  if dst  != "ANY" else (0, 2**32-1)
        if port_s == "ANY":   ps, pe = 0, PORT_MAX
        elif "-" in port_s:   a,b=port_s.split("-",1); ps,pe=int(a),int(b)
        else:                  ps = pe = int(port_s)

        # ── ICMP-type validation ──────────────────────────────────────────
        # For pure ICMP rules, dst_port stores the ICMP type and MUST be 0-255.
        # If the user wrote "ANY" for an ICMP rule, we narrow it to [0, 255].
        if proto == "ICMP":
            if port_s == "ANY":
                ps, pe = 0, ICMP_TYPE_MAX
            else:
                if not (0 <= ps <= ICMP_TYPE_MAX and 0 <= pe <= ICMP_TYPE_MAX):
                    raise ValueError(
                        f"Line {i+1}: ICMP type {port_s!r} out of range "
                        f"(must be 0–{ICMP_TYPE_MAX})"
                    )
        else:
            # Generic port validation for TCP / UDP / IP / ANY rules
            if not (0 <= ps <= PORT_MAX and 0 <= pe <= PORT_MAX):
                raise ValueError(
                    f"Line {i+1}: port {port_s!r} out of range (0–{PORT_MAX})"
                )

        rules.append(Rule(proto, ss, se, ds, de, ps, pe, action, rule_id=len(rules)))

    def _is_deny_all(r):
        return (PROTO_SUPERS[r.protocol] == {"TCP","UDP","ICMP"} and
                r.src_start==0 and r.src_end==2**32-1 and
                r.dst_start==0 and r.dst_end==2**32-1 and
                r.port_start==0 and r.port_end==PORT_MAX and r.action=="DENY")

    if not rules or not _is_deny_all(rules[-1]):
        rules.append(Rule("ANY",0,2**32-1,0,2**32-1,0,PORT_MAX,"DENY",rule_id=len(rules)))
    return rules


# ═══════════════════════════════════════════════════════════════════════════
# 4. STEP 2 — DETERMINISTIC TRIAD (STAGE C ONLY)
# ═══════════════════════════════════════════════════════════════════════════

def deterministic_triad(rules: list[Rule]) -> tuple[list[Rule], dict]:
    """
    Exhaustive O(n²) pairwise containment.
    Theorem 3: Recall = 1.0 guaranteed (exact arithmetic, no sampling).
    """
    n = len(rules)
    shadow_idx    = set()
    redundant_idx = set()
    for i in range(n):
        for j in range(i+1, n):
            if j in shadow_idx or j in redundant_idx:
                continue
            if contains(rules[i], rules[j]):
                if rules[i].action != rules[j].action:
                    shadow_idx.add(j)
                else:
                    redundant_idx.add(j)
    flagged = shadow_idx | redundant_idx
    clean   = [r for k, r in enumerate(rules) if k not in flagged]
    return clean, {
        "n_shadow":      len(shadow_idx),
        "n_redundant":   len(redundant_idx),
        "shadow_ids":    sorted(shadow_idx),
        "redundant_ids": sorted(redundant_idx),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. STEP 4 — UNIFIED 4D DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════════

def decompose_4d(rules: list[Rule]) -> list[Cell]:
    """
    Phase 1: Protocol expansion (atomic protocols).
    Phase 2: 3D sweep-line — collect cut points, Cartesian product, first-match assignment.
    Phase 3: Handled by projection normalization (Step 5).

    v12: dst_port domain is protocol-dependent. For atom=ICMP the upper bound
    is 255 (ICMP type), for TCP/UDP it is 65535. Each atom's sweep uses its
    own port_max, and ICMP rules with ports >255 are clamped (this only
    matters for super-protocol rules like 'IP ANY' or 'ANY ANY' that are
    expanded into ICMP atoms).

    Memory note: For large n, N = O(n³) cells. The list is held in RAM during
    normalization; for n=400 in the worst case this can be tens of millions of
    cells. In practice the directional merge reduces this significantly.
    """
    proto_rules: dict[str, list[Rule]] = {p: [] for p in PROTOCOLS}
    for r in rules:
        for atom in PROTO_SUPERS[r.protocol]:
            proto_rules[atom].append(r)

    all_cells: list[Cell] = []

    for atom, prules in proto_rules.items():
        if not prules:
            continue

        # Protocol-dependent port bound.
        atom_port_max = _port_max_for_proto(atom)

        # Per-rule clamping for this atom's domain.
        # Example: an "ANY ANY ANY 8080 ALLOW" rule projected onto ICMP becomes
        # invalid (8080 > 255), so we skip it for the ICMP atom.
        clamped: list[tuple[Rule,int,int]] = []
        for r in prules:
            ps = max(0, r.port_start)
            pe = min(atom_port_max, r.port_end)
            if ps > pe:
                continue   # rule does not apply to this atom's port domain
            clamped.append((r, ps, pe))
        if not clamped:
            continue

        src_pts  = sorted({0} | {r.src_start  for (r,_,_) in clamped} |
                                {r.src_end+1 for (r,_,_) in clamped} | {2**32})
        dst_pts  = sorted({0} | {r.dst_start  for (r,_,_) in clamped} |
                                {r.dst_end+1 for (r,_,_) in clamped} | {2**32})
        port_pts = sorted({0} | {ps    for (_,ps,_) in clamped} |
                                {pe+1  for (_,_,pe) in clamped} | {atom_port_max+1})

        src_segs  = [(src_pts[i],  src_pts[i+1]-1)  for i in range(len(src_pts)-1)]
        dst_segs  = [(dst_pts[i],  dst_pts[i+1]-1)  for i in range(len(dst_pts)-1)]
        port_segs = [(port_pts[i], port_pts[i+1]-1) for i in range(len(port_pts)-1)]

        for (ss, se) in src_segs:
            for (ds, de) in dst_segs:
                for (ps, pe) in port_segs:
                    action = "DENY"
                    for (r, rps, rpe) in clamped:
                        if (r.src_start<=ss and se<=r.src_end and
                            r.dst_start<=ds and de<=r.dst_end and
                            rps<=ps and pe<=rpe):
                            action = r.action
                            break
                    all_cells.append(Cell(atom,ss,se,ds,de,ps,pe,action))

    return all_cells


# ═══════════════════════════════════════════════════════════════════════════
# 6. STEP 5 — PROJECTION NORMALIZATION (ALGORITHM 1)
# ═══════════════════════════════════════════════════════════════════════════

def projection_normalization(cells: list[Cell], ordering: list[str]) -> list[Cell]:
    """
    Algorithm 1: Re-cut cells on each non-protocol axis in A* order.
    Guarantees: projections onto any prefix of A* are pairwise disjoint.
    Foundation of Theorem 2 (Disjointness Invariant).

    v12 changes:
      (a) When axis == 'dst_port', the upper bound is protocol-dependent
          (ICMP → 255, TCP/UDP → 65535).
      (b) Cells are grouped by protocol ONLY when the protocol attribute has
          already been branched on in the TRF — i.e., when the current axis
          comes AFTER 'protocol' in the ordering. For axes that come BEFORE
          'protocol', cells must be cut using GLOBAL cut points (taken across
          all protocols) so that the disjointness invariant holds at the
          higher levels of the tree.
    """
    import copy

    non_proto = [a for a in ordering if a != "protocol"]
    proto_pos = ordering.index("protocol")  # position of 'protocol' in ordering

    def get_axis(c, ax):
        if ax=="src_ip":   return c.src_start,  c.src_end
        if ax=="dst_ip":   return c.dst_start,  c.dst_end
        if ax=="dst_port": return c.port_start, c.port_end

    def set_axis(c, ax, s, e):
        nc = copy.copy(c)
        if ax=="src_ip":   nc.src_start,  nc.src_end  = s, e
        elif ax=="dst_ip": nc.dst_start,  nc.dst_end  = s, e
        else:              nc.port_start, nc.port_end = s, e
        return nc

    current = cells
    for axis in non_proto:
        axis_pos    = ordering.index(axis)
        before_proto = axis_pos < proto_pos

        if before_proto:
            # ── Global cut: this axis is branched BEFORE protocol in the TRF.
            # All protocols must share the same cut points on this axis.
            # (dst_port can never be 'before_proto' because the constraint
            #  protocol < dst_port is enforced; dst_port is always after.)
            max_val = 2**32 - 1   # only IPs are possible here
            pts_set = {0, max_val+1}
            for c in current:
                s, e = get_axis(c, axis)
                pts_set.add(s); pts_set.add(e+1)
            pts  = sorted(pts_set)
            segs = [(pts[i], pts[i+1]-1) for i in range(len(pts)-1) if pts[i]<=pts[i+1]-1]

            new_cells: list[Cell] = []
            for c in current:
                cs, ce = get_axis(c, axis)
                sub = [(s,e) for (s,e) in segs if cs<=s and e<=ce]
                if len(sub)==1 and sub[0]==(cs,ce):
                    new_cells.append(c)
                else:
                    for (s,e) in sub:
                        new_cells.append(set_axis(c, axis, s, e))
            current = new_cells

        else:
            # ── Per-protocol cut: this axis is branched AFTER protocol in the
            # TRF, so each atomic protocol's subtree can have its own cuts.
            groups: dict[str, list] = {p: [] for p in PROTOCOLS}
            for c in current:
                groups[c.proto].append(c)

            new_cells = []
            for proto, grp in groups.items():
                if not grp:
                    continue
                # Protocol-aware upper bound for the dst_port axis.
                if axis == "dst_port":
                    max_val = _port_max_for_proto(proto)
                else:
                    max_val = 2**32 - 1

                pts_set = {0, max_val+1}
                for c in grp:
                    s, e = get_axis(c, axis)
                    pts_set.add(s); pts_set.add(e+1)
                pts  = sorted(pts_set)
                segs = [(pts[i], pts[i+1]-1) for i in range(len(pts)-1) if pts[i]<=pts[i+1]-1]

                for c in grp:
                    cs, ce = get_axis(c, axis)
                    sub = [(s,e) for (s,e) in segs if cs<=s and e<=ce]
                    if len(sub)==1 and sub[0]==(cs,ce):
                        new_cells.append(c)
                    else:
                        for (s,e) in sub:
                            new_cells.append(set_axis(c, axis, s, e))
            current = new_cells

    return current


# ═══════════════════════════════════════════════════════════════════════════
# 7. STEP 6 — BUILD TRF
# ═══════════════════════════════════════════════════════════════════════════

def build_trf(cells: list[Cell], ordering: list[str]) -> TRFNode:
    def get_range(c, attr):
        if attr=="protocol": return c.proto,       c.proto
        if attr=="src_ip":   return c.src_start,   c.src_end
        if attr=="dst_ip":   return c.dst_start,   c.dst_end
        if attr=="dst_port": return c.port_start,  c.port_end

    def _build(subset, depth):
        if depth == len(ordering):
            return TRFNode(attribute="leaf",
                           action=subset[0].action if subset else "DENY",
                           is_leaf=True)
        attr = ordering[depth]
        node = TRFNode(attribute=attr)
        groups: dict = {}
        for c in subset:
            k = get_range(c, attr)
            if k not in groups: groups[k] = []
            groups[k].append(c)
        for rng, grp in sorted(groups.items(), key=lambda x: x[0]):
            node.ranges.append((rng, _build(grp, depth+1)))
        return node

    return _build(cells, 0)


def trf_depth(node: TRFNode) -> int:
    if node.is_leaf or not node.ranges: return 0
    return 1 + max(trf_depth(ch) for _, ch in node.ranges)

def trf_node_count(node: TRFNode) -> tuple[int,int]:
    if node.is_leaf: return 0, 1
    ni, nl = 1, 0
    for _, ch in node.ranges:
        ci, cl = trf_node_count(ch); ni+=ci; nl+=cl
    return ni, nl


def trf_size_bytes(node: TRFNode) -> int:
    """Recursive deep-size of a TRF tree using sys.getsizeof.

    Counts: TRFNode objects, the .ranges list at each internal node, and
    each (range_tuple, child) entry. Strings and ints inside ranges are
    not deep-counted (they are usually small/intern'd) but are included
    via sys.getsizeof of the tuple.

    Used by ordering_benchmark_v12.py to compare TRF memory across orderings.
    """
    import sys as _sys
    sz = _sys.getsizeof(node)
    if not node.is_leaf and node.ranges:
        sz += _sys.getsizeof(node.ranges)
        for rng, ch in node.ranges:
            sz += _sys.getsizeof(rng)
            sz += trf_size_bytes(ch)
    return sz


# ═══════════════════════════════════════════════════════════════════════════
# 8. MATCHING (for verification)
# ═══════════════════════════════════════════════════════════════════════════

def trf_match(node: TRFNode, pkt: dict) -> str:
    if node.is_leaf: return node.action
    val = pkt[node.attribute]
    for (rng, ch) in node.ranges:
        if node.attribute=="protocol":
            if val==rng[0]: return trf_match(ch, pkt)
        else:
            if rng[0]<=val<=rng[1]: return trf_match(ch, pkt)
    return "DENY"

def lrf_match(rules: list[Rule], pkt: dict) -> str:
    proto=pkt["protocol"]; src=pkt["src_ip"]; dst=pkt["dst_ip"]; port=pkt["dst_port"]
    for r in rules:
        if (proto in PROTO_SUPERS[r.protocol] and
            r.src_start<=src<=r.src_end and
            r.dst_start<=dst<=r.dst_end and
            r.port_start<=port<=r.port_end):
            return r.action
    return "DENY"


# ═══════════════════════════════════════════════════════════════════════════
# 9. TRF TEXT RENDERER
# ═══════════════════════════════════════════════════════════════════════════

def render_trf(node: TRFNode, indent: int = 0, proto_ctx: Optional[str] = None) -> str:
    """
    Pretty-print the TRF.
    proto_ctx tracks the protocol of the enclosing branch (when known),
    so that 'dst_port' nodes under an ICMP branch are labelled 'ICMP type'.
    """
    pad = "  " * indent
    if node.is_leaf:
        sym = "🟢" if node.action=="ALLOW" else "🔴"
        return f"{pad}{sym} -> {node.action}\n"

    # Decide the human-readable attribute label for this node.
    if node.attribute == "dst_port" and proto_ctx == "ICMP":
        attr_label = "icmp_type"
    else:
        attr_label = node.attribute

    lines = [f"{pad}[{attr_label}]\n"]
    for (rng, ch) in node.ranges:
        # Update protocol context as we descend.
        if node.attribute == "protocol":
            new_ctx = rng[0]
            label   = rng[0]
        elif node.attribute in ("src_ip","dst_ip"):
            new_ctx = proto_ctx
            label   = f"{int_to_ip(rng[0])}-{int_to_ip(rng[1])}"
        else:  # dst_port
            new_ctx = proto_ctx
            label   = f"{rng[0]}-{rng[1]}"
        lines.append(f"{pad}  ⚪ {label}\n")
        lines.append(render_trf(ch, indent+2, new_ctx))
    return "".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# 10. FULL CONVERSION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def convert_policy(rules_or_lines, policy_id: int = 0,
                   ordering_id: int = 4,
                   verbose: bool = False) -> tuple[TRFNode, ConversionReport, list[Rule]]:
    """
    Full 6-step pipeline (algorithm only, no ML).
    Memory: cells are garbage-collected after TRF construction.
    """
    t0 = time.perf_counter()
    if ordering_id not in ORDERING_OPTIONS:
        raise ValueError(
            f"Invalid ordering_id={ordering_id}. "
            f"Valid: 1–{N_ORDERINGS}."
        )
    ordering = ORDERING_OPTIONS[ordering_id]
    validate_ordering(ordering)   # safety check

    if isinstance(rules_or_lines, list) and rules_or_lines and isinstance(rules_or_lines[0], str):
        rules = parse_policy(rules_or_lines)
    else:
        rules = rules_or_lines

    n_in = len(rules)
    cat  = _size_category(n_in)
    if verbose:
        print(f"  [P{policy_id}] n={n_in} ({cat}) ordering={ordering_id}", flush=True)

    # ── ICMP usage statistics (computed before triad cleanup) ─────────────
    n_icmp = sum(1 for r in rules if "ICMP" in PROTO_SUPERS[r.protocol])
    n_icmp_pure = sum(1 for r in rules if r.protocol == "ICMP")
    icmp_pure_rules = [r for r in rules if r.protocol == "ICMP"]
    if icmp_pure_rules:
        icmp_type_min = min(r.port_start for r in icmp_pure_rules)
        icmp_type_max = max(r.port_end   for r in icmp_pure_rules)
    else:
        icmp_type_min = icmp_type_max = -1

    clean, anomaly_rep = deterministic_triad(rules)

    cells_raw  = decompose_4d(clean)
    n_raw      = len(cells_raw)
    if verbose:
        print(f"  [P{policy_id}] cells_raw={n_raw}", flush=True)

    cells_norm = projection_normalization(cells_raw, ordering)
    n_norm     = len(cells_norm)
    del cells_raw; gc.collect()   # free memory early

    trf = build_trf(cells_norm, ordering)
    del cells_norm; gc.collect()

    d         = trf_depth(trf)
    n_int, nl = trf_node_count(trf)
    elapsed   = time.perf_counter() - t0

    report = ConversionReport(
        policy_id          = policy_id,
        n_rules_in         = n_in,
        n_anomalies_shadow = anomaly_rep["n_shadow"],
        n_anomalies_redund = anomaly_rep["n_redundant"],
        n_rules_clean      = len(clean),
        n_cells_raw        = n_raw,
        n_cells_normalized = n_norm,
        trf_depth          = d,
        n_leaves           = nl,
        n_nodes            = n_int,
        attribute_ordering = ordering_id,
        conversion_time_s  = elapsed,
        size_category      = cat,
        n_icmp_rules       = n_icmp,
        n_icmp_pure_rules  = n_icmp_pure,
        icmp_type_min      = icmp_type_min,
        icmp_type_max      = icmp_type_max,
    )
    return trf, report, clean


# ═══════════════════════════════════════════════════════════════════════════
# 11. SYNTHETIC POLICY GENERATOR (v12 size categories)
# ═══════════════════════════════════════════════════════════════════════════

def _sample_ip(rng: random.Random) -> str:
    c = rng.random()
    if c < 0.35:   return rng.choice(SINGLE_HOSTS)
    elif c < 0.70: return rng.choice(SUBNETS_24)
    elif c < 0.85: return rng.choice(SUBNETS_16)
    else:          return "ANY"

def _sample_port(rng: random.Random) -> str:
    """Sample a TCP/UDP/IP/ANY port string."""
    c = rng.random()
    if c < 0.50:   return str(rng.choice(COMMON_PORTS))
    elif c < 0.75: return str(rng.randint(1024,65535))
    elif c < 0.85:
        lo = rng.randint(1024,60000)
        hi = lo + rng.randint(100,5000)
        return f"{lo}-{min(hi,65535)}"
    else:          return "ANY"

# Common ICMP types (RFC 792 / 4884): echo-reply=0, dest-unreach=3,
# source-quench=4, redirect=5, echo=8, time-exceeded=11, param-prob=12,
# timestamp=13, timestamp-reply=14, info-req=15, info-reply=16, addr-mask=17,
# addr-mask-reply=18, traceroute=30.
COMMON_ICMP_TYPES = [0, 3, 5, 8, 11, 13, 14, 17, 30]

def _sample_icmp_type(rng: random.Random) -> str:
    """Sample an ICMP-type string (0–255)."""
    c = rng.random()
    if c < 0.55:   return str(rng.choice(COMMON_ICMP_TYPES))
    elif c < 0.80: return str(rng.randint(0, ICMP_TYPE_MAX))
    elif c < 0.92:
        lo = rng.randint(0, ICMP_TYPE_MAX-10)
        hi = lo + rng.randint(1, 10)
        return f"{lo}-{min(hi, ICMP_TYPE_MAX)}"
    else:          return "ANY"

def _sample_proto(rng: random.Random) -> str:
    return rng.choices(["TCP","UDP","ICMP","IP","ANY"], weights=[40,25,10,10,15])[0]


def _sample_port_for_proto(rng: random.Random, proto: str) -> str:
    """Choose a port/icmp-type sampler based on the rule's protocol."""
    if proto == "ICMP":
        return _sample_icmp_type(rng)
    return _sample_port(rng)


def generate_policy(args) -> dict:
    """
    Generate one synthetic LRF policy with controlled anomaly injection.
    v12: supports Small (1–25), Medium (26–100), Large (101–400).
    Top-level function for multiprocessing.Pool.
    """
    policy_id, n_rules_range, seed = args
    rng = random.Random(seed)
    n_rules = rng.randint(*n_rules_range)
    lines, injected = [], []

    for _ in range(n_rules):
        proto  = _sample_proto(rng)
        src    = _sample_ip(rng)
        dst    = _sample_ip(rng)
        port   = _sample_port_for_proto(rng, proto)
        action = rng.choices(["ALLOW","DENY"], weights=[55,45])[0]
        lines.append(f"{proto} {src} {dst} {port} {action}")

    # Anomaly injection: 0–5 per policy (same injection protocol as v7)
    n_inject = rng.randint(0, 5)
    for _ in range(n_inject):
        if not lines: break
        atype     = rng.choice(["shadow","redundant","correlation"])
        base_line = rng.choice(lines)
        parts     = base_line.split()
        if len(parts) != 5: continue
        bp, bs, bd, bport, bact = parts

        if atype == "shadow":
            opp = "DENY" if bact=="ALLOW" else "ALLOW"
            ns  = rng.choice(SINGLE_HOSTS) if bs=="ANY" else bs
            lines.insert(rng.randint(0,len(lines)), f"{bp} {ns} {bd} {bport} {opp}")
            injected.append({"type":"shadow"})
        elif atype == "redundant":
            ns = rng.choice(SINGLE_HOSTS) if bs!="ANY" else bs
            lines.insert(rng.randint(0,len(lines)), f"{bp} {ns} {bd} {bport} {bact}")
            injected.append({"type":"redundant"})
        elif atype == "correlation":
            opp = "DENY" if bact=="ALLOW" else "ALLOW"
            alt = rng.choice(SUBNETS_16) if bs in SUBNETS_24 else rng.choice(SUBNETS_24)
            lines.insert(rng.randint(0,len(lines)), f"{bp} {alt} {bd} {bport} {opp}")
            injected.append({"type":"correlation"})

    return {"policy_id": policy_id, "lines": lines, "injected_anomalies": injected,
            "n_rules": n_rules}


def _size_category_range(policy_id: int, n_total: int) -> tuple[int,int]:
    """
    v12 size categories:
      Small  : 1–25  rules  (first third of dataset)
      Medium : 26–100 rules  (second third)
      Large  : 101–400 rules (last third)
    """
    third = n_total // 3
    if policy_id < third:
        return SIZE_CATEGORIES["small"]    # (1, 25)
    elif policy_id < 2 * third:
        return SIZE_CATEGORIES["medium"]   # (26, 100)
    else:
        return SIZE_CATEGORIES["large"]    # (101, 400)


# ═══════════════════════════════════════════════════════════════════════════
# 12. DEMO
# ═══════════════════════════════════════════════════════════════════════════

DEMO_POLICY = """\
# Demo LRF policy — v12 (no ML, with ICMP type support)
TCP  10.0.0.0/24  192.168.1.0/24 443  ALLOW
IP   10.0.0.5     192.168.1.10   ANY  DENY
UDP  ANY           ANY            53   ALLOW
TCP  10.0.0.5     192.168.1.0/24 443  ALLOW
ICMP 10.0.0.0/24  ANY            8    ALLOW
ICMP ANY          ANY            0-15 ALLOW
ANY  ANY           ANY            ANY  DENY
"""

def run_interactive():
    print("=" * 65)
    print("  LRF-to-TRF Framework v12  (Algorithm Only, No ML)")
    print("  Size categories : Small 1–25 | Medium 26–100 | Large 101–400")
    print(f"  Orderings       : {N_ORDERINGS} (1–6 protocol-first, 7–12 protocol-elsewhere)")
    print("  ICMP semantics  : dst_port stores ICMP type ∈ [0, 255]")
    print("  Default dataset : 5,000 policies")
    print("=" * 65)
    print("\nDemo policy:")
    print(DEMO_POLICY)

    lines = [l for l in DEMO_POLICY.strip().splitlines()
             if l.strip() and not l.startswith("#")]
    rules = parse_policy(lines)
    print(f"[Step 1] Parsed {len(rules)} rules")

    clean, rep = deterministic_triad(rules)
    print(f"[Step 2] Triad: Shadow={rep['n_shadow']} Redundant={rep['n_redundant']}")
    print(f"         Clean rules: {len(clean)}")

    oid      = 4
    ordering = ORDERING_OPTIONS[oid]
    print(f"[Step 3] Ordering Option {oid}: {' → '.join(ordering)}")

    cells_raw = decompose_4d(clean)
    print(f"[Step 4] Cells (raw): {len(cells_raw)}")

    cells_norm = projection_normalization(cells_raw, ordering)
    print(f"[Step 5] Cells (normalized): {len(cells_norm)}")

    trf, report, _ = convert_policy(rules, ordering_id=oid)
    print(f"[Step 6] TRF: depth={report.trf_depth}  leaves={report.n_leaves}  "
          f"nodes={report.n_nodes}  time={report.conversion_time_s:.4f}s")

    print("\n── TRF Structure ──────────────────────────────────────────")
    print(render_trf(trf))

    rng = random.Random(42)
    ok = fail = 0
    clean_rules = parse_policy(lines)
    for _ in range(2000):
        pkt = {"protocol": rng.choice(PROTOCOLS),
               "src_ip":   rng.randint(0,2**32-1),
               "dst_ip":   rng.randint(0,2**32-1),
               "dst_port": rng.randint(0,65535)}
        if lrf_match(clean_rules, pkt) == trf_match(trf, pkt): ok+=1
        else: fail+=1

    print("── Semantic Verification ───────────────────────────────────")
    print(f"   2,000 random packets: {ok} OK  {fail} FAIL")
    print(f"   Fidelity: {100*ok/(ok+fail):.2f}%  {'✅ PASS' if fail==0 else '❌ FAIL'}")


# ═══════════════════════════════════════════════════════════════════════════
# 13. CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="LRF-to-TRF v12 (Algorithm Only — No ML)\n"
                    "Policy sizes: Small 1–25 | Medium 26–100 | Large 101–400\n"
                    "Orderings: 1–12 (protocol must precede dst_port)\n"
                    "Default scale: 5,000 policies")
    sub = parser.add_subparsers(dest="command")

    p_demo = sub.add_parser("demo", help="Run interactive demo")

    p_conv = sub.add_parser("convert", help="Convert single policy file")
    p_conv.add_argument("policy_file")
    p_conv.add_argument("--ordering", type=int, default=4, choices=range(1, N_ORDERINGS+1))
    p_conv.add_argument("--output-dir", default=".")
    p_conv.add_argument("--verbose", action="store_true")

    p_gen = sub.add_parser("generate", help="Generate synthetic dataset")
    p_gen.add_argument("--policies", type=int, default=10000)
    p_gen.add_argument("--workers",  type=int, default=max(1,cpu_count()-1))
    p_gen.add_argument("--seed",     type=int, default=2025)
    p_gen.add_argument("--output",   default="policies_v12.jsonl")

    p_batch = sub.add_parser("batch", help="Batch-convert policy directory")
    p_batch.add_argument("policy_dir")
    p_batch.add_argument("--ordering", type=int, default=4, choices=range(1, N_ORDERINGS+1))
    p_batch.add_argument("--output-dir", default="trf_output_v11")
    p_batch.add_argument("--workers", type=int, default=4)

    args = parser.parse_args()

    # ── DEMO ──
    if args.command=="demo" or args.command is None:
        run_interactive(); return

    # ── CONVERT ──
    if args.command=="convert":
        path = Path(args.policy_file)
        if not path.exists():
            print(f"Error: {path}"); sys.exit(1)
        lines = path.read_text().splitlines()
        trf, report, clean = convert_policy(lines, ordering_id=args.ordering,
                                             verbose=args.verbose)
        out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
        stem = path.stem
        (out/f"{stem}_trf.txt").write_text(render_trf(trf))
        def _node_dict(n):
            if n.is_leaf: return {"leaf":True,"action":n.action}
            return {"attr":n.attribute,
                    "children":[{"range":list(rng),"subtree":_node_dict(ch)}
                                 for rng,ch in n.ranges]}
        (out/f"{stem}_trf.json").write_text(json.dumps(_node_dict(trf),indent=2))
        import dataclasses
        (out/f"{stem}_report.json").write_text(json.dumps(dataclasses.asdict(report),indent=2))
        print(f"Converted {path.name}")
        print(f"  Shadow: {report.n_anomalies_shadow}  Redundant: {report.n_anomalies_redund}")
        print(f"  TRF depth={report.trf_depth}  leaves={report.n_leaves}")
        print(f"  Category: {report.size_category}  Time: {report.conversion_time_s:.4f}s")
        return

    # ── GENERATE ──
    if args.command=="generate":
        n=args.policies; seed=args.seed; workers=args.workers; outf=args.output
        print(f"Generating {n:,} policies | workers={workers} | seed={seed}")
        print(f"Small 1–25, Medium 26–100, Large 101–400")
        print(f"Output: {outf}")
        task_args = [(i, _size_category_range(i, n), seed+i) for i in range(n)]
        t0    = time.perf_counter()
        chunk = max(1, n//(workers*4))
        with open(outf,"w") as fh, Pool(processes=workers) as pool:
            for i, pol in enumerate(pool.imap(generate_policy, task_args, chunksize=chunk)):
                fh.write(json.dumps(pol)+"\n")
                if (i+1) % max(1,n//20)==0:
                    el = time.perf_counter()-t0
                    rate = (i+1)/el; eta=(n-i-1)/rate
                    print(f"  {i+1:>8,}/{n:,}  ({100*(i+1)/n:.0f}%)  "
                          f"{rate:.0f} pol/s  ETA {eta:.0f}s", flush=True)
        el = time.perf_counter()-t0
        mb = os.path.getsize(outf)/1e6
        print(f"\nDone: {n:,} policies in {el:.1f}s  ({mb:.1f} MB)")
        return

    # ── BATCH ──
    if args.command=="batch":
        in_dir  = Path(args.policy_dir)
        out_dir = Path(args.output_dir); out_dir.mkdir(parents=True,exist_ok=True)
        files   = sorted(in_dir.glob("*.txt"))
        if not files:
            print(f"No .txt in {in_dir}"); sys.exit(1)
        print(f"Batch: {len(files)} policies  ordering={args.ordering}")
        reports=[]
        for i, path in enumerate(files):
            lines = path.read_text().splitlines()
            trf, report, _ = convert_policy(lines, policy_id=i,
                                             ordering_id=args.ordering)
            (out_dir/f"{path.stem}_trf.txt").write_text(render_trf(trf))
            reports.append(asdict(report))
            if (i+1)%max(1,len(files)//10)==0:
                print(f"  {i+1}/{len(files)}", flush=True)
        (out_dir/"batch_reports.json").write_text(json.dumps(reports,indent=2))
        print(f"Done → {out_dir}/batch_reports.json")


if __name__=="__main__":
    main()
