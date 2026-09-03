# Changelog

## v14.0 (2026-09)

Revision accompanying the revised manuscript.

### Added
- `tests/test_proposition4_counterexample.py` - the two-rule policy used in the proof of
  Proposition 4; verifies 10 internal nodes under Ordering 1 and 14 under Ordering 5 (five leaves each).
- `figures/scripts/` - matplotlib scripts that regenerate Figures 4, 5, 11, 13, 14, and 15 at 600 dpi
  from the raw result files in this repository.
- `ExtendedExperiments/AdaptiveOrdering/` - data (`e1_wide.csv`, `summary.txt`) and README for the
  follow-up ordering study of Section 7.4 (800 policies x 12 orderings).

### Changed
- Figures 4 and 5: the example rules are now listed in first-match order (specific rule before the
  general rule), consistent with the pipeline; the earlier versions listed them in the reverse order.
- Figure 11: the LRF curve is labelled as the Python linear-scan reference, not as iptables.
- Figures 13, 14, 15: labels now read "FDD-style fixed-order ablation"; the pipeline title no longer
  implies that the ordering benchmark uses the 10,000-policy dataset; the HiCuts depth range reads 1-12.
- Documentation clarifies that the ordering benchmark (`ordering_benchmark_v12.py`) uses ten
  independently generated policies per size, built by its own simpler generator, not the
  10,000-policy dataset; the numbers in the results files are unchanged.
- Documentation notes that the FDD baseline (`fdd_baseline_v12.py`) is a fixed-order ablation
  built within this framework, not an independent implementation of Firewall Decision Diagrams.

## v13.0 (2026-08)
- Repository synchronized with the manuscript; ExtendedExperiments folder added; 50k policy dataset added.
