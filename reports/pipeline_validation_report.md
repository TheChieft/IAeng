# Pipeline Validation Report

- Overall status: **PASS**
- Checks passed: 10
- Checks failed: 0

## Check Results

### raw_shapes_match_source
- Status: **PASS**
- Details:
  - RAW_INPUT_METRICS: (12573, 15)
  - RAW_ORDERS: (1242, 13)
  - RAW_SUMMARY: (15, 4)

### metrics_exact_duplicates_real
- Status: **PASS**
- Details:
  - raw_exact_duplicates: 963
  - expected: 963

### dedup_preserves_non_exact_rows
- Status: **PASS**
- Details:
  - raw_unique_rows: 11610
  - metrics_clean_rows: 11610

### weekly_mapping_columns_detected
- Status: **PASS**
- Details:
  - metrics_has_roll_cols: True
  - orders_has_week_cols: True

### numeric_coercion_no_artificial_nans
- Status: **PASS**
- Details:
  - metrics_artificial_nans: {'L8W': 0, 'L7W': 0, 'L6W': 0, 'L5W': 0, 'L4W': 0, 'L3W': 0, 'L2W': 0, 'L1W': 0, 'L0W': 0}
  - orders_artificial_nans: {'L8W': 0, 'L7W': 0, 'L6W': 0, 'L5W': 0, 'L4W': 0, 'L3W': 0, 'L2W': 0, 'L1W': 0, 'L0W': 0}

### wide_to_long_math_and_grain
- Status: **PASS**
- Details:
  - metrics_expected_rows: 104490
  - metrics_actual_rows: 104490
  - orders_expected_rows: 11178
  - orders_actual_rows: 11178
  - metrics_grain_duplicates: 0
  - orders_grain_duplicates: 0

### zone_master_matches_union
- Status: **PASS**
- Details:
  - zone_master_count: 1244
  - union_count: 1244
  - metrics_only: 2
  - orders_only: 264

### coverage_mismatch_warning_real
- Status: **PASS**
- Details:
  - metrics_only: 2
  - orders_only: 264

### processed_outputs_coherent
- Status: **PASS**
- Details:
  - metrics_source_tables: ['RAW_INPUT_METRICS']
  - orders_source_tables: ['RAW_ORDERS']
  - metrics_week_offsets: ['L0W', 'L1W', 'L2W', 'L3W', 'L4W', 'L5W', 'L6W', 'L7W', 'L8W']
  - orders_week_offsets: ['L0W', 'L1W', 'L2W', 'L3W', 'L4W', 'L5W', 'L6W', 'L7W', 'L8W']

### pipeline_end_to_end_no_manual_steps
- Status: **PASS**
- Details:
  - run_pipeline: True
  - return_code: 0
  - stderr_tail: 
