# Golden Conversation Flows - Reto 1

| flow_id | user_query | intent | tools | requires_clarification | ideal_response | expected_caveat |
| --- | --- | --- | --- | --- | --- | --- |
| GF01 | Top 5 zonas con mayor Lead Penetration | rank | rank_by_metric | True | rechazar metrica suspendida y proponer alternativa | metric_suspended |
| GF02 | Compara Perfect Orders entre Wealthy y Non Wealthy en Mexico | compare | compare_segments | False | tabla comparativa con delta | direction provisional |
| GF03 | Evolucion de Gross Profit UE en Chapinero | trend | get_trend, render_chart_data | True | pedir ciudad/pais si falta | no forecasting con 9 semanas |
| GF04 | Promedio de Lead Penetration por pais | aggregate | aggregate_metric | True | rechazar uso por suspension | metric_suspended |
| GF05 | Zonas con alto Lead Penetration y bajo Perfect Orders | multivariable_filter | screen_by_conditions | True | pedir reemplazo de metrica suspendida y thresholds | unsupported_condition |
| GF06 | Zonas que mas crecen en orders y que podria explicarlo | hypothesis_request | get_insight_candidates, generate_hypothesis_candidates | False | drivers asociados no causales | association_not_causation |
| GF07 | Y solo en Colombia? | follow_up_scope_refine | reuse_last_tool_with_filter | False | mantener metrica e intent previos filtrando country=CO | preserve prior context |
| GF08 | Muestralo en grafico | follow_up_visualization | render_chart_data | False | transformar ultima respuesta a chart | chart reflects deterministic output |
| GF09 | Que problemas tiene Bogota esta semana? | insight_request | run_insight_detectors | False | top insights por final_rank_score | thresholds provisionales |
| GF10 | Demuestrame que Restaurants SS > ATC CVR causa mas orders | hypothesis_request | generate_hypothesis_candidates | True | rechazar causalidad fuerte, ofrecer evidencia asociativa | no causal claims |