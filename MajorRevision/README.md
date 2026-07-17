# Major Revision — Supplementary Scripts and Results

**Manuscript:** "Automated, Formally Proven Conversion of Listed-Rule Firewalls to Tree-Rule Firewalls"
**Submission ID:** Access-2026-25252 (IEEE Access, reject-and-resubmit)
**This folder contains everything produced *during the major revision* in response to the two reviewers' comments.** It supplements — does not replace — the main v12.0 archive already cited in the manuscript (Zenodo DOI: 10.5281/zenodo.20396163), which contains the original framework and the experiments reported in the initial submission.

---

## 1. Why this folder exists

Every file here was generated to answer a specific reviewer comment or editor decision point (D1–D3) raised during the major-revision round. The table below maps each reviewer comment to the exact script and result file that answers it, and to the section of the revised manuscript where the finding is reported.

| Reviewer comment | What it asked for | Script(s) | Result file(s) | Manuscript section |
|---|---|---|---|---|
| **R2.5** — statistics too weak (bare binomial sign test, p=0.03125, no correction) | Effect size, Holm-Bonferroni correction, TOST equivalence test | `scripts/stats_strengthen_v12.py` (re-runs the ordering benchmark with 10 trials/size instead of 5, then computes rank-biserial effect size + Holm-Bonferroni + TOST) | `results/ordering_benchmark_v12_results_merged10.json` (raw 10-trial data), `results/stats_strengthen_v12_results_10trials.json` (computed stats, family=20 correction — used in the manuscript), `results/holm_family4_10trials.json` (alternative family=4 correction scope, kept for comparison, **not** used in the final manuscript), `results/R2.5_Option_A_Family20.md` (write-up comparing both correction scopes) | Table III, Section VI-E |
| **R1.3** — memory measured with `sys.getsizeof` only (known limitations) | Quantitative tracemalloc memory figures | *(tracemalloc instrumentation was already present in `ordering_benchmark_v12.py` from the original submission; no new script needed — see `peak_bytes` field in the JSON above)* | same as above (`peak_bytes` field) | Section VI-E (paragraph on tracemalloc) |
| **R2.4** — baseline fairness / no HiCuts parameter sensitivity | Sweep of HiCuts hyperparameters (binth, spfac) | `scripts/hicuts_sensitivity_v12.py` | `results/hicuts_sensitivity_v12_results.json` | Section VI-G (paragraph on HiCuts parameter sensitivity) |
| **R2.2** — scale limited to 400 rules per policy | Editor decision D1: either run a larger-scale experiment or state operational scope. We chose to run a genuine 50,000-policy dataset (5× the original 10,000). | *(uses the existing `notebook1/2_v12_*.py` and `semantic_verify_v12.py` from the main v12.0 archive — see `scripts/run_50k_experiment.sh` for the exact commands used)* | `results/semantic_verify_50k_results.json` (Theorem 1 check on a 10,000-policy sample drawn from the 50,000), `results/conversion_reports_v12.jsonl` (per-policy conversion metadata for all 50,000 policies), `results/policies_v12_50k.jsonl.gz` (the generated 50,000-policy dataset itself, gzip-compressed) | Section VI-I "Large-Scale Validation", Table VI, Figure 21 |
| **R1.2** — single-platform timing results | Editor decision D2: repeat the scalability benchmark on a second, independently-specified machine | *(uses the existing `scalability_benchmark_v12.py` from the main v12.0 archive — see `scripts/run_100k_experiment.sh` for context; the actual second-platform command is the one-liner in Section VI-J of the manuscript)* | `results/scalability_2ndplatform_results_clean.json` (Intel Core i7-8700 @ 3.20 GHz, 6C/12T, 16 GB RAM, Windows 11 — re-run after an initial contaminated run, discarded, was found to have a concurrent CPU-heavy process competing for resources) | Section VI-J "Cross-Platform Validation", Table VII |
| **R2.1** — no real-world (non-ClassBench-ng) ruleset | Editor decision D3: obtain a real production ruleset if possible | *(no script — a real production ruleset could not be obtained; this is disclosed as a limitation)* | *(none — see manuscript text instead)* | Section VIII-C "External Validity" (new paragraph on ClassBench-ng's real-seed provenance) |
| **R2.6** — related work too narrow | Broaden related work | *(literature only, no code)* | *(none)* | Section II-C, References [29]–[32] |
| **R2.3** — novelty unclear | "Adopted vs. novel" positioning paragraph | *(text only, no code)* | *(none)* | End of Section I |
| **R1.5** — 24 figures, running-title artifact | Reduce figure count, fix header | *(document editing only, no code)* | *(none)* | Figures 1–20 (renumbered from 24), page headers |
| **R1.1** — FDD baseline fidelity | Clarify FDD is a controlled reimplementation, not an independent codebase | *(text only, no code)* | *(none)* | Section VI-G, Section VIII-B |
| **R1.4** — abstract scope | State {TCP, UDP, ICMP} scope explicitly | *(text only, no code)* | *(none)* | Abstract |

`merge_chunks.py` is a utility script used internally to combine the ordering-benchmark trials, which were run in multiple smaller batches (2–4 trials at a time) due to execution-time limits in the sandboxed environment used for this analysis; it is included for full transparency of how `ordering_benchmark_v12_results_merged10.json` was assembled from the raw per-batch outputs. It has no bearing on the experiment's validity — it only concatenates independent trials that use the same generator and seeds documented in the original `ordering_benchmark_v12.py`.

---

## 2. Generative AI disclosure

In accordance with IEEE publication policy, the scripts in `scripts/` (`stats_strengthen_v12.py`, `hicuts_sensitivity_v12.py`, `merge_chunks.py`) were AI-drafted (Anthropic Claude) during the major-revision round, in the same manner disclosed in the manuscript's existing Generative AI Disclosure section for the original v12.0 framework code. All AI-drafted code was reviewed by the author; the statistical methodology (effect size choice, correction scope, equivalence-test bounds) and the decision of which experiments to run were author decisions, not AI decisions.

---

## 3. File manifest

```
MajorRevision/
├── README.md                                        (this file)
├── README.html                                       (HTML version of this file)
├── scripts/
│   ├── stats_strengthen_v12.py                       (R2.5: effect size + Holm-Bonferroni + TOST)
│   ├── hicuts_sensitivity_v12.py                      (R2.4: HiCuts binth/spfac sweep)
│   ├── merge_chunks.py                                (utility: combine chunked ordering-benchmark runs)
│   ├── run_50k_experiment.sh                          (D1: commands used for the 50,000-policy run)
│   └── run_100k_experiment.sh                         (reference script; superseded by the 50k run — see Section VI-I)
└── results/
    ├── ordering_benchmark_v12_results_merged10.json   (raw 10-trial ordering-benchmark data)
    ├── stats_strengthen_v12_results_10trials.json     (R2.5 computed stats, family=20 — used in manuscript)
    ├── holm_family4_10trials.json                     (R2.5 alternative correction scope, for comparison only)
    ├── R2.5_Option_A_Family20.md                       (write-up comparing correction-scope choices)
    ├── hicuts_sensitivity_v12_results.json            (R2.4 sensitivity sweep results)
    ├── semantic_verify_50k_results.json               (D1: Theorem 1 check, 10k sample from 50k policies)
    ├── conversion_reports_v12.jsonl                    (D1: per-policy conversion metadata, all 50,000 policies)
    ├── policies_v12_50k.jsonl.gz                       (D1: the 50,000-policy dataset itself, gzip-compressed)
    └── scalability_2ndplatform_results_clean.json     (D2: second-platform scalability benchmark, i7-8700)
```

To decompress the dataset: `gunzip -k policies_v12_50k.jsonl.gz`

---

## 4. Relationship to the main v12.0 archive

This folder does **not** duplicate the original framework code (`lrf_trf_app_v12.py`, `notebook1/2/3_v12_*.py`, `semantic_verify_v12.py`, `anomaly_benchmark_v12.py`, `scalability_benchmark_v12.py`, `ordering_benchmark_v12.py`, `hicuts_baseline_v12.py`, `fdd_baseline_v12.py`, etc.), which is unchanged from the original submission and remains available at:

- GitHub: https://github.com/thawatchai2799/TreeRuleFirewall_20260526_2001
- Zenodo (archived, DOI): 10.5281/zenodo.20396163

The scripts in this folder import from and depend on that original code (e.g., `stats_strengthen_v12.py` and `hicuts_sensitivity_v12.py` both `import` from `lrf_trf_app_v12.py`); to re-run anything here, place these scripts in the same directory as the original v12.0 files.
