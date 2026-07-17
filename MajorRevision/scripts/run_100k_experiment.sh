# =============================================================================
# LRF-to-TRF Framework v12 -- 100,000-Policy Experiment (Reproducibility Script)
# Target machine used in this run: Intel(R) Core(TM) 5 210H @ 2.20 GHz (8C/12T),
# 32 GB RAM, Windows 11.
#
# Prerequisites:
#   - Python 3.10+ on PATH
#   - All project .py files in the SAME folder as this script:
#       lrf_trf_app_v12.py
#       notebook1_v12_generate_dataset.py
#       notebook2_v12_convert_all.py
#       notebook3_v12_run_benchmarks.py
#       semantic_verify_v12.py
#       anomaly_benchmark_v12.py
#       scalability_benchmark_v12.py
#       ordering_benchmark_v12.py
#   - No third-party packages required (standard library only)
#
# Notes on runtime:
#   - Step 1 (generate) and Step 2 (convert) are fast / multiprocessing-enabled.
#   - Step 3a (semantic_verify_v12.py) is SINGLE-THREADED by design -- its
#     runtime scales with --policies (sample size), not with CPU core count.
#     We sample 10,000 of the 100,000 policies (10%) to keep total runtime in
#     the same ballpark as the original 10,000-policy run reported in the
#     paper (order of several hours). Increase --policies below for a larger
#     sample; runtime scales roughly linearly with that number.
#   - Run Steps 3a/3b unattended (e.g. overnight); there is no auto-resume if
#     interrupted, so avoid closing the terminal / letting the machine sleep.
# =============================================================================

# -----------------------------------------------------------------------------
# Step 0 (optional but recommended): quick environment sanity check
# -----------------------------------------------------------------------------
python --version
python -c "import sys; print('OK, running:', sys.executable)"

# -----------------------------------------------------------------------------
# Step 1: Generate 100,000 synthetic LRF policies
#   --seed 2025 is the same base seed used for the original 10,000-policy
#   dataset in the paper, so the first 10,000 policies generated here are
#   expected to reproduce that original dataset (deterministic RNG).
#   Expected runtime: ~1-3 minutes.
# -----------------------------------------------------------------------------
python notebook1_v12_generate_dataset.py --policies 100000 --workers 8 --seed 2025 --output policies_v12_100k.jsonl

# -----------------------------------------------------------------------------
# Step 2: Convert ALL 100,000 policies from LRF to TRF
#   Uses multiprocessing internally (Pool); the worker count for Large
#   policies (101-400 rules) is auto-scaled down to limit peak RAM use.
#   This step must complete before Step 3b (notebook3), which depends on
#   the conversion report it produces.
#   Expected runtime: on the order of a few hours (parallelized).
# -----------------------------------------------------------------------------
python notebook2_v12_convert_all.py --dataset policies_v12_100k.jsonl

# -----------------------------------------------------------------------------
# Step 3a: Semantic fidelity verification (empirical check of Theorem 1)
#   Samples 10,000 of the 100,000 policies (fixed --seed for reproducibility)
#   and compares phi_LRF vs phi_TRF packet-by-packet.
#   Expected runtime: several hours (single-threaded; dominated by Large
#   policies, which are individually expensive due to O(N^2) Projection
#   Normalization). Run this as its own unattended session.
# -----------------------------------------------------------------------------
python semantic_verify_v12.py --dataset policies_v12_100k.jsonl --policies 10000 --random-packets 500 --seed 42 --output semantic_verify_100k_results.json

# -----------------------------------------------------------------------------
# Step 3b: Anomaly detection, scalability, and ordering-comparison benchmarks
#   Runs against the full 100,000-policy dataset via notebook3, which
#   internally calls anomaly_benchmark_v12.py, scalability_benchmark_v12.py,
#   and ordering_benchmark_v12.py in sequence.
#   Trial counts below match (or exceed) the settings used elsewhere in the
#   paper; adjust if you want a faster/slower run.
# -----------------------------------------------------------------------------
python notebook3_v12_run_benchmarks.py --dataset policies_v12_100k.jsonl --anom-trials 500 --scale-trials 10 --ord-trials 10 --ordering 4

# Optional: fast end-to-end sanity check BEFORE committing to the full Step 3b
# run above (recommended to run this first, on a fresh machine/environment):
#   python notebook3_v12_run_benchmarks.py --dataset policies_v12_100k.jsonl --quick

# -----------------------------------------------------------------------------
# Output files produced by this script (collect these for reporting):
#   policies_v12_100k.jsonl              -- the generated 100,000-policy dataset
#   semantic_verify_100k_results.json    -- Step 3a results (Theorem 1 check)
#   (notebook3 output filename(s) -- check console output / working directory
#    after Step 3b completes; these hold the anomaly/scalability/ordering
#    benchmark results)
# =============================================================================
