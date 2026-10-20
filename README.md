# Bone Health Score — OJPHI reproducibility code

**Release candidate — not yet published.** This repository contains code but **no individual-level study data**, nicknames, private database exports, credentials, or application secrets.

Associated manuscript: *Real-World Deployment of a Web-Based Bone Health Self-Assessment Tool in Thailand: A Descriptive Cross-Sectional Study* (OJPHI #104939).

## What is included

- `analysis/reproduce_analysis.py`: consolidated Python 3 analysis script for reproducing the reported descriptive results. Reconstructs the study cohort from an authorized private database export, repeats the selected DXA and unfavorable-factor sensitivity analyses, and evaluates probable repeat assessments.
- `app_rules/archived_calculations.ts`: a byte-for-byte source snapshot of the application calculation module provided by the investigators. It retains application imports and is supplied for code review, not standalone execution.
- `app_rules/scoring_dxa_rules.ts`: isolated TypeScript versions of the application-generated Bone Health Score, its categories, and the DXA-consideration prompt. The functions omit database access, user identification, display code, and nonessential application features.
- `tests/test_analysis.py` and `tests/synthetic_rules.test.mjs`: synthetic-data unit tests. None of the test cases represent study participants.

**Code scope:** The repository preserves the archived application calculation module and provides isolated scoring and DXA-prompt functions for direct inspection. The public-release Python script consolidates the documented cohort-selection, descriptive, and sensitivity-analysis procedures, with added verification checks; its outputs were checked against the archived study export and the earlier analysis audit workbook. This source collection does not establish an independently verifiable deployment date for every historical app version.

## Reproduce the aggregate analysis

The full export consists of 304 submitted records and is **not included** because it contains linkable health-related responses. Authorized investigators with a local copy can run:

```bash
python analysis/reproduce_analysis.py --input /private/path/scores_rows.csv --output /private/path/aggregate_outputs
```

The script requires Python 3.10+ and its standard library only. The input must preserve the archived CSV column names, JSON-valued fracture-history field, and submission timestamps. Excel (`.xlsx`) users should export a CSV copy first. An older export containing only 261 records will *not* reproduce the final analytic cohort.

The analysis creates aggregate-only summaries (`analysis_summary.json`, S3–S6 CSV summaries, and `verification_report.json`). The built-in manuscript-specific checks verify the published 304 → 296 → 256 cohort flow, major results, and repeat-sensitivity cohort of 243 assessments. These checks intentionally fail if a different data export is provided. Outputs must be kept outside the public Git repository.

### Dataset and study rules used

- Study period: October 9 to December 20, 2025, inclusive (date component of the archived timestamp).
- Team-designated internal test identifiers: `test`, `Test`, and `Tester`. The exclusion check trims leading/trailing whitespace and case-folds; 40 in-period records are excluded on this basis. The investigators confirmed these were team testing identifiers; do not infer that this procedure was specified before deployment.
- Adult eligibility: age ≥20 years. No additional in-period non-test record was excluded for age <20 years in the examined export. No numeric-plausibility exclusions were made.
- Unit of analysis: **completed assessment**, not verified individual.
- Repeated nicknames: strip leading/trailing whitespace and case-fold, **without fuzzy spelling matches**; review matching sex, age, weight, and height. The deterministic sensitivity implementation requires matching sex and age and differences ≤0.5 kg and ≤0.5 cm, respectively. It groups concordant records into connected components and retains the earliest assessment in each probable cluster. These are not confirmed identities.
- Application-defined score categories and DXA prompts are rule-based outputs, **not** externally validated clinical risk classifications or full TOPF eligibility determinations.
- The menopause-default sensitivity excludes female records aged 45–64 with the stored default response, changing the denominator from 254 to 226; the percentages are therefore not paired comparisons.
- Descriptive summaries use sample SD and interpolated quartiles matching conventional pandas defaults. Percentages are formatted to one decimal place.

## Run synthetic tests (no health records required)

For Python:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

For isolated TypeScript rules (Node.js 22+ with built-in TypeScript type stripping):

```bash
node --experimental-strip-types tests/synthetic_rules.test.mjs
```

The Python standard-library smoke tests check nickname normalization, multi-field repeat detection, age logic, and menopause-default handling. The TypeScript synthetic tests cover scoring weights, category thresholds, age boundaries, and selected DXA rules. These synthetic tests are separate from the private author verification against the full study dataset.

## Independent verification performed by investigators' analysis team

With the archived private 304-record export, the Python implementation matched **45/45** prespecified aggregate checks. The score was recalculated from questionnaire inputs and matched the archived `final_score` for **256/256** study assessments. A private source-equivalence comparison of the isolated TypeScript functions against the supplied archived `calculations.ts` found no differences in score, score category, or DXA decision across **364 input sets** (256 study assessments plus 108 synthetic boundary cases). Neither the private input data nor those record-level comparisons are part of this public package.

The public code enables methodological inspection and repetition when an approved dataset is available; it cannot recreate participant-based tables from no dataset.

## Data protection and limitations

This repository must not contain raw study data, even as sample screenshots, Git commit history, notebook outputs, database connections, or test fixtures. No participant-level dataset is public. De-identified data sharing, if any, is subject to the manuscript's Data Availability statement and ethics/data-governance approval.

The archived `calculations.ts` also contains personalized Thai-language recommendations, database operations, and a percentile display; these are deliberately excluded from the isolated scoring and DXA rule module. The analysis script reads stored `final_score` for manuscript summaries rather than rewriting historical scores.

## Repository release notes

Before making the repository public, confirm permission to redistribute the hospital application code and check that no credential files, confidential data, or participant-level extracts were added. The archived calculation module imports the original app-specific `types` and `supabase` modules, which are intentionally not provided; use the isolated rule file and its tests for executable verification.