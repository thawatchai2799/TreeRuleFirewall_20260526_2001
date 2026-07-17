<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="" xml:lang="">
<head>
  <meta charset="utf-8" />
  <meta name="generator" content="pandoc" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes" />
  <title>Major Revision Supplementary Materials - Access-2026-25252</title>
  <style>
    code{white-space: pre-wrap;}
    span.smallcaps{font-variant: small-caps;}
    div.columns{display: flex; gap: min(4vw, 1.5em);}
    div.column{flex: auto; overflow-x: auto;}
    div.hanging-indent{margin-left: 1.5em; text-indent: -1.5em;}
    /* The extra [class] is a hack that increases specificity enough to
       override a similar rule in reveal.js */
    ul.task-list[class]{list-style: none;}
    ul.task-list li input[type="checkbox"] {
      font-size: inherit;
      width: 0.8em;
      margin: 0 0.8em 0.2em -1.6em;
      vertical-align: middle;
    }
    .display.math{display: block; text-align: center; margin: 0.5rem auto;}
  </style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css" />
</head>
<body>
<header id="title-block-header">
<h1 class="title">Major Revision Supplementary Materials -
Access-2026-25252</h1>
</header>
<h1 id="major-revision-supplementary-scripts-and-results">Major Revision
— Supplementary Scripts and Results</h1>
<p><strong>Manuscript:</strong> “Automated, Formally Proven Conversion
of Listed-Rule Firewalls to Tree-Rule Firewalls” <strong>Submission
ID:</strong> Access-2026-25252 (IEEE Access, reject-and-resubmit)
<strong>This folder contains everything produced <em>during the major
revision</em> in response to the two reviewers’ comments.</strong> It
supplements — does not replace — the main v12.0 archive already cited in
the manuscript (Zenodo DOI: 10.5281/zenodo.20396163), which contains the
original framework and the experiments reported in the initial
submission.</p>
<hr />
<h2 id="why-this-folder-exists">1. Why this folder exists</h2>
<p>Every file here was generated to answer a specific reviewer comment
or editor decision point (D1–D3) raised during the major-revision round.
The table below maps each reviewer comment to the exact script and
result file that answers it, and to the section of the revised
manuscript where the finding is reported.</p>
<table>
<colgroup>
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr class="header">
<th>Reviewer comment</th>
<th>What it asked for</th>
<th>Script(s)</th>
<th>Result file(s)</th>
<th>Manuscript section</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>R2.5</strong> — statistics too weak (bare binomial sign
test, p=0.03125, no correction)</td>
<td>Effect size, Holm-Bonferroni correction, TOST equivalence test</td>
<td><code>scripts/stats_strengthen_v12.py</code> (re-runs the ordering
benchmark with 10 trials/size instead of 5, then computes rank-biserial
effect size + Holm-Bonferroni + TOST)</td>
<td><code>results/ordering_benchmark_v12_results_merged10.json</code>
(raw 10-trial data),
<code>results/stats_strengthen_v12_results_10trials.json</code>
(computed stats, family=20 correction — used in the manuscript),
<code>results/holm_family4_10trials.json</code> (alternative family=4
correction scope, kept for comparison, <strong>not</strong> used in the
final manuscript), <code>results/R2.5_Option_A_Family20.md</code>
(write-up comparing both correction scopes)</td>
<td>Table III, Section VI-E</td>
</tr>
<tr class="even">
<td><strong>R1.3</strong> — memory measured with
<code>sys.getsizeof</code> only (known limitations)</td>
<td>Quantitative tracemalloc memory figures</td>
<td><em>(tracemalloc instrumentation was already present in
<code>ordering_benchmark_v12.py</code> from the original submission; no
new script needed — see <code>peak_bytes</code> field in the JSON
above)</em></td>
<td>same as above (<code>peak_bytes</code> field)</td>
<td>Section VI-E (paragraph on tracemalloc)</td>
</tr>
<tr class="odd">
<td><strong>R2.4</strong> — baseline fairness / no HiCuts parameter
sensitivity</td>
<td>Sweep of HiCuts hyperparameters (binth, spfac)</td>
<td><code>scripts/hicuts_sensitivity_v12.py</code></td>
<td><code>results/hicuts_sensitivity_v12_results.json</code></td>
<td>Section VI-G (paragraph on HiCuts parameter sensitivity)</td>
</tr>
<tr class="even">
<td><strong>R2.2</strong> — scale limited to 400 rules per policy</td>
<td>Editor decision D1: either run a larger-scale experiment or state
operational scope. We chose to run a genuine 50,000-policy dataset (5×
the original 10,000).</td>
<td><em>(uses the existing <code>notebook1/2_v12_*.py</code> and
<code>semantic_verify_v12.py</code> from the main v12.0 archive — see
<code>scripts/run_50k_experiment.sh</code> for the exact commands
used)</em></td>
<td><code>results/semantic_verify_50k_results.json</code> (Theorem 1
check on a 10,000-policy sample drawn from the 50,000),
<code>results/conversion_reports_v12.jsonl</code> (per-policy conversion
metadata for all 50,000 policies),
<code>results/policies_v12_50k.jsonl.gz</code> (the generated
50,000-policy dataset itself, gzip-compressed)</td>
<td>Section VI-I “Large-Scale Validation”, Table VI, Figure 21</td>
</tr>
<tr class="odd">
<td><strong>R1.2</strong> — single-platform timing results</td>
<td>Editor decision D2: repeat the scalability benchmark on a second,
independently-specified machine</td>
<td><em>(uses the existing <code>scalability_benchmark_v12.py</code>
from the main v12.0 archive — see
<code>scripts/run_100k_experiment.sh</code> for context; the actual
second-platform command is the one-liner in Section VI-J of the
manuscript)</em></td>
<td><code>results/scalability_2ndplatform_results_clean.json</code>
(Intel Core i7-8700 @ 3.20 GHz, 6C/12T, 16 GB RAM, Windows 11 — re-run
after an initial contaminated run, discarded, was found to have a
concurrent CPU-heavy process competing for resources)</td>
<td>Section VI-J “Cross-Platform Validation”, Table VII</td>
</tr>
<tr class="even">
<td><strong>R2.1</strong> — no real-world (non-ClassBench-ng)
ruleset</td>
<td>Editor decision D3: obtain a real production ruleset if
possible</td>
<td><em>(no script — a real production ruleset could not be obtained;
this is disclosed as a limitation)</em></td>
<td><em>(none — see manuscript text instead)</em></td>
<td>Section VIII-C “External Validity” (new paragraph on ClassBench-ng’s
real-seed provenance)</td>
</tr>
<tr class="odd">
<td><strong>R2.6</strong> — related work too narrow</td>
<td>Broaden related work</td>
<td><em>(literature only, no code)</em></td>
<td><em>(none)</em></td>
<td>Section II-C, References [29]–[32]</td>
</tr>
<tr class="even">
<td><strong>R2.3</strong> — novelty unclear</td>
<td>“Adopted vs. novel” positioning paragraph</td>
<td><em>(text only, no code)</em></td>
<td><em>(none)</em></td>
<td>End of Section I</td>
</tr>
<tr class="odd">
<td><strong>R1.5</strong> — 24 figures, running-title artifact</td>
<td>Reduce figure count, fix header</td>
<td><em>(document editing only, no code)</em></td>
<td><em>(none)</em></td>
<td>Figures 1–20 (renumbered from 24), page headers</td>
</tr>
<tr class="even">
<td><strong>R1.1</strong> — FDD baseline fidelity</td>
<td>Clarify FDD is a controlled reimplementation, not an independent
codebase</td>
<td><em>(text only, no code)</em></td>
<td><em>(none)</em></td>
<td>Section VI-G, Section VIII-B</td>
</tr>
<tr class="odd">
<td><strong>R1.4</strong> — abstract scope</td>
<td>State {TCP, UDP, ICMP} scope explicitly</td>
<td><em>(text only, no code)</em></td>
<td><em>(none)</em></td>
<td>Abstract</td>
</tr>
</tbody>
</table>
<p><code>merge_chunks.py</code> is a utility script used internally to
combine the ordering-benchmark trials, which were run in multiple
smaller batches (2–4 trials at a time) due to execution-time limits in
the sandboxed environment used for this analysis; it is included for
full transparency of how
<code>ordering_benchmark_v12_results_merged10.json</code> was assembled
from the raw per-batch outputs. It has no bearing on the experiment’s
validity — it only concatenates independent trials that use the same
generator and seeds documented in the original
<code>ordering_benchmark_v12.py</code>.</p>
<hr />
<h2 id="generative-ai-disclosure">2. Generative AI disclosure</h2>
<p>In accordance with IEEE publication policy, the scripts in
<code>scripts/</code> (<code>stats_strengthen_v12.py</code>,
<code>hicuts_sensitivity_v12.py</code>, <code>merge_chunks.py</code>)
were AI-drafted (Anthropic Claude) during the major-revision round, in
the same manner disclosed in the manuscript’s existing Generative AI
Disclosure section for the original v12.0 framework code. All AI-drafted
code was reviewed by the author; the statistical methodology (effect
size choice, correction scope, equivalence-test bounds) and the decision
of which experiments to run were author decisions, not AI decisions.</p>
<hr />
<h2 id="file-manifest">3. File manifest</h2>
<pre><code>MajorRevision/
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
    └── scalability_2ndplatform_results_clean.json     (D2: second-platform scalability benchmark, i7-8700)</code></pre>
