# Bone Health Score

**Application Algorithms and Reproducible Analysis**

This repository contains the application scoring logic, DXA-consideration rules, and Python analysis code associated with the study:

*Real-World Deployment of a Web-Based Bone Health Self-Assessment Tool in Thailand: A Descriptive Cross-Sectional Study*

The code is provided to support methodological transparency, inspection of the rule-based application outputs, and reproducibility of the reported descriptive and sensitivity analyses.

## Repository contents

| File | Description |
| --- | --- |
| `analysis/reproduce_analysis.py` | Python implementation of cohort selection, descriptive analyses, repeat-assessment sensitivity analysis, and DXA-prompt sensitivity analyses. |
| `app_rules/archived_calculations.ts` | Archived application calculation module containing scoring and DXA logic, along with application-specific functions and imports. |
| `app_rules/scoring_dxa_rules.ts` | Standalone scoring and DXA-prompt functions, separated from database and interface operations for easier inspection and testing. |
| `tests/test_analysis.py` | Python unit tests using synthetic records. |
| `tests/synthetic_rules.test.mjs` | Synthetic tests for scoring thresholds and DXA-prompt rules. |

The Python analysis script consolidates the study's documented data-processing and statistical procedures and includes consistency checks for key reported results. The isolated TypeScript functions were verified against the archived application calculation module.

## Study data and analytical cohort

The retrospective study used completed assessments submitted between **October 9 and December 20, 2025**. The database export contained 304 records, of which eight were outside the study period and 40 were internal application-testing submissions. The primary analytical dataset comprised **256 eligible completed assessments**.

Because users were not authenticated, the unit of analysis was the **completed assessment**, rather than a confirmed unique individual. A sensitivity analysis retained the earliest assessment within probable repeat clusters identified using normalized nicknames and concordant demographic and anthropometric characteristics, resulting in **243 assessments**.

The primary analysis was descriptive. The application-generated Bone Health Score and DXA-consideration prompt are rule-based outputs and should not be interpreted as clinically validated diagnostic or risk classifications. The DXA-prompt rules reflect selected criteria captured by the questionnaire, not the full set of Thai Osteoporosis Foundation indications.

## Reproducing the analysis

**Requirements:** Python 3.10 or later. The analysis uses the Python standard library; no additional Python packages are required.

With authorized access to the original structured data export, run:

```bash
python analysis/reproduce_analysis.py \
  --input /path/to/private/scores_rows.csv \
  --output /path/to/private/aggregate_outputs
```

The input CSV must preserve the original column names and data representations, including JSON-formatted fracture-history responses and submission timestamps. The output folder should be **outside this GitHub repository**.

The script generates aggregate summaries and tables for descriptive and sensitivity analyses, together with a verification report. Its principal steps are:

1. Select records within the study period and exclude internal test submissions.
2. Apply the adult eligibility criterion (age ≥20 years).
3. Calculate descriptive summaries, score distributions, and DXA-prompt frequencies.
4. Identify probable repeat-assessment clusters using matching nicknames after trimming whitespace and ignoring letter case; require identical recorded age and sex and weight/height differences of no more than 0.5 kg/0.5 cm.
5. Repeat the selected descriptive analyses after retaining the earliest assessment within each probable repeat cluster.
6. Perform the reported DXA-prompt and unfavorable-factor sensitivity analyses.

The repeat-assessment procedure identifies *probable* repeated submissions, not verified individual identities. For the menopause-default sensitivity analysis, excluding records with the relevant default response changes the evaluable denominator; its percentages are not directly comparable as paired estimates.

## Application rules and testing

The standalone TypeScript module provides the weighted Bone Health Score, score categories, and DXA-consideration logic without requiring the original web application's database connection. The archived application module is included as a source reference and retains imports that depend on the original application environment.

To run the included synthetic tests:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

With Node.js 22 or later:

```bash
node --experimental-strip-types tests/synthetic_rules.test.mjs
```

The scoring and DXA implementations were checked against the archived application logic, and the aggregate analytical outputs were checked against the reported study results. Synthetic tests contain no actual participant records.

## Data availability and privacy

**Individual-level assessment data are not included in this repository.** The underlying dataset contains linkable, self-reported health-related information. Access to de-identified analytical data, where permitted, is subject to the institutional ethics and data-governance conditions described in the associated manuscript.

The repository contains research code and documentation only; it does not contain user nicknames, participant-level exports, credentials, or database connection secrets. Public availability of the code does not imply public availability of the study dataset.

## Citation

**Associated publication**

Suwanaratana R, Rujiraphan T, Lordkaew N, Chanalithichai N. *Real-World Deployment of a Web-Based Bone Health Self-Assessment Tool in Thailand: A Descriptive Cross-Sectional Study.* Online Journal of Public Health Informatics. [Publication details and DOI to be added upon publication.]

**Software repository**

Suwanaratana R. *Bone Health Score: Application Algorithms and Reproducible Analysis* [Computer software]. GitHub; 2026.

https://github.com/ModSpurz/bone-health-score-ojphi

When citing the software, please specify the version or commit used to support reproducibility.
