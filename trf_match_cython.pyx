# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""
trf_match_cython.pyx
=====================
Compiled match function for the TRF data structure. This is a minimal
kernel that takes a flat representation of the TRF (arrays of node
metadata) and returns the matched action for a packet.

A compiled prototype that exercises the O(d) traversal independent of
Python interpreter overhead.

The kernel uses a flat array representation:
- node_attr[i]   : 0=protocol, 1=src_ip, 2=dst_ip, 3=dst_port, 4=leaf
- node_first_child[i] : index of first child in arrays below
- node_n_children[i]  : number of children
- edge_low[j], edge_high[j] : range of edge j
- edge_target[j]    : index of child node for edge j
- node_action[i]    : 0=DENY, 1=ALLOW (for leaves)

To build: python3 setup_cython.py build_ext --inplace
"""

import cython
from libc.stdint cimport uint32_t, int32_t

PROTO_TCP  = 0
PROTO_UDP  = 1
PROTO_ICMP = 2

ACTION_DENY  = 0
ACTION_ALLOW = 1


@cython.boundscheck(False)
@cython.wraparound(False)
def match_packet(int[::1]      node_attr,
                 int[::1]      node_first_edge,
                 int[::1]      node_n_edges,
                 int[::1]      node_action,
                 long long[::1] edge_low,
                 long long[::1] edge_high,
                 int[::1]      edge_target,
                 int           proto,
                 long long     src_ip,
                 long long     dst_ip,
                 int           dst_port):
    """Match a single packet through the flat TRF.

    Returns: 0 (DENY) or 1 (ALLOW)
    """
    cdef int idx = 0  # root
    cdef int attr
    cdef long long val
    cdef int first, n_edges, e, found
    cdef long long lo, hi

    # Bounded loop: TRF depth ≤ 7; we cap at 16 for safety
    for _ in range(16):
        attr = node_attr[idx]
        if attr == 4:  # leaf
            return node_action[idx]
        # Pick value for this attribute
        if attr == 0:
            val = proto
        elif attr == 1:
            val = src_ip
        elif attr == 2:
            val = dst_ip
        else:  # attr == 3 (dst_port)
            val = dst_port
        # Find matching edge
        first = node_first_edge[idx]
        n_edges = node_n_edges[idx]
        found = 0
        for e in range(n_edges):
            lo = edge_low[first + e]
            hi = edge_high[first + e]
            if lo <= val and val <= hi:
                idx = edge_target[first + e]
                found = 1
                break
        if not found:
            return 0  # implicit DENY

    return 0  # safety fallback


@cython.boundscheck(False)
@cython.wraparound(False)
def match_packets_batch(int[::1]       node_attr,
                        int[::1]       node_first_edge,
                        int[::1]       node_n_edges,
                        int[::1]       node_action,
                        long long[::1] edge_low,
                        long long[::1] edge_high,
                        int[::1]       edge_target,
                        int[::1]       proto_array,
                        long long[::1] src_array,
                        long long[::1] dst_array,
                        int[::1]       port_array,
                        int[::1]       result):
    """Match a batch of packets, write results into `result` array."""
    cdef Py_ssize_t i, n = proto_array.shape[0]
    cdef int idx, attr, first, n_edges, e, found
    cdef long long val, lo, hi

    for i in range(n):
        idx = 0
        for _ in range(16):
            attr = node_attr[idx]
            if attr == 4:
                result[i] = node_action[idx]
                break
            if attr == 0:
                val = proto_array[i]
            elif attr == 1:
                val = src_array[i]
            elif attr == 2:
                val = dst_array[i]
            else:
                val = port_array[i]
            first = node_first_edge[idx]
            n_edges = node_n_edges[idx]
            found = 0
            for e in range(n_edges):
                lo = edge_low[first + e]
                hi = edge_high[first + e]
                if lo <= val and val <= hi:
                    idx = edge_target[first + e]
                    found = 1
                    break
            if not found:
                result[i] = 0
                break
        else:
            result[i] = 0
