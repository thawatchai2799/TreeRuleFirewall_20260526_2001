# LRF-to-TRF Framework v12 — How To Use

**Paper:** *Automated, Formally Proven Conversion of Listed-Rule Firewalls to Tree-Rule Firewalls*  
**Author:** Thawatchai Chomsiri · Mahasarakham University, Thailand  
**Default dataset:** 10,000 policies · Benchmark sizes: n ∈ {50, 100, 200, 400}

---

## Repository Structure

```
v12_source/
├── lrf_trf_app_v12.py                      # Core library (import by all scripts)
├── notebook1_v12_generate_dataset.py       # Step 1 — Generate synthetic policies
├── notebook2_v12_convert_all.py            # Step 2 — Batch LRF→TRF conversion
├── notebook3_v12_run_benchmarks.py         # Step 3 — Run all benchmarks (orchestrator)
├── semantic_verify_v12.py                  # Benchmark 1 — Semantic fidelity
├── anomaly_benchmark_v12.py                # Benchmark 2 — Anomaly detection
├── scalability_benchmark_v12.py            # Benchmark 3 — Scalability & speedup
├── ordering_benchmark_v12.py               # Benchmark 4 — Ordering comparison
├── wilcoxon_test_v12.py                    # Statistical test (post-processing)
├── classbench_loader_v12.py                # Helper — Load ClassBench-ng files
├── fdd_baseline_v12.py                     # Baseline — FDD (Liu & Gouda 2009)
├── hicuts_baseline_v12.py                  # Baseline — HiCuts (Gupta & McKeown 2000)
├── classbench_comparative_benchmark_v12.py # Benchmark 5 — ClassBench head-to-head
├── trf_match_cython.pyx                    # Cython kernel source
├── setup_cython.py                         # Build script for Cython kernel
└── cython_benchmark_v12.py                 # Benchmark 6 — Cython speedup
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10+ | 3.12+ |
| RAM | 8 GB | 16 GB |
| Disk | 2 GB free | 5 GB free |
| CPU cores | 4 | 8+ |
| OS | Windows 10 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |

```bash
pip install scipy numpy Cython
```

---

## Quick Start (Full Pipeline)

> **Note.** The bundled datasets are stored gzip-compressed to keep the repository small.
> Decompress before running any benchmark: `gunzip -k policies_v12.jsonl.gz`
> (or regenerate from scratch with Step 1 below).

```bash
# Step 0: Compile Cython kernel (one-time, optional)
python setup_cython.py build_ext --inplace

# Step 1: Generate 10,000-policy dataset (~10 min)
python notebook1_v12_generate_dataset.py

# Step 2: Run all benchmarks — orchestrated (~10-15 hours total)
python notebook3_v12_run_benchmarks.py --dataset policies_v12.jsonl

# Step 3: Statistical test
python wilcoxon_test_v12.py \
    --input ordering_benchmark_v12_results.json \
    --output wilcoxon_results.json

# Step 4: ClassBench head-to-head (requires ClassBench-ng data)
python classbench_comparative_benchmark_v12.py

# Step 5: Cython speedup benchmark (requires Step 0)
python cython_benchmark_v12.py
```

> **Note:** `notebook2_v12_convert_all.py` is **not required** for reproducing
> paper results. Run it only if you want to inspect per-policy conversion reports
> (depth, node count, timing). See [Optional: Batch Conversion Inspection](#optional--batch-conversion-inspection) below.

---

## Step-by-Step Guide

---

### STEP 0 — Environment Setup (one-time)

```bash
# Install Python dependencies
pip install scipy numpy Cython

# Compile the Cython TRF match kernel
python setup_cython.py build_ext --inplace
# Output: trf_match_cython.cpython-3xx-*.so  (Linux/macOS)
#         trf_match_cython.pyd                (Windows)
```

> **Note:** The Cython kernel is optional. All benchmarks run in pure Python
> without it. The Cython kernel is only required for `cython_benchmark_v12.py`.

---

### STEP 1 — Generate the 10,000-Policy Synthetic Dataset

```bash
python notebook1_v12_generate_dataset.py \
    --policies 10000 \
    --workers  8 \
    --seed     2025 \
    --output   policies_v12.jsonl
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--policies` | 10000 | Number of policies to generate |
| `--workers` | 8 | Parallel worker processes |
| `--seed` | 2025 | Random seed (fixed for reproducibility) |
| `--output` | `policies_v12.jsonl` | Output file |

**Expected output:**

```
Generating 10,000 policies | workers=8 | seed=2025
[████████████████████] 10000/10000  ~10 min
Saved → policies_v12.jsonl  (≈ 550–600 MB)
```

**Verify:**

```python
# Quick check
with open('policies_v12.jsonl') as f:
    lines = f.readlines()
