#!/usr/bin/env python3
"""OJPHI Bone Health Score: public-release analysis and verification script.

Input: authorized private study export in CSV format.
Output: aggregate, non-identifiable tables only. Never publishes input records.
This script consolidates the documented analysis procedures and includes
verification checks against manuscript outputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date
import json
from decimal import Decimal, ROUND_HALF_EVEN
import math
from pathlib import Path
from statistics import mean, stdev

STUDY_START = date(2025, 10, 9)
STUDY_END = date(2025, 12, 20)
# Historical internal test labels: confirm their provenance against project logs
# before public release. Matching is case-insensitive after trimming whitespace.
INTERNAL_TEST_LABELS = {"test", "tester"}

REQUIRED = {
    "id", "created_at", "nickname", "final_score", "input_age",
    "input_gender", "input_weight_kg", "input_height_cm",
    "input_fracture_history", "input_fall_history", "input_parent_fracture",
    "input_steroids", "input_smoking", "input_alcohol", "input_caffeine",
    "input_exercise", "input_calcium", "input_vitamin_d",
    "input_balance_exercise", "input_menopause_before_45",
}


def read_records(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Required columns missing: " + ", ".join(sorted(missing)))
        return list(reader)


def nickname_key(s: str) -> str:
    """Trim outer whitespace and case-fold; do not infer verified identities."""
    return (s or "").strip().casefold()


def submitted_date(row: dict) -> date:
    # Exported timestamps are ISO dates with a UTC offset; the database
    # export's date component is used, consistent with the reviewed cohort.
    return date.fromisoformat(row["created_at"][:10])


def within_study(row: dict) -> bool:
    return STUDY_START <= submitted_date(row) <= STUDY_END


def as_int(row: dict, key: str) -> int:
    return int(float(row[key]))


def as_float(row: dict, key: str) -> float:
    return float(row[key])


def flag(row: dict, key: str) -> bool:
    return row[key].strip().lower() == "true"


def bmi(row: dict) -> float:
    return as_float(row, "input_weight_kg") / (as_float(row, "input_height_cm") / 100.0) ** 2


def fracture_sites(row: dict) -> dict:
    return json.loads(row["input_fracture_history"] or "{}")


def has_fracture(row: dict) -> bool:
    return any(bool(v) for v in fracture_sites(row).values())


def age_group(row: dict) -> str:
    a = as_int(row, "input_age")
    if a < 50:
        return "20-49"
    if a < 65:
        return "50-64"
    if a < 70:
        return "65-69"
    return ">=70"


def score_category(row: dict) -> str:
    score = as_int(row, "final_score")
    if score > 125:
        return "Excellent"
    if score >= 95:
        return "Good"
    if score >= 70:
        return "Needs improvement"
    return "High risk"


def age_threshold(row: dict) -> bool:
    a = as_int(row, "input_age")
    return ((row["input_gender"] == "Female" and a >= 65)
            or (row["input_gender"] == "Male" and a >= 70))


def dxa_non_age_reasons(row: dict, relax_early_menopause: bool = False) -> list[str]:
    """Exact captured variables from the deployed app (not full TOPF eligibility)."""
    s, a = row["input_gender"], as_int(row, "input_age")
    if s not in {"Female", "Male"} or age_threshold(row):
        return []
    can_use_other = a > 50
    reasons = []
    if (s == "Female" and row["input_menopause_before_45"] == "yes"
            and (can_use_other or relax_early_menopause)):
        reasons.append("Early menopause")
    if can_use_other:
        if bmi(row) < 20:
            reasons.append("BMI <20")
        if flag(row, "input_parent_fracture"):
            reasons.append("Parental hip fracture")
        if has_fracture(row):
            reasons.append("Low-trauma fracture")
        if flag(row, "input_steroids"):
            reasons.append("Glucocorticoids >3 months")
    return reasons


def dxa_prompt(row: dict, relax_early_menopause: bool = False) -> bool | None:
    if row["input_gender"] not in {"Female", "Male"}:
        return None
    return age_threshold(row) or bool(dxa_non_age_reasons(row, relax_early_menopause))


def menopause_default(row: dict) -> bool:
    return (row["input_gender"] == "Female"
            and 45 <= as_int(row, "input_age") <= 64
            and row["input_menopause_before_45"] == "not_applicable")


def unfavorable_flags(row: dict) -> dict[str, bool]:
    return {
        "Infrequent weight-bearing exercise": row["input_exercise"] == "less_than_1",
        "Infrequent calcium intake": row["input_calcium"] == "less_often",
        "Predominantly indoor vitamin D exposure": row["input_vitamin_d"] == "indoor",
        "Current smoking": flag(row, "input_smoking"),
        "Alcohol >3 drinks/day": flag(row, "input_alcohol"),
        "Glucocorticoids >3 months": flag(row, "input_steroids"),
        "Caffeine >4 cups/day": flag(row, "input_caffeine"),
        "No balance exercise": not flag(row, "input_balance_exercise"),
    }


def factor_count(row: dict, excluded: frozenset[str] = frozenset()) -> int:
    return sum(int(v) for k, v in unfavorable_flags(row).items() if k not in excluded)


def quantile(values: list[float], p: float) -> float:
    """Linear interpolation corresponding to pandas' default quantile behavior."""
    if not values:
        raise ValueError("No observations")
    sorted_values = sorted(values)
    pos = (len(sorted_values) - 1) * p
    low, high = math.floor(pos), math.ceil(pos)
    return sorted_values[low] * (high - pos) + sorted_values[high] * (pos - low) if high != low else sorted_values[low]


