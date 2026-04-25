# Semantic Layer Report — Reto 1
Generated: 2026-04-25T00:24:35.104013

## Semantic Checks
| Check | Status | Detail |
|---|---|---|
| `all_dataset_metrics_in_catalog` | ✓ PASS | dataset=13, catalog=13, missing=set() |
| `no_orphan_metrics_in_catalog` | ✓ PASS | orphans=set() |
| `metric_ids_are_unique` | ✓ PASS | n_ids=13, n_unique=13 |
| `all_metrics_have_direction` | ✓ PASS | all entries have desired_direction field |
| `all_metrics_have_confidence` | ✓ PASS | all entries have direction_confidence field |
| `zone_key_is_unique` | ✓ PASS | n_zone_keys=1244 |
| `peer_groups_have_reliable_groups` | ✓ PASS | reliable_groups=25, total_groups=43 |
| `intents_have_required_params` | ✓ PASS | n_intents=8 |
| `intents_have_examples` | ✓ PASS |  |
| `scale_violations_documented` | ✓ PASS | violations=none |

## Catalog Summary
- Metrics in catalog: 13
- Metrics in dataset: 13
- Direction distribution: {'higher_is_better': 12, 'lower_is_better': 1}
- Direction confidence: {'provisional': 13}

## Peer Group Summary
- Total groups: 43
- Reliable (≥10 zones): 25
- Low confidence: 7
- Too small: 11

## Open Items
- Todas las direcciones de métricas son provisionales — requieren validación de negocio
- Thresholds de detectores en business_rules.yaml pendientes de calibración por métrica
- lead_penetration excluida de rankings y benchmarks hasta clarificar denominador
- turbo_adoption excluida de peer benchmarks por baja cobertura (<70% en algunos grupos)
- Peer groups con low_confidence o too_small producirán alertas low_confidence en NB 30