<p>To decompress the dataset:
<code>gunzip -k policies_v12_50k.jsonl.gz</code></p>
<hr />
<h2 id="relationship-to-the-main-v12.0-archive">4. Relationship to the
main v12.0 archive</h2>
<p>This folder does <strong>not</strong> duplicate the original
framework code (<code>lrf_trf_app_v12.py</code>,
<code>notebook1/2/3_v12_*.py</code>,
<code>semantic_verify_v12.py</code>,
<code>anomaly_benchmark_v12.py</code>,
<code>scalability_benchmark_v12.py</code>,
<code>ordering_benchmark_v12.py</code>,
<code>hicuts_baseline_v12.py</code>, <code>fdd_baseline_v12.py</code>,
etc.), which is unchanged from the original submission and remains
available at:</p>
<ul>
<li>GitHub:
https://github.com/thawatchai2799/TreeRuleFirewall_20260526_2001</li>
<li>Zenodo (archived, DOI): 10.5281/zenodo.20396163</li>
</ul>
<p>The scripts in this folder import from and depend on that original
code (e.g., <code>stats_strengthen_v12.py</code> and
<code>hicuts_sensitivity_v12.py</code> both <code>import</code> from
<code>lrf_trf_app_v12.py</code>); to re-run anything here, place these
scripts in the same directory as the original v12.0 files.</p>
</body>
</html>