def distribution(values: list[int]) -> dict:
    return {
        "n": len(values),
        "median": quantile(values, .5),
        "q1": quantile(values, .25),
        "q3": quantile(values, .75),
        "zero": sum(v == 0 for v in values),
        "one": sum(v == 1 for v in values),
        "ge2": sum(v >= 2 for v in values),
        "ge3": sum(v >= 3 for v in values),
        "ge4": sum(v >= 4 for v in values),
    }


def deduplicate_probable_repeats(rows: list[dict]) -> tuple[list[dict], dict]:
    """Nickname + exact sex/age + weight/height difference <=0.5.

    Build connected components among concordant same-nickname pairs, and keep
    the earliest dated row from each multi-record component. This is not a
    determination of unique personhood.
    """
    by_name: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_name[nickname_key(row["nickname"])].append(row)
    multi = [group for group in by_name.values() if len(group) > 1]
    clusters: list[list[dict]] = []
    removed_ids: set[str] = set()
    for group in by_name.values():
        unseen = set(range(len(group)))
        while unseen:
            start = min(unseen)
            unseen.remove(start)
            component = [start]
            queue = [start]
            while queue:
                i = queue.pop()
                for j in list(unseen):
                    a, b = group[i], group[j]
                    agree = (a["input_gender"] == b["input_gender"]
                             and as_int(a, "input_age") == as_int(b, "input_age")
                             and abs(as_float(a, "input_weight_kg") - as_float(b, "input_weight_kg")) <= .5
                             and abs(as_float(a, "input_height_cm") - as_float(b, "input_height_cm")) <= .5)
                    if agree:
                        unseen.remove(j)
                        component.append(j)
                        queue.append(j)
            if len(component) > 1:
                cluster = sorted((group[i] for i in component),
                                 key=lambda r: (r["created_at"], r["id"]))
                clusters.append(cluster)
                removed_ids.update(r["id"] for r in cluster[1:])
    kept = [r for r in rows if r["id"] not in removed_ids]
    meta = {
        "repeated_nickname_groups": len(multi),
        "repeated_nickname_records": sum(map(len, multi)),
        "repeated_nickname_size_distribution": dict(sorted(Counter(map(len, multi)).items())),
        "probable_repeat_clusters": len(clusters),
        "probable_repeat_records": sum(map(len, clusters)),
        "subsequent_submissions_removed": len(removed_ids),
        "retained_analytical_records": len(kept),
    }
    return kept, meta


