# Extended Experiments — LRF-to-TRF Framework

**Manuscript:** "Automated, Formally Proven Conversion of Listed-Rule Firewalls to Tree-Rule Firewalls"
**Author:** Thawatchai Chomsiri · Mahasarakham University, Thailand

This folder contains a second round of experiments extending the core evaluation: a larger dataset, a second hardware platform, a hyperparameter sensitivity sweep, and a strengthened statistical treatment of the ordering benchmark. It **supplements — does not replace** the main framework archive in the repository root, which contains the conversion framework itself and the primary experiments.

---

## 1. What each experiment answers

| Research question | Script(s) | Result file(s) | Manuscript section |
|---|---|---|---|
| **Does the depth result hold at larger scale?** The primary evaluation used 10,000 policies; here an independent 50,000-policy dataset (5×) is generated and converted, with semantic fidelity re-checked on a 10,000-policy random sample. | *(uses `notebook1/2_v12_*.py` and `semantic_verify_v12.py` from the repository root — see `scripts/run_50k_experiment.sh` for the exact commands)* | `results/policies_v12_50k.jsonl.gz` (the dataset), `results/conversion_reports_v12.jsonl.gz` (per-policy conversion metadata for all 50,000), `results/semantic_verify_50k_results.json` (Theorem 1 check on the sample) | Section 6.9 "Large-Scale Validation", Table 6 |
| **Are the timing results specific to one machine?** The primary timings came from a single workstation; here the scalability benchmark is repeated on an independently specified second machine. | *(uses `scalability_benchmark_v12.py` from the repository root)* | `results/scalability_2ndplatform_results_clean.json` (Intel Core i7-8700 @ 3.20 GHz, 6C/12T, 16 GB RAM, Windows 11) | Section 6.10 "Cross-Platform Validation", Table 7 |
| **Do the HiCuts comparison conclusions depend on its hyperparameters?** The main comparison fixes binth=8, spfac=4; both are swept here to test whether HiCuts' variable, data-dependent depth is structural or configuration-specific. | `scripts/hicuts_sensitivity_v12.py` | `results/hicuts_sensitivity_v12_results.json` | Section 6.7 (HiCuts parameter sensitivity) |
| **How robust is the ordering result under a rigorous statistical treatment?** The benchmark is re-run with 10 independent trials per condition (up from 5), then analysed with a matched-pairs rank-biserial effect size, Holm-Bonferroni family-wise correction, and TOST equivalence testing. | `scripts/stats_strengthen_v12.py` | `results/ordering_benchmark_v12_results_merged10.json` (raw 10-trial data), `results/stats_strengthen_v12_results_10trials.json` (computed statistics, family = 20 — **the version used in the manuscript**), `results/holm_family4_10trials.json` (alternative family = 4 correction scope, retained for comparison, **not** used), `results/ordering_statistics_family20.md` (write-up comparing the two scopes) | Section 6.5, Table 3 |
| **How much memory does conversion actually consume?** Peak-memory figures measured with `tracemalloc` rather than `sys.getsizeof`. | *(instrumentation already present in `ordering_benchmark_v12.py`; no separate script — see the `peak_bytes` field)* | `results/ordering_benchmark_v12_results_merged10.json` (`peak_bytes` field) | Section 6.5, Section 7.5 |

**Note on the second-platform run.** An initial run on the second machine was discarded after a concurrent CPU-heavy process was found to have been competing for resources. `scalability_2ndplatform_results_clean.json` is the clean re-run and the only version reported.

---

## 2. Generative AI disclosure

The scripts in `scripts/` (`stats_strengthen_v12.py`, `hicuts_sensitivity_v12.py`, `merge_chunks.py`) were AI-drafted (Anthropic Claude), in the same manner disclosed in the manuscript's Generative AI Disclosure section for the framework code. All AI-drafted code was reviewed and tested by the author. The statistical methodology — the choice of effect-size measure, the scope of the family-wise correction, and the equivalence-test bounds — and the decision of which experiments to run were author decisions, not AI decisions.

---

## 3. File manifest

```
ExtendedExperiments/
├── README.md                                        (this file)
├── README.html                                      (HTML version of this file)
├── scripts/
│   ├── stats_strengthen_v12.py                      (effect size + Holm-Bonferroni + TOST)
│   ├── hicuts_sensitivity_v12.py                    (HiCuts binth/spfac sweep)
│   ├── merge_chunks.py                              (utility: combine chunked benchmark runs)
│   ├── run_50k_experiment.sh                        (commands used for the 50,000-policy run)
│   └── run_100k_experiment.sh                       (reference script; superseded by the 50k run)
└── results/
    ├── ordering_benchmark_v12_results_merged10.json (raw 10-trial ordering-benchmark data)
    ├── stats_strengthen_v12_results_10trials.json   (computed statistics, family=20 — used in manuscript)
    ├── holm_family4_10trials.json                   (alternative correction scope, for comparison only)
    ├── ordering_statistics_family20.md              (write-up comparing correction-scope choices)
    ├── hicuts_sensitivity_v12_results.json          (HiCuts sensitivity sweep results)
    ├── semantic_verify_50k_results.json             (Theorem 1 check, 10k sample from 50k policies)
    ├── conversion_reports_v12.jsonl.gz              (per-policy conversion metadata, all 50,000 policies)
    ├── policies_v12_50k.jsonl.gz                    (the 50,000-policy dataset itself)
    └── scalability_2ndplatform_results_clean.json   (second-platform scalability benchmark, i7-8700)
```

To decompress a dataset: `gunzip -k policies_v12_50k.jsonl.gz`

---

## 4. Relationship to the main archive

This folder does **not** duplicate the framework code (`lrf_trf_app_v12.py`, `notebook1/2/3_v12_*.py`, `semantic_verify_v12.py`, `anomaly_benchmark_v12.py`, `scalability_benchmark_v12.py`, `ordering_benchmark_v12.py`, `hicuts_baseline_v12.py`, `fdd_baseline_v12.py`, and the rest), which lives in the repository root and is unchanged. Both are archived together at:

- GitHub: https://github.com/thawatchai2799/TreeRuleFirewall_20260526_2001
- Zenodo (archived, DOI): 10.5281/zenodo.20396163

The scripts here import from that code (`stats_strengthen_v12.py` and `hicuts_sensitivity_v12.py` both import `lrf_trf_app_v12.py`); to re-run anything, place them in the same directory as the root-level files, or run them from the repository root.
