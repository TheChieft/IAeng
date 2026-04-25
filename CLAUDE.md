# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Two-reto analytics challenge built on Rappi dummy data:
- **Reto 1 — Operational Intelligence**: data already provided; goal is analytical model + product (conversational bot + auto-insights over weekly operational metrics by zone).
- **Reto 2 — Competitive Intelligence**: starts from data acquisition of public competitor data to support pricing/ops/strategy decisions by zone.

Raw source: one Excel workbook (`data/raw/*.xlsx`) with three sheets: `RAW_INPUT_METRICS`, `RAW_ORDERS`, `RAW_SUMMARY`.

## Running the pipeline

The primary entry point is the notebook. Scripts are gone — all logic is in `notebooks/reto1/00_reto1_data_prep.ipynb`.

```bash
# Run full pipeline (Jupyter)
jupyter notebook notebooks/reto1/00_reto1_data_prep.ipynb

# Or with nbconvert for headless execution
jupyter nbconvert --to notebook --execute notebooks/reto1/00_reto1_data_prep.ipynb --output notebooks/reto1/00_reto1_data_prep.ipynb
```

## Notebook sequence (Reto 1)

All notebooks live in `notebooks/reto1/`.

| Notebook | Purpose |
|---|---|
| `00_reto1_data_prep.ipynb` | Load raw → clean → long → zone_master → validate → export parquets |
| `10_reto1_eda.ipynb` | EDA formal oriented to system design |
| `20_reto1_semantic_layer.ipynb` | Metric catalog, entity keys, peer groups, intent taxonomy, 10 semantic checks |
| `30_reto1_insight_engine.ipynb` | Transparent detectors: WoW, streaks, peer deviation, robust z (placeholder) |
| `40_reto1_chatbot_design.ipynb` | Bot architecture: intent → function → narrative (placeholder) |

## Directory structure

```
data/raw/           # immutable source Excel
data/interim/       # cleaned wide tables (pre-melt): metrics_raw_cleaned, orders_raw_cleaned
data/processed/     # canonical long tables + zone_master (source of truth for analysis)
config/             # semantic contracts: metrics.yaml, business_rules.yaml, question_types.yaml
docs/retos/         # case PDFs + problem statements
docs/research/      # deep research reports
docs/working_notes/ # technical bitacora + data prep decisions
docs/architecture/  # system design (in progress)
notebooks/reto1/    # Reto 1 notebooks + README
notebooks/reto2/    # Reto 2 notebooks + README (not started)
reports/reto1/      # auditable output reports (md + json)
src/helpers/        # paths.py + io.py only — no business logic
```

## Architecture

### Data flow

```
data/raw/*.xlsx
  └─ notebooks/reto1/00_reto1_data_prep.ipynb
       ├─ clean_sheet()          → data/interim/metrics_raw_cleaned.parquet
       ├─ clean_sheet()          → data/interim/orders_raw_cleaned.parquet
       ├─ make_long()            → data/processed/metrics_long.parquet
       ├─ make_long()            → data/processed/orders_long.parquet
       └─ zone_master build      → data/processed/zone_master.parquet
  └─ notebooks/reto1/20_reto1_semantic_layer.ipynb
       └─ validates config/*.yaml  → reports/reto1/semantic_layer_report.{json,md}
```

### Key design decisions

- **Parquet-only** in `interim/` and `processed/`. CSV not persisted.
- **No imputation** of missing values. Propagated via `has_missing_history` flag.
- **No calendar dates.** Only relative weekly offsets `L8W`–`L0W`.
- **Conservative dedup:** exact duplicates only. 963 removed from `RAW_INPUT_METRICS`, 0 from `RAW_ORDERS`.
- **Zone coverage mismatch is structural:** 264 zones in orders without metrics. `zone_master` documents it.

### Long table grain

`(COUNTRY, CITY, ZONE, METRIC, WEEK_OFFSET)` — must be unique. Verified by pipeline validation check `grain_unique_in_long_tables`.

### src/helpers

Minimal shared utilities only:
- `paths.py`: `get_paths()`, `find_root()`, `default_excel()`
- `io.py`: `load_sheet()`, `detect_week_columns()`, `coerce_numeric()`, `write_parquet()`

Import from notebooks: `sys.path.insert(0, str(ROOT / 'src'))` then `from helpers.paths import ...`

## Pipeline validation (10 checks)

All must PASS before using artifacts downstream:

| Check | What it verifies |
|---|---|
| `raw_shapes_match_source` | Raw sheet shapes unchanged |
| `metrics_exact_dupes_963` | Exactly 963 exact dupes in raw metrics |
| `orders_no_exact_dupes` | Zero dupes in raw orders |
| `week_columns_detected` | ROLL/non-ROLL columns detected correctly |
| `no_artificial_nans_from_coercion` | No NaNs introduced by numeric coercion |
| `wide_to_long_row_math` | Row count = clean_rows × 9 |
| `grain_unique_in_long_tables` | No duplicate grain keys |
| `zone_master_is_union` | zone_master = union of metrics+orders zones |
| `coverage_mismatch_is_real` | Coverage gap between tables exists (expected) |
| `processed_outputs_coherent` | SOURCE_TABLE tags and WEEK_OFFSET values correct |

## Semantic layer (config/)

Three YAML files define the semantic contract between data and the insight engine / chatbot:
- `config/metrics.yaml` — 13 metrics: scale, desired_direction (all `provisional`), outlier_risk
- `config/business_rules.yaml` — entity keys, peer groups, detector thresholds, language rules
- `config/question_types.yaml` — 7 intents with required_params, future_function, examples

Key constraints:
- `ZONE_KEY = COUNTRY|CITY|ZONE` — ZONE alone is not unique
- Primary peer group: `(COUNTRY, ZONE_TYPE, ZONE_PRIORITIZATION)`, min 10 zones
- `lead_penetration`: excluded from rankings/benchmarks (outlier max=393.9)
- `turbo_adoption`: excluded from peer benchmarks (coverage <70% in some groups)
- `restaurants_markdowns_gmv`: only `lower_is_better` metric — ranking must invert direction

## Open items

- `30_reto1_insight_engine.ipynb` — detector thresholds not calibrated per metric.
- `40_reto1_chatbot_design.ipynb` — bot architecture not implemented.
- All `desired_direction` values are `provisional` — need business validation before use in narrative.
- Reto 2 pipeline not started.