print(f"Policies generated: {len(lines)}")  # should be 10,000
```

**Size distribution:**

| Category | Rule count | Policies |
|----------|-----------|---------|
| Small | 1–25 | ~3,333 |
| Medium | 26–100 | ~3,334 |
| Large | 101–400 | ~3,333 |

---

### STEP 2 — Run All Benchmarks (Orchestrator)

```bash
# Full run — recommended (~13–14 hours, run overnight)
python notebook3_v12_run_benchmarks.py --dataset policies_v12.jsonl

# Quick test mode (reduced samples — for pipeline testing only)
python notebook3_v12_run_benchmarks.py --dataset policies_v12.jsonl --quick

# Skip ordering benchmark (saves ~3 hours)
python notebook3_v12_run_benchmarks.py --dataset policies_v12.jsonl --skip-ordering
```

**What notebook3 runs internally:**

| Sub-step | Script | Est. time | Output file |
|----------|--------|-----------|-------------|
| 1 | `semantic_verify_v12.py` | ~8 hours | `semantic_verify_v12_results.json` |
| 2 | `anomaly_benchmark_v12.py` | ~1 hour | `anomaly_benchmark_v12_results.json` |
| 3 | `scalability_benchmark_v12.py` | ~30 min | `scalability_v12_results.json` |
| 4 | `ordering_benchmark_v12.py` | ~3–4 hours | `ordering_benchmark_v12_results.json` |

**Total: ~13–14 hours** — recommended to run overnight.

---

### STEP 3 — Statistical Test

```bash
python wilcoxon_test_v12.py \
    --input  ordering_benchmark_v12_results.json \
    --output wilcoxon_results.json
```

Computes the Wilcoxon signed-rank test (paired) comparing:
- Protocol-first orderings (IDs 1–6) vs Protocol-elsewhere orderings (IDs 7–12)

**Output:** `wilcoxon_results.json`

---

### Advanced A — Semantic Fidelity (standalone, optional)

```bash
python semantic_verify_v12.py \
    --dataset  policies_v12.jsonl \
    --policies 10000 \
    --ordering 4
