#!/usr/bin/env python3
"""
E1 runner - per-policy ordering ground truth (resumable, with live progress).

For every policy in the input dataset, this script converts the policy under each
of the twelve admissible attribute orderings and records the structural and timing
cost of each resulting tree, together with the policy-shape feature vector.

Output is one JSON object per policy per ordering, written as JSON Lines so that a
run is resumable: completed (policy_id, ordering_id) pairs are skipped on restart.

A background reporter prints progress every few seconds, showing percent complete
and estimated time remaining. The estimate is weighted by policy size, because
conversion cost grows roughly with the square of the rule count; a plain
count-based estimate would be badly wrong whenever policy sizes are mixed.

Usage (Windows PowerShell or cmd):

    python e1_runner.py --policies data\\policies.jsonl.gz --out results\\e1.jsonl
    python e1_runner.py --policies data\\policies.jsonl.gz --out results\\e1.jsonl --limit 50
    python e1_runner.py --policies data\\policies.jsonl.gz --out results\\e1.jsonl --sizes 50,100,200,400 --per-size 200
    python e1_runner.py --policies data\\policies.jsonl.gz --out results\\e1.jsonl --report-every 10

Press Ctrl+C at any time. The record in progress is finished, the file is flushed,
and the process exits. Rerun the identical command to continue.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import platform
import random
import signal
import statistics
import sys
import threading
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import lrf_trf_app_v12 as app
except ImportError:
    sys.stderr.write(
        "ERROR: cannot import lrf_trf_app_v12.\n"
        "Place lrf_trf_app_v12.py next to this script, or add its folder to PYTHONPATH.\n"
    )
    raise

from features import features as extract_features

ALL_ORDERINGS = list(range(1, 13))
SCHEMA_VERSION = 1

# Conversion cost grows with rule count, but far more slowly than quadratically
# once policies are past the smallest sizes: measured data show a policy at 400
# rules costing roughly 2.9 times one at 50 rules, which an exponent near 0.5
# reproduces closely. Work units use this exponent so that percent-complete and
# time-remaining stay accurate when policy sizes are mixed.
#
# If your own pilot runs show a different growth rate, override it with
# --work-exponent. A value of 0 weights every record equally.
DEFAULT_WORK_EXPONENT = 0.5

_stop_requested = False


def _handle_sigint(signum, frame):
    global _stop_requested
    if _stop_requested:
        return
    _stop_requested = True
    sys.stderr.write(
        "\nStop requested. Finishing the record in progress, then exiting.\n"
    )


# --------------------------------------------------------------------------
# Progress tracking
# --------------------------------------------------------------------------

class Progress:
    """
    Shared progress state, written by the worker and read by the reporter thread.

    All mutation happens under a lock, and the reporter takes a consistent
    snapshot, so the two threads never observe a partial update.
    """

    def __init__(self, total_units: float, total_records: int,
                 already_present: int):
        self._lock = threading.Lock()
        self.total_units = max(total_units, 1e-9)
        self.done_units = 0.0
        self.total_records = total_records
        self.done_records = 0
        self.already_present = already_present
        self.failed_records = 0
        self.current_policy = None
        self.current_size = None
        self.current_ordering = None
        self.started = time.perf_counter()

    def record_done(self, units: float) -> None:
        with self._lock:
            self.done_units += units
            self.done_records += 1

    def record_failed(self, units: float) -> None:
        with self._lock:
            self.done_units += units
            self.failed_records += 1

    def set_current(self, policy_id, size, ordering_id) -> None:
        with self._lock:
            self.current_policy = policy_id
            self.current_size = size
            self.current_ordering = ordering_id

    def snapshot(self) -> dict:
        with self._lock:
            elapsed = time.perf_counter() - self.started
            frac = min(self.done_units / self.total_units, 1.0)
            eta_s = float("nan")
            if self.done_units > 0 and elapsed > 0:
                rate = self.done_units / elapsed
                if rate > 0:
                    eta_s = max(self.total_units - self.done_units, 0.0) / rate
            return {
                "percent": frac * 100.0,
                "elapsed_s": elapsed,
                "eta_s": eta_s,
                "done_records": self.done_records,
                "total_records": self.total_records,
                "already_present": self.already_present,
                "failed": self.failed_records,
                "policy": self.current_policy,
                "size": self.current_size,
                "ordering": self.current_ordering,
            }


def _is_nan(x: float) -> bool:
    return x != x


def _fmt_duration(seconds: float) -> str:
    """Render a duration as hours and minutes, or smaller units when short."""
    if _is_nan(seconds) or seconds == float("inf"):
        return "estimating"
    seconds = max(seconds, 0.0)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def reporter_loop(progress: Progress, interval: float,
                  stop_event: threading.Event) -> None:
    """Print a status line every interval seconds until asked to stop."""
    while not stop_event.wait(interval):
        s = progress.snapshot()
        if _is_nan(s["eta_s"]):
            eta_txt = "estimating"
        else:
            eta_txt = f"{s['eta_s'] / 3600.0:.2f} h ({_fmt_duration(s['eta_s'])})"
        where = ""
        if s["policy"] is not None:
            where = (f" | policy {s['policy']} (n={s['size']}) "
                     f"ordering {s['ordering']}")
        line = (f"[{_fmt_duration(s['elapsed_s'])}] "
                f"{s['percent']:5.1f}% | "
                f"{s['done_records']}/{s['total_records']} records | "
                f"remaining {eta_txt}{where}")
        if s["failed"]:
            line += f" | failed {s['failed']}"
        print(line, flush=True)


# --------------------------------------------------------------------------
# Dataset loading
# --------------------------------------------------------------------------

def open_maybe_gzip(path: Path):
    if str(path).lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def load_policies(path: Path, sizes, per_size: int, limit, seed: int):
    """
    Read policies and select the sample to process.

    With --sizes, policies are bucketed by rule count and up to per_size are drawn
    from each bucket using a seeded shuffle, so selection is reproducible and does
    not depend on file order.
    """
    pool = []
    with open_maybe_gzip(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "lines" not in rec or "policy_id" not in rec:
                continue
            pool.append(rec)
            if limit is not None and sizes is None and len(pool) >= limit:
                break

    if sizes is None:
        return pool[:limit] if limit is not None else pool

    buckets = {s: [] for s in sizes}
    for rec in pool:
        n = int(rec.get("n_rules", len(rec["lines"])))
        for s in sizes:
            if abs(n - s) <= max(2, int(0.10 * s)):
                buckets[s].append(rec)
                break

    rng = random.Random(seed)
    selected = []
    for s in sizes:
        b = buckets[s]
        rng.shuffle(b)
        take = b[:per_size]
        if len(take) < per_size:
            sys.stderr.write(
                f"WARNING: size {s} matched only {len(take)} policies "
                f"(requested {per_size}).\n"
            )
        selected.extend(take)
    return selected


# --------------------------------------------------------------------------
# Resume support
# --------------------------------------------------------------------------

def load_done(out_path: Path) -> set:
    """Return the set of (policy_id, ordering_id) pairs already recorded."""
    done = set()
    if not out_path.exists():
        return done
    bad = 0
    with open(out_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add((int(rec["policy_id"]), int(rec["ordering_id"])))
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                bad += 1
    if bad:
        sys.stderr.write(
            f"WARNING: {bad} unreadable line(s) in {out_path} were ignored. "
            "Those records will be recomputed and appended.\n"
        )
    return done


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------

def sample_packets(rng: random.Random, count: int):
    """Draw uniform random packets across the protocol-appropriate domains."""
    pkts = []
    for _ in range(count):
        proto = rng.choice(["TCP", "UDP", "ICMP"])
        hi = 255 if proto == "ICMP" else 65535
        pkts.append({
            "protocol": proto,
            "src_ip": rng.randint(0, 2 ** 32 - 1),
            "dst_ip": rng.randint(0, 2 ** 32 - 1),
            "dst_port": rng.randint(0, hi),
        })
    return pkts


def measure_one(lines, policy_id: int, ordering_id: int, do_timing: bool,
                packets, timing_trials: int) -> dict:
    """Convert one policy under one ordering and return its cost record."""
    tracemalloc.start()
    try:
        t0 = time.perf_counter()
        trf, report, _rules = app.convert_policy(
            lines, policy_id=policy_id, ordering_id=ordering_id
        )
        conv_s = time.perf_counter() - t0
        _cur, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    rec = {
        "schema": SCHEMA_VERSION,
        "policy_id": int(policy_id),
        "ordering_id": int(ordering_id),
        "n_rules_in": int(report.n_rules_in),
        "n_rules_clean": int(report.n_rules_clean),
        "trf_depth": int(report.trf_depth),
        "n_nodes": int(report.n_nodes),
        "n_leaves": int(report.n_leaves),
        "n_cells_raw": int(report.n_cells_raw),
        "n_cells_normalized": int(report.n_cells_normalized),
        "tree_bytes": int(app.trf_size_bytes(trf)),
        "peak_bytes": int(peak),
        "conv_s": float(conv_s),
        "match_us_mean": None,
        "match_us_std": None,
        "timing_trials": 0,
    }

    if do_timing and packets:
        per_trial = []
        for _ in range(timing_trials):
            t1 = time.perf_counter()
            for pkt in packets:
                app.trf_match(trf, pkt)
            per_trial.append((time.perf_counter() - t1) / len(packets) * 1e6)
        rec["match_us_mean"] = float(statistics.mean(per_trial))
        rec["match_us_std"] = (
            float(statistics.pstdev(per_trial)) if len(per_trial) > 1 else 0.0
        )
        rec["timing_trials"] = int(timing_trials)

    return rec


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def parse_ordering_spec(spec: str):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="E1: per-policy ordering ground truth (resumable, live progress)."
    )
    ap.add_argument("--policies", required=True,
                    help="Input dataset, .jsonl or .jsonl.gz")
    ap.add_argument("--out", required=True,
                    help="Output JSON Lines file (appended on resume)")
    ap.add_argument("--sizes", default=None,
                    help="Target rule counts, e.g. 50,100,200,400")
    ap.add_argument("--per-size", type=int, default=500,
                    help="Policies to draw from each size bucket")
    ap.add_argument("--limit", type=int, default=None,
                    help="Cap on the total number of policies")
    ap.add_argument("--orderings", default="1-12",
                    help="Orderings to run, e.g. 1-12 or 1,4,7")
    ap.add_argument("--timing-every", type=int, default=1,
                    help="Measure match latency on every Nth policy (1 = all)")
    ap.add_argument("--timing-packets", type=int, default=2000,
                    help="Packets per timing trial")
    ap.add_argument("--timing-trials", type=int, default=3,
                    help="Timing trials per record")
    ap.add_argument("--seed", type=int, default=7331,
                    help="Seed for policy selection and packet sampling")
    ap.add_argument("--report-every", type=float, default=10.0,
                    help="Seconds between progress lines (default 10; 0 disables)")
    ap.add_argument("--work-exponent", type=float, default=DEFAULT_WORK_EXPONENT,
                    help=f"Growth exponent used to weight the time estimate by policy "
                         f"size (default {DEFAULT_WORK_EXPONENT}). Set 0 to weight every "
                         f"record equally.")
    args = ap.parse_args()

    if args.per_size < 1:
        sys.stderr.write("ERROR: --per-size must be at least 1.\n")
        return 2
    if args.timing_every < 1:
        sys.stderr.write("ERROR: --timing-every must be at least 1.\n")
        return 2
    if args.timing_trials < 1:
        sys.stderr.write("ERROR: --timing-trials must be at least 1.\n")
        return 2
    if args.timing_packets < 1:
        sys.stderr.write("ERROR: --timing-packets must be at least 1.\n")
        return 2
    if args.work_exponent < 0:
        sys.stderr.write("ERROR: --work-exponent must not be negative.\n")
        return 2

    policies_path = Path(args.policies)
    out_path = Path(args.out)
    if not policies_path.exists():
        sys.stderr.write(f"ERROR: input not found: {policies_path}\n")
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)

    orderings = parse_ordering_spec(args.orderings)
    invalid = [o for o in orderings if o not in ALL_ORDERINGS]
    if invalid:
        sys.stderr.write(
            f"ERROR: invalid ordering id(s): {invalid}. Valid range is 1-12.\n")
        return 2
    if not orderings:
        sys.stderr.write("ERROR: no orderings selected.\n")
        return 2

    sizes = None
    if args.sizes:
        try:
            sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
        except ValueError:
            sys.stderr.write(
                "ERROR: --sizes must be a comma-separated list of integers.\n")
            return 2

    print("Loading policies ...", flush=True)
    policies = load_policies(policies_path, sizes, args.per_size,
                             args.limit, args.seed)
    if args.limit is not None and sizes is not None:
        policies = policies[:args.limit]
    if not policies:
        sys.stderr.write("ERROR: no policies selected. Check --sizes and --per-size.\n")
        return 2

    done = load_done(out_path)

    # ---- build the work list, weighted by expected cost --------------------
    work = []
    already_present = 0
    for pol in policies:
        pid = int(pol["policy_id"])
        n = int(pol.get("n_rules", len(pol["lines"])))
        units = max(float(n), 1.0) ** args.work_exponent
        for oid in orderings:
            if (pid, oid) in done:
                already_present += 1
                continue
            work.append((pol, oid, units))

    total_records = len(work)
    total_units = sum(w[2] for w in work)

    print(f"Selected {len(policies)} policies x {len(orderings)} orderings.")
    if already_present:
        print(f"Resuming: {already_present} records already present, "
              f"{total_records} remaining.")
    else:
        print(f"To compute: {total_records} records.")
    if total_records == 0:
        print("Nothing to do. All requested records are already present.")
        return 0

    # ---- metadata (one entry per session, appended) ------------------------
    meta_path = out_path.with_suffix(out_path.suffix + ".meta.json")
    session = {
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": args.seed,
        "orderings": orderings,
        "sizes": sizes,
        "per_size": args.per_size,
        "limit": args.limit,
        "timing_every": args.timing_every,
        "timing_packets": args.timing_packets,
        "timing_trials": args.timing_trials,
        "work_exponent": args.work_exponent,
        "records_planned": total_records,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "input": str(policies_path),
    }
    sessions = []
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                prev = json.load(fh)
            if isinstance(prev, dict):
                sessions = prev.get("sessions", [])
        except (json.JSONDecodeError, OSError):
            sessions = []
    sessions.append(session)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"schema": SCHEMA_VERSION, "sessions": sessions}, fh, indent=2)

    # ---- run ---------------------------------------------------------------
    signal.signal(signal.SIGINT, _handle_sigint)

    rng = random.Random(args.seed)
    packets = sample_packets(rng, args.timing_packets)

    progress = Progress(total_units, total_records, already_present)
    stop_event = threading.Event()
    reporter = None
    if args.report_every > 0:
        reporter = threading.Thread(
            target=reporter_loop,
            args=(progress, args.report_every, stop_event),
            daemon=True,
        )
        reporter.start()

    # Feature vectors are per policy; cache to avoid recomputing per ordering.
    feature_cache = {}
    # Timing subsampling is decided per policy using its position in the
    # selected list, so the same policies are timed on every resume.
    policy_position = {int(p["policy_id"]): i for i, p in enumerate(policies)}

    written = 0
    t_start = time.perf_counter()

    try:
        with open(out_path, "a", encoding="utf-8") as out_fh:
            for pol, oid, units in work:
                if _stop_requested:
                    break

                pid = int(pol["policy_id"])
                n = int(pol.get("n_rules", len(pol["lines"])))
                progress.set_current(pid, n, oid)

                if pid not in feature_cache:
                    try:
                        feature_cache[pid] = extract_features(pol["lines"])
                    except Exception as exc:  # noqa: BLE001
                        sys.stderr.write(
                            f"WARNING: feature extraction failed for policy {pid}: {exc}\n"
                        )
                        feature_cache[pid] = None

                do_timing = (policy_position.get(pid, 0) % args.timing_every == 0)

                try:
                    rec = measure_one(pol["lines"], pid, oid, do_timing,
                                      packets, args.timing_trials)
                except Exception as exc:  # noqa: BLE001
                    progress.record_failed(units)
                    sys.stderr.write(f"ERROR: policy {pid} ordering {oid}: {exc}\n")
                    continue

                if feature_cache[pid] is not None:
                    rec["features"] = feature_cache[pid]

                out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out_fh.flush()
                os.fsync(out_fh.fileno())
                written += 1
                progress.record_done(units)
    finally:
        stop_event.set()
        if reporter is not None:
            reporter.join(timeout=2.0)

    total = time.perf_counter() - t_start
    snap = progress.snapshot()
    print(f"\nDone. Written {written}, failed {snap['failed']}, "
          f"already present {already_present}, in {_fmt_duration(total)}.")
    print(f"Output:   {out_path}")
    print(f"Metadata: {meta_path}")
    if _stop_requested:
        print("Run was interrupted. Rerun the identical command to continue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
