# Insight Engine Report - Reto 1

Generado: 2026-04-25T12:38:19.230051

## Resumen
- n_candidates: 12443
- by_category: {'possible_driver': 5311, 'opportunity': 3270, 'peer_gap': 2321, 'persistent_deterioration': 1399, 'anomaly': 142}
- by_detector: {'possible_driver': 5311, 'opportunity': 3270, 'peer_gap': 2321, 'persistent_deterioration': 1399, 'anomaly_point': 142}

## Top candidatos
| insight_id | insight_category | detector_name | display_entity | metric_id | severity_score | confidence_score | final_rank_score | caveats |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INS-000009 | anomaly | anomaly_point | MX | Monterrey | MTY_Apodaca_Huinalá | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000015 | anomaly | anomaly_point | PE | Lima | Comas | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000026 | anomaly | anomaly_point | PE | Lima | La Molina | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000027 | anomaly | anomaly_point | PE | Lima | Chorrillos | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000036 | anomaly | anomaly_point | PE | Lima | San Juan de Miraflores | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000053 | anomaly | anomaly_point | PE | Lima | Campoy | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000057 | anomaly | anomaly_point | PE | Arequipa | Cercado Arequipa | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000065 | anomaly | anomaly_point | PE | Lima | Cono norte | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000068 | anomaly | anomaly_point | PE | Lima | San Juan de Lurigancho | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000069 | anomaly | anomaly_point | PE | Lima | Santa Anita | gross_profit_ue | 1.0 | 0.686375 | 0.7210873125 | direction provisional; validation_status=pending_business_validation; thresholds provisionales |
| INS-000385 | persistent_deterioration | persistent_deterioration | BR | Grande São Paulo | SP - SP - Itaim Bibi | restaurants_ss_atc_cvr | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-000386 | persistent_deterioration | persistent_deterioration | BR | Grande São Paulo | SP - SP - Itaim Bibi | restaurants_sst_ss_cvr | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-000497 | persistent_deterioration | persistent_deterioration | MX | Chihuahua | CH_Centro | restaurants_ss_atc_cvr | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-000547 | persistent_deterioration | persistent_deterioration | MX | Tijuana | TIJ_Centro_Norte | turbo_adoption | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-001028 | persistent_deterioration | persistent_deterioration | MX | Guadalajara | Tonalá | turbo_adoption | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-001111 | persistent_deterioration | persistent_deterioration | BR | Grande São Paulo | SP - SP - Santo Amaro/Jabaquara | mltv_top_verticals_adoption | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-001148 | persistent_deterioration | persistent_deterioration | MX | Cancun | Cun Centro | non_pro_ptc_op | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-001367 | persistent_deterioration | persistent_deterioration | BR | Recife | PE - REC - Zona Norte | mltv_top_verticals_adoption | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-001394 | persistent_deterioration | persistent_deterioration | BR | Grande São Paulo | Jardins/Pinheiros | restaurants_sst_ss_cvr | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |
| INS-001421 | persistent_deterioration | persistent_deterioration | BR | Grande São Paulo | Jardins/Pinheiros | restaurants_ss_atc_cvr | 1.0 | 0.65025 | 0.710845875 | direction provisional; validation_status=pending_business_validation; streak threshold provisional |

## Limites abiertos
- Thresholds provisionales pendientes de calibracion por metrica
- Direction confidence aun provisional en el catalogo
- 9 semanas limitan robustez temporal y de asociaciones
- Peer groups low_confidence requieren interpretacion cautelosa