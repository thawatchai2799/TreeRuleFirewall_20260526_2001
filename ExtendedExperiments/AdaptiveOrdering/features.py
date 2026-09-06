"""Policy-shape features for predicting the best attribute ordering."""
import re, ipaddress, math
from collections import Counter

def parse_rule(line):
    p = line.split()
    if len(p) < 5: return None
    proto, src, dst, port, act = p[0], p[1], p[2], p[3], p[4]
    def ip_range(s):
        if s in ('ANY','any','*'): return 0, 2**32-1
        if '/' in s:
            n = ipaddress.ip_network(s, strict=False)
            return int(n.network_address), int(n.broadcast_address)
        a = int(ipaddress.ip_address(s)); return a, a
    def port_range(s, proto):
        hi = 255 if proto == 'ICMP' else 65535
        if s in ('ANY','any','*'): return 0, hi
        if '-' in s:
            a,b = s.split('-'); return int(a), int(b)
        a = int(s); return a, a
    return dict(proto=proto, src=ip_range(src), dst=ip_range(dst),
                port=port_range(port, proto), act=act)

def features(lines):
    R = [r for r in (parse_rule(l) for l in lines) if r]
    n = len(R)
    if n == 0: return None
    # cut-points per axis = distinct endpoints (what drives cell count)
    cuts = {}
    for axis in ('src','dst','port'):
        pts = set()
        for r in R:
            pts.add(r[axis][0]); pts.add(r[axis][1] + 1)
        cuts[axis] = len(pts)
    protos = Counter(r['proto'] for r in R)
    n_atomic = len(set(protos) - {'IP','ANY'})
    superset_frac = sum(protos[p] for p in ('IP','ANY')) / n
    # the key ratio: how much finer the global cut set is than per-protocol sets
    per_proto_cuts = 0
    for p in set(protos):
        sub = [r for r in R if r['proto'] == p]
        pts = set()
        for r in sub:
            pts.add(r['port'][0]); pts.add(r['port'][1] + 1)
        per_proto_cuts += len(pts)
    global_port_cuts = cuts['port']
    return dict(
        n_rules            = n,
        cuts_src           = cuts['src'],
        cuts_dst           = cuts['dst'],
        cuts_port          = cuts['port'],
        cut_ratio_src_port = cuts['src'] / max(cuts['port'], 1),
        cut_ratio_dst_port = cuts['dst'] / max(cuts['port'], 1),
        proto_entropy      = -sum((c/n)*math.log2(c/n) for c in protos.values()),
        n_atomic_protocols = n_atomic,
        superset_frac      = superset_frac,
        icmp_frac          = protos.get('ICMP', 0) / n,
        # predicted saving from protocol-first: global cuts vs summed per-protocol cuts
        proto_split_gain   = global_port_cuts / max(per_proto_cuts / max(len(protos),1), 1),
        any_port_frac      = sum(1 for r in R if r['port'] == (0, 65535) or r['port'] == (0, 255)) / n,
        mean_src_span      = sum(r['src'][1]-r['src'][0]+1 for r in R) / n / 2**32,
        mean_dst_span      = sum(r['dst'][1]-r['dst'][0]+1 for r in R) / n / 2**32,
        deny_frac          = sum(1 for r in R if r['act'] == 'DENY') / n,
    )