FACTORS = {
    "BMI <20 kg/m2": lambda r: bmi(r) < 20,
    "Parental hip fracture": lambda r: flag(r, "input_parent_fracture"),
    "Low-trauma fracture <5 years": has_fracture,
    "Fall in previous year": lambda r: r["input_fall_history"] != "none",
    "Glucocorticoids >3 months": lambda r: flag(r, "input_steroids"),
    "Current smoking": lambda r: flag(r, "input_smoking"),
    "Alcohol >3 drinks/day": lambda r: flag(r, "input_alcohol"),
    "Caffeine >4 cups/day": lambda r: flag(r, "input_caffeine"),
    "Weight-bearing exercise <1 time/week": lambda r: r["input_exercise"] == "less_than_1",
    "Calcium less often than 2-3 times/week": lambda r: r["input_calcium"] == "less_often",
    "Predominantly indoor vitamin D": lambda r: r["input_vitamin_d"] == "indoor",
    "No balance exercise": lambda r: not flag(r, "input_balance_exercise"),
}

FACTOR_VARIANTS = {
    "Original 8-factor count": frozenset(),
    "Excluding glucocorticoids": frozenset({"Glucocorticoids >3 months"}),
    "Excluding balance exercise": frozenset({"No balance exercise"}),
    "Excluding both": frozenset({"Glucocorticoids >3 months", "No balance exercise"}),
}


def cohort_summary(rows: list[dict]) -> dict:
    valid_sex = [r for r in rows if r["input_gender"] in {"Female", "Male"}]
    ages = [as_int(r, "input_age") for r in rows]
    scores = [as_int(r, "final_score") for r in rows]
    return {
        "n": len(rows),
        "female": sum(r["input_gender"] == "Female" for r in rows),
        "male": sum(r["input_gender"] == "Male" for r in rows),
        "missing_sex": len(rows) - len(valid_sex),
        "mean_age": round(mean(ages), 1),
        "sd_age": round(stdev(ages), 1),
        "median_bmi": round(quantile([bmi(r) for r in rows], .5), 1),
        "median_score": quantile(scores, .5),
        "q1_score": quantile(scores, .25),
        "q3_score": quantile(scores, .75),
        "min_score": min(scores),
        "max_score": max(scores),
        "score_categories": dict(Counter(score_category(r) for r in rows)),
        "score_lt95": sum(s < 95 for s in scores),
        "dxa_evaluable": len(valid_sex),
        "dxa_prompt": sum(bool(dxa_prompt(r)) for r in valid_sex),
        "factor_ge2": sum(factor_count(r) >= 2 for r in rows),
        "factor_ge3": sum(factor_count(r) >= 3 for r in rows),
        "selected_factors": {name: sum(bool(fn(r)) for r in rows) for name, fn in FACTORS.items()},
    }


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)


