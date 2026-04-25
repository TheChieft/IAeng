# Data Dictionary

## Canonical Long Schema

| Column | Type | Description |
| --- | --- | --- |
| COUNTRY | string | Country code (standardized with trim + uppercase). |
| CITY | string | City name (trim + whitespace normalization). |
| ZONE | string | Zone name (trim + whitespace normalization). |
| ZONE_TYPE | string | Zone category when available (metrics table). |
| ZONE_PRIORITIZATION | string | Zone prioritization bucket when available (metrics table). |
| METRIC | string | Metric name from source table. |
| metric_group | string | Optional structural grouping inferred from METRIC text. |
| WEEK_OFFSET | string | Weekly relative offset label: L8W..L0W. |
| week_offset_num | int | Numeric week offset where 0 is current week and 8 is 8 weeks ago. |
| VALUE | float | Numeric metric/order value after coercion. |
| SOURCE_TABLE | string | Origin sheet: RAW_INPUT_METRICS or RAW_ORDERS. |
| is_current_week | bool | True only when WEEK_OFFSET is L0W. |
| has_missing_history | bool | True if any weekly value is missing in the same entity history. |
| _SOURCE_ROW_NUMBER | int | Original Excel row index for traceability. |

## Week Column Mapping Rules

- RAW_INPUT_METRICS weekly columns: L8W_ROLL..L0W_ROLL mapped to canonical L8W..L0W.
- RAW_ORDERS weekly columns: L8W..L0W mapped directly to canonical L8W..L0W.
- If source columns follow LxW_VALUE, they are also mapped to canonical LxW.

## Cleaning Rules

- Conservative string cleaning only: trim and internal whitespace normalization.
- COUNTRY additionally uppercased; CITY/ZONE names are not semantically renamed.
- Exact duplicate rows are removed and counted.
- Non-exact duplicates on logical keys are reported, not silently collapsed.
- Numeric coercion warnings are tracked per weekly canonical column.