```

**Output:** `semantic_verify_v12_results.json`

**Expected result:** 0 failures across ~73 million packet evaluations.  
**95% upper-CI on FN rate:** ≤ 4.10×10⁻⁸ (Rule of Three: 3/N)

---

### Advanced B — Ordering Comparison Benchmark (standalone, optional)

```bash
python ordering_benchmark_v12.py \
    --sizes   50,100,200,400 \
    --trials  10 \
    --packets 500 \
    --output  ordering_benchmark_v12_results.json
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--sizes` | `50,100,200,400` | Rule-count sizes to test |
| `--trials` | 10 | Trials per (size, ordering) pair |
| `--packets` | 500 | Test packets per trial |

**What this measures:**  
12 attribute orderings × 4 sizes × 10 trials = 480 data points.  
Metrics: tree memory, internal nodes, match latency, conversion time, peak memory.

**Output:** `ordering_benchmark_v12_results.json`

---

### Advanced C — ClassBench-ng Head-to-Head (standalone, optional)

**Prerequisites:** ClassBench-ng rule files must be present.

```bash
# Clone NeuroCuts repository to get ClassBench-ng files
git clone https://github.com/neurocuts/neurocuts.git
# Files will be at: neurocuts/classbench/acl1_1k, fw1_1k, etc.
```

```bash
python classbench_comparative_benchmark_v12.py \
    --classbench-dir neurocuts/classbench \
    --sizes 50,100,200,400 \
    --packets 500
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--classbench-dir` | `neurocuts/classbench` | Path to ClassBench-ng files |
| `--sizes` | `50,100,200,400` | Rule-count samples per ruleset |
| `--packets` | 500 | Test packets per case |

**Rulesets used (8 total):**

| Category | Files |
|----------|-------|
| ACL | acl1_1k, acl2_1k, acl3_1k |
| Firewall | fw1_1k, fw2_1k, fw3_1k |
| IPC | ipc1_1k, ipc2_1k |

**Total test cases:** 8 rulesets × 4 sizes = **32 test cases**  
**Output:** `classbench_results.json`

---

### Advanced D — Cython Compiled Kernel Benchmark (standalone, optional)

```bash
# Must compile first (see STEP 0)
python cython_benchmark_v12.py
```

**Tests:** n ∈ {25, 50, 100, 200, 400} × 5 trials × 5,000 packets  
**Output:** `cython_results.json`

---

## Output Files Summary

| File | Produced by | Paper reference |
|------|-------------|-----------------|
| `policies_v12.jsonl` | notebook1 | Dataset for all benchmarks (shipped as `.gz`) |
| `conversion_reports_v12.jsonl` | notebook2 | Conversion metadata (shipped as `.gz`) |
| `semantic_verify_v12_results.json` | semantic_verify | Table 2 |
| `anomaly_benchmark_v12_results.json` | anomaly_benchmark | Figure 10 |
| `scalability_v12_results.json` | scalability_benchmark | Table 7, Figures 11-12 |
| `ordering_benchmark_v12_results.json` | ordering_benchmark | Table 3 |
| `wilcoxon_results.json` | wilcoxon_test | Section 6.5 |
| `classbench_results.json` | classbench_comparative | Table 4, Figures 14-15 |
| `cython_results.json` | cython_benchmark | Table 5 |

---

## Estimated Runtimes

Hardware reference: **Intel Core i7-12700, 16 GB RAM, Windows 11 / Ubuntu 22.04**

| Script | 10,000 policies | Notes |
|--------|-----------------|-------|
| notebook1 | ~10 min | Parallelized |
| notebook2 | ~45 min | Sequential per policy |
| semantic_verify | **~8 hours** | 73M+ evaluations |
| anomaly_benchmark | ~1 hour | 14 configs × 500 trials |
| scalability_benchmark | ~30 min | n ∈ {5..400} |
| ordering_benchmark | ~3–4 hours | 12 orderings × 4 sizes |
| classbench | ~2–3 hours | 8 rulesets × 4 sizes |
| cython_benchmark | ~30 min | Requires Cython build |
| **Total** | **~16–18 hours** | Run overnight |

---

## Troubleshooting

**Q: `ImportError: No module named lrf_trf_app_v12`**  
A: Make sure all scripts are in the same directory. Run from inside `v12_source/`.

**Q: `ModuleNotFoundError: No module named 'trf_match_cython'`**  
A: Compile the Cython kernel first:
```bash
python setup_cython.py build_ext --inplace
```

**Q: ClassBench directory not found**  
A: Set the environment variable:
```bash
export V12_CLASSBENCH_DIR=/path/to/neurocuts/classbench   # Linux/macOS
set V12_CLASSBENCH_DIR=C:\path\to\neurocuts\classbench    # Windows
```

**Q: `MemoryError` during semantic verify**  
A: Reduce the policy batch size:
```bash
python semantic_verify_v12.py --policies 5000
```

**Q: Ordering benchmark is too slow**  
A: Use `--quick` mode or reduce sizes:
```bash
python ordering_benchmark_v12.py --sizes 50,100,200 --trials 5
```

---

## Reproducibility

All experiments use fixed random seeds:
- Policy generation: `--seed 2025`
- ClassBench sampling: `seed=42` (hardcoded)
- Packet generation per trial: `BASE_SEED + trial_idx`

To fully reproduce paper results:
```bash
python notebook1_v12_generate_dataset.py --seed 2025 --policies 10000
python notebook3_v12_run_benchmarks.py --dataset policies_v12.jsonl
python wilcoxon_test_v12.py --input ordering_benchmark_v12_results.json
python classbench_comparative_benchmark_v12.py --sizes 50,100,200,400
python cython_benchmark_v12.py
```

> **Note:** `notebook2_v12_convert_all.py` is **not included** above because
> no benchmark reads its output (`conversion_reports_v12.jsonl`). Each benchmark
> performs its own LRF→TRF conversion internally. Run notebook2 only if you
> need per-policy conversion metadata for debugging or analysis.

---


---

## Optional: Batch Conversion Inspection

`notebook2_v12_convert_all.py` pre-converts all 10,000 policies and saves
per-policy metadata to `conversion_reports_v12.jsonl`. This is **not required**
for any benchmark but is useful for:

- Inspecting conversion depth, node count, and timing per policy
- Finding outlier policies (unusually slow conversion or high depth)
- Debugging conversion errors on specific policies

```bash
python notebook2_v12_convert_all.py \
    --dataset  policies_v12.jsonl \
    --ordering 4 \
    --output   conversion_reports_v12.jsonl
```

**Output:** `conversion_reports_v12.jsonl` (~3–4 MB)

```python
# Example: inspect conversion reports
import json
with open('conversion_reports_v12.jsonl') as f:
    reports = [json.loads(line) for line in f]

# Find policies with depth > 4
deep = [r for r in reports if r.get('depth', 0) > 4]
print(f"Policies with depth > 4: {len(deep)}")

# Find slowest conversions
slow = sorted(reports, key=lambda r: r.get('conv_ms', 0), reverse=True)[:5]
for r in slow:
    print(f"  policy_id={r['policy_id']}  "
          f"n_rules={r['n_rules']}  conv_ms={r['conv_ms']:.1f}")
```

## Citation

```bibtex
@software{chomsiri_lrf2trf_framework,
  title   = {LRF-to-TRF Framework: Source Code, Datasets, and
             Benchmark Results},
  author  = {Chomsiri, Thawatchai},
  year    = {2026},
  doi     = {10.5281/zenodo.20396163},
  url     = {https://doi.org/10.5281/zenodo.20396163}
}
```

---

## Contact

Thawatchai Chomsiri  
Department of Information Technology, Faculty of Informatics  
Mahasarakham University, Maha Sarakham 44150, Thailand  
thawatchai.c@msu.ac.th