def analyze(rows: list[dict]) -> dict:
    inperiod = [r for r in rows if within_study(r)]
    is_test = lambda r: nickname_key(r["nickname"]) in INTERNAL_TEST_LABELS
    tests = [r for r in inperiod if is_test(r)]
    public_submissions = [r for r in inperiod if not is_test(r)]
    below_adult_age = [r for r in public_submissions if as_int(r, "input_age") < 20]
    primary = [r for r in public_submissions if as_int(r, "input_age") >= 20]
    sensitivity, repeat_meta = deduplicate_probable_repeats(primary)
    eligible_sex = [r for r in primary if r["input_gender"] in {"Female", "Male"}]
    no_dxa = [r for r in eligible_sex if not dxa_prompt(r)]
    dxa_triggered = [r for r in eligible_sex if dxa_prompt(r)]
    below_age = [r for r in dxa_triggered if not age_threshold(r)]
    complete_cases = [r for r in eligible_sex if not menopause_default(r)]
    menopause = [r for r in primary if r["input_gender"] == "Female"
                 and 45 <= as_int(r, "input_age") <= 64]
    comparison = {
        "input_n": len(rows), "outside_study_window": len(rows) - len(inperiod),
        "within_study_window": len(inperiod), "internal_testing_excluded": len(tests),
        "age_below_20_excluded": len(below_adult_age),
        "primary": cohort_summary(primary), "repeat_sensitivity": cohort_summary(sensitivity),
        "repeat_details": repeat_meta,
        "menopause_45_64": dict(Counter(r["input_menopause_before_45"] for r in menopause)),
        "dxa_age_triggered": sum(age_threshold(r) for r in dxa_triggered),
        "dxa_below_age_triggered": len(below_age),
        "dxa_non_age_reasons": dict(Counter(reason for r in below_age for reason in dxa_non_age_reasons(r))),
        "dxa_excluding_menopause_defaults": {"denominator": len(complete_cases),
                                            "triggered": sum(bool(dxa_prompt(r)) for r in complete_cases)},
        "dxa_relaxed_menopause_age": {"denominator": len(eligible_sex),
                                       "triggered": sum(bool(dxa_prompt(r, True)) for r in eligible_sex)},
    }
    def format_pct(n: int, d: int) -> str:
        pct = ((Decimal(n) * Decimal(100)) / Decimal(d)).quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)
        return f"{n}/{d} ({pct}%)"
    age_table, sex_table = [], []
    for factor, fn in FACTORS.items():
        age_row = {"Factor": factor}
        for label in ("20-49", "50-64", "65-69", ">=70"):
            sub = [r for r in primary if age_group(r) == label]
            age_row[label] = format_pct(sum(bool(fn(r)) for r in sub), len(sub))
        age_table.append(age_row)
        sex_row = {"Factor": factor}
        for label in ("Female", "Male"):
            sub = [r for r in primary if r["input_gender"] == label]
            sex_row[label] = format_pct(sum(bool(fn(r)) for r in sub), len(sub))
        sex_table.append(sex_row)
    S4 = []
    for name, omit in FACTOR_VARIANTS.items():
        a = distribution([factor_count(r, omit) for r in primary])
        b = distribution([factor_count(r, omit) for r in no_dxa])
        S4.append({"Definition": name, "Dataset": "Primary N=256", **a})
        S4.append({"Definition": name, "Dataset": "Non-DXA N=160", **b})
    S5 = []
    for key in ("female", "selected_factors", "score_lt95", "dxa_prompt", "factor_ge2", "factor_ge3"):
        if key == "selected_factors":
            for fac in ("Low-trauma fracture <5 years", "Weight-bearing exercise <1 time/week",
                        "Calcium less often than 2-3 times/week", "Predominantly indoor vitamin D",
                        "No balance exercise"):
                S5.append({"Measure": fac, "Primary": comparison["primary"][key][fac],
                           "Repeat sensitivity": comparison["repeat_sensitivity"][key][fac]})
        else:
            S5.append({"Measure": key, "Primary": comparison["primary"][key],
                       "Repeat sensitivity": comparison["repeat_sensitivity"][key]})
    S6 = [
        {"Analysis": "Deployed algorithm", "Evaluable": len(eligible_sex), "Prompt": len(dxa_triggered)},
        {"Analysis": "Exclude menopause defaults", "Evaluable": len(complete_cases),
         "Prompt": sum(bool(dxa_prompt(r)) for r in complete_cases)},
        {"Analysis": "Remove age >50 condition for early menopause", "Evaluable": len(eligible_sex),
         "Prompt": sum(bool(dxa_prompt(r, True)) for r in eligible_sex)},
    ]
    return {"aggregate": comparison, "S3_age": age_table, "S3_sex": sex_table,
            "S4": S4, "S5": S5, "S6": S6}


