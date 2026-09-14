# Labelling guide

The matcher only proposes pairs. Human labels decide whether a pair really is the same topic,
and they are the only basis for the precision numbers in the write-up.

## Setup

1. Copy `results/pairs_for_labelling.csv` to `results/labels_<yourname>.csv`.
2. Fill the `same_topic` column with `1` or `0`. Do not look at the `jaccard` or `band`
   columns while labelling (hide them in your spreadsheet).
3. Label independently. Do not discuss pairs with the other annotator until both files are done.
4. Run `python analysis/precision.py`.

## Rule

Write **1** when a supervisor would say both titles describe the same research project:
the same independent variable, the same dependent variable, and the same population type.

Write **0** otherwise.

| Situation | Label |
|---|---|
| Identical apart from typos, spacing, plurals or word order | 1 |
| Same topic, different case study organisation, state or school | 1 |
| Same topic, one title adds or drops a year range | 1 |
| Same template, different variable ("effect of hawking on academic performance" vs "effect of drug abuse on academic performance") | 0 |
| Same variables, different population (primary pupils vs undergraduates) | 0 |
| Same subject area but a different question | 0 |
| Too vague to judge | 0, and note it in a `note` column |

## Minimum

Two annotators, all rows. If time is short, both annotators label the same first 120 rows,
because agreement can only be computed on pairs both have labelled.
