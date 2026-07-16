# =============================================================================
# LRF-to-TRF Framework v12 -- 50,000-Policy Experiment Pipeline
# Run these on the Intel i7 machine, in order, inside the project folder
# (the one containing notebook1/2/3_v12_*.py, lrf_trf_app_v12.py, etc.)
# =============================================================================

# -----------------------------------------------------------------------------
# 1. Generate 50,000 synthetic LRF policies (fast, ~1-2 minutes)
#    --seed 2025 matches the seed used for the original 10,000-policy dataset,
#    so the first 10,000 policies here should reproduce that original dataset.
# -----------------------------------------------------------------------------
python notebook1_v12_generate_dataset.py --policies 50000 --workers 8 --seed 2025 --output policies_v12_50k.jsonl

# -----------------------------------------------------------------------------
# 2. Convert ALL 50,000 policies LRF -> TRF
#    Uses multiprocessing internally; worker count is auto-scaled down for
#    Large policies (101-400 rules) to avoid RAM pressure. This step is
#    required before Step 3b (anomaly/scalability/ordering benchmarks),
#    which read from the conversion report, not from Step 3a.
# -----------------------------------------------------------------------------
python notebook2_v12_convert_all.py --dataset policies_v12_50k.jsonl

# -----------------------------------------------------------------------------
# 3a. Verify Step 1 -- semantic fidelity (Theorem 1 empirical check)
#     We sample 10,000 of the 50,000 policies (not all of them) to keep the
#     runtime comparable to the original 10,000-policy run (~8-11 hours on
#     an i5/i7). Increase --policies later if you want a larger sample --
#     you do not need to regenerate or reconvert the dataset to do that.
# -----------------------------------------------------------------------------
python semantic_verify_v12.py --dataset policies_v12_50k.jsonl --policies 10000 --random-packets 500 --seed 42 --output semantic_verify_50k_results.json

# -----------------------------------------------------------------------------
# 3b. Verify Step 2 -- anomaly detection, scalability, and ordering benchmarks
#     Run against the same 50,000-policy dataset. Trial counts default to the
#     script's built-in values if you omit the --*-trials flags; set them
#     explicitly below to match (or exceed) the original paper's settings.
#     Use --quick first to sanity-check the pipeline runs end-to-end before
#     committing to a long run.
# -----------------------------------------------------------------------------
python notebook3_v12_run_benchmarks.py --dataset policies_v12_50k.jsonl --anom-trials 500 --scale-trials 10 --ord-trials 10 --ordering 4

# Optional sanity check (fast, runs a small subset of everything first):
#   python notebook3_v12_run_benchmarks.py --dataset policies_v12_50k.jsonl --quick