EXPECTED = {
    "input_n": 304, "outside_study_window": 8, "within_study_window": 296,
    "internal_testing_excluded": 40, "age_below_20_excluded": 0,
    "primary.n": 256, "primary.female": 195, "primary.male": 59,
    "primary.missing_sex": 2, "primary.mean_age": 51.9, "primary.sd_age": 14.0,
    "primary.median_score": 110, "primary.q1_score": 90,
    "primary.q3_score": 120, "primary.min_score": 55, "primary.max_score": 140,
    "primary.score_categories.Excellent": 38,
    "primary.score_categories.Good": 137,
    "primary.score_categories.Needs improvement": 77,
    "primary.score_categories.High risk": 4,
    "primary.dxa_evaluable": 254, "primary.dxa_prompt": 94,
    "primary.factor_ge2": 151, "primary.factor_ge3": 97,
    "repeat_sensitivity.n": 243, "repeat_sensitivity.female": 189,
    "repeat_sensitivity.dxa_evaluable": 241, "repeat_sensitivity.dxa_prompt": 91,
    "repeat_sensitivity.score_lt95": 79,
    "repeat_sensitivity.factor_ge2": 148, "repeat_sensitivity.factor_ge3": 94,
    "repeat_details.repeated_nickname_groups": 18,
    "repeat_details.repeated_nickname_records": 44,
    "repeat_details.probable_repeat_clusters": 8,
    "repeat_details.probable_repeat_records": 21,
    "repeat_details.subsequent_submissions_removed": 13,
    "menopause_45_64.yes": 25, "menopause_45_64.no": 45,
    "menopause_45_64.not_applicable": 28,
    "dxa_age_triggered": 44, "dxa_below_age_triggered": 50,
    "dxa_excluding_menopause_defaults.denominator": 226,
    "dxa_excluding_menopause_defaults.triggered": 93,
    "dxa_relaxed_menopause_age.denominator": 254,
    "dxa_relaxed_menopause_age.triggered": 95,
}


def nested_get(mapping: dict, dotted_key: str):
    val = mapping
    for part in dotted_key.split("."):
        val = val[part]
    return val


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Private full database CSV export")
    parser.add_argument("--output", type=Path, default=Path("aggregate_outputs"),
                        help="Directory for aggregate results; do not use public raw-data folders")
    args = parser.parse_args()
    rows = read_records(args.input)
    outputs = analyze(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "analysis_summary.json").write_text(
        json.dumps(outputs["aggregate"], ensure_ascii=False, indent=2), encoding="utf-8")
    for key, filename in (("S3_age", "table_s3_age.csv"), ("S3_sex", "table_s3_sex.csv"),
                          ("S4", "table_s4_factor_sensitivity.csv"),
                          ("S5", "table_s5_repeat_sensitivity.csv"),
                          ("S6", "table_s6_dxa_sensitivity.csv")):
        write_csv(args.output / filename, outputs[key])
    actual = outputs["aggregate"]
    failures = {key: {"expected": exp, "observed": nested_get(actual, key)}
                for key, exp in EXPECTED.items() if nested_get(actual, key) != exp}
    audit = {"checks": len(EXPECTED), "passed": len(EXPECTED) - len(failures),
             "failed": len(failures), "failures": failures}
    (args.output / "verification_report.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Verification: {audit['passed']}/{audit['checks']} checks passed")
    print("Cohort:", actual["input_n"], "exported ->", actual["within_study_window"],
          "during period ->", actual["primary"]["n"], "eligible ->",
          actual["repeat_sensitivity"]["n"], "repeat sensitivity")
    print("Tables and summary written to:", args.output.resolve())
    if failures:
        raise SystemExit("Verification failed; review aggregate JSON (no individual records included).")


if __name__ == "__main__":
    main()
