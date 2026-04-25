# Reto 1 Chatbot Contract

Generated at: 2026-04-25T14:09:15.306338+00:00

## Conversational Architecture
- LLM role: planner + orchestrator + controlled renderer
- Deterministic tools role: all calculations and retrievals
- Insight engine role: ranked insight candidates and evidence

## Intent Operational Map
| intent | display_name | support_level | required_params_text | optional_params_text | future_function_name | requires_visualization | direct_answer_possible | requires_clarification_by_default | requires_insight_engine | hypothesis_mode |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| query | Consulta directa | bien | metric_id, zone_key | week_offset | get_metric_value(metric_id, zone_key, week_offset) | True | True | False | False | False |
| aggregate | Agregación | bien | metric_id, group_by | week_offset, aggregation_func, filter_condition | aggregate_metric(metric_id, group_by, week_offset, agg_func, filters) | True | False | False | False | False |
| rank | Ranking | bien | metric_id, entity_level | week_offset, n, direction, filter_condition | rank_by_metric(metric_id, entity_level, week_offset, n, direction, filters) | True | False | False | False | False |
| trend | Tendencia temporal | bien | metric_id, zone_key | offsets | get_trend(metric_id, zone_key, offsets) | True | False | False | False | False |
| compare | Comparación entre segmentos | bien | metric_id, segment_a, segment_b | week_offset | compare_segments(metric_id, segment_a, segment_b, week_offset) | True | False | False | False | False |
| multivariable_filter | Filtro multivariable | parcial | conditions | week_offset, entity_level | screen_by_conditions(conditions, week_offset, entity_level) | True | False | True | False | False |
| insight_request | Request de insight automático | parcial | zone_key | metrics, detectors, week_offset | run_insight_detectors(zone_key, metrics, detectors, week_offset) | True | False | False | True | False |
| hypothesis_request | Hipótesis explicativa | parcial | outcome_metric, zone_key | candidate_metrics, week_offset | generate_hypothesis(outcome_metric, zone_key, candidate_metrics, week_offset) | True | False | True | False | True |

## Clarification Rules
| trigger | why | good_clarification |
| --- | --- | --- |
| metrica_ambigua | No se puede ejecutar funcion sin metrica canonica | Que metrica quieres analizar? Ej: Perfect Orders o Gross Profit UE. |
| entidad_ambigua | ZONE no es unica sin COUNTRY y CITY | Te refieres a que pais y ciudad para esa zona? |
| comparacion_invalida | NB20 define pares no comparables | Esa comparacion no es valida. Quieres comparar dentro del mismo pais y tipo de zona? |
| peer_group_debil | Benchmark con n pequeno es fragil | El peer group es pequeno. Continuo con caveat o prefieres ampliar el alcance? |
| causalidad_fuerte | El sistema solo soporta asociaciones no causales | Puedo darte posibles drivers asociados, no causalidad confirmada. Continuo? |
| fuera_de_alcance | Intent no cubierto por funciones deterministicas | No puedo responder eso con el contrato actual. Te propongo reformular en formato ranking, tendencia, comparacion o insight. |
| metrica_suspendida | validation_status suspendida impide uso analitico confiable | Esa metrica esta suspendida temporalmente. Quieres usar una metrica alternativa? |

## Tool Contract
| tool | input_schema | output_schema | errors | chatbot_caveat |
| --- | --- | --- | --- | --- |
| get_metric_value | metric_id, entity_scope, week_offset | value, metadata, caveats | metric_not_found|entity_not_found|insufficient_data | direction/validation caveats |
| aggregate_metric | metric_id, group_by, filters, week_offset, agg_func | rows[group, value, n, coverage] | invalid_group_by|unsupported_metric | coverage and excluded zones |
| rank_by_metric | metric_id, entity_level, n, direction, filters | ranked_rows | metric_not_rankable|direction_mismatch | invert when lower_is_better |
| get_trend | metric_id, entity_scope, window | series[value,wow] | insufficient_history | no complex forecasting with 9 weeks |
| compare_segments | metric_id, segment_a, segment_b, week_offset | comparison_table + delta | invalid_comparison | respect not_comparable rules |
| screen_by_conditions | conditions[], entity_level, week_offset | matching_entities | missing_threshold|unsupported_condition | thresholds must be explicit |
| run_insight_detectors | entity_scope, metrics, detectors, week_offset | insight_candidates[] | detector_not_available | provisional thresholds caveat |
| get_insight_candidates | filters, sort, limit | insight_table | empty_result | report confidence and caveats |
| generate_hypothesis_candidates | target_metric, entity_scope, candidate_metrics | association_table | insufficient_points|target_not_supported | association not causation |
| render_chart_data | intent, data_payload, chart_pref | chart_spec | chart_not_supported | chart is view, not evidence source |

## Response Contract
| intent | short_answer | evidence | scope | viz | caveat | next_questions |
| --- | --- | --- | --- | --- | --- | --- |
| query | valor puntual | valor + semana + fuente | entity + metric + offset | kpi_card | validation/direction | trend|compare |
| aggregate | estadistico principal | tabla agregada + n | group_by + filtros | bar_chart | coverage/missing | rank|segment drill-down |
| rank | top/bottom n | tabla rankeada | entity_level + n + filtros | ranked_table | lower_is_better + elegibilidad | why this zone?|trend |
| trend | direccion reciente | serie + wow | entity + ventana | line_chart | 9 weeks no forecasting | insight_request |
| compare | delta entre segmentos | tabla comparativa + n | segment_a vs segment_b | side_by_side_bar | comparabilidad | rank within segment |
| insight_request | top hallazgos | insight_candidates ordenados | entity/filtro + detectores | alert_cards | thresholds provisionales | show evidence|actions |
| hypothesis_request | posibles drivers | asociaciones y caveats | target_metric + entidad | correlation_table | no causalidad | validate with ops context |