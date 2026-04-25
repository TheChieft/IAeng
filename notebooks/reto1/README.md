# Reto 1 — Notebooks

## Objetivo
Construir un sistema de inteligencia operacional conversacional sobre métricas semanales por zona.  
El sistema responde preguntas de negocio, detecta anomalías y genera hipótesis — de forma auditable y con incertidumbre explícita.

## Estado actual

| Notebook                        | Estado                              | Bloqueantes                                      |
| ------------------------------- | ----------------------------------- | ------------------------------------------------ |
| `00_reto1_data_prep.ipynb`      | ✓ Completo                          | —                                                |
| `10_reto1_eda.ipynb`            | ✓ Completo                          | —                                                |
| `20_reto1_semantic_layer.ipynb` | ✓ Completo (iteración 2, 29 celdas) | `desired_direction` pendiente validación negocio |
| `30_reto1_insight_engine.ipynb` | ✓ Completo (iteración 1 funcional)  | thresholds y direcciones aún provisionales       |
| `40_reto1_chatbot_design.ipynb` | Placeholder                         | Integrar consumo de `insight_candidates.*`       |

## Flujo de notebooks

```
00_reto1_data_prep
    → data/interim/*.parquet (wide, limpios)
    → data/processed/*.parquet (long, zone_master)
    → reports/reto1/pipeline_validation.{json,md}

10_reto1_eda
    → hallazgos de distribución, outliers, correlaciones
    → insumo conceptual para NB 20

20_reto1_semantic_layer
    → config/metrics.yaml  (ya existía, NB 20 lo valida y enriquece)
    → config/business_rules.yaml  (ídem)
    → config/question_types.yaml  (ídem)
    → reports/reto1/semantic_layer_report.{json,md}

30_reto1_insight_engine
    → detectors: anomaly_point, persistent_deterioration, peer_gap, opportunity, possible_driver
    → reports/reto1/insight_candidates.{parquet,csv}
    → reports/reto1/insight_engine_report.{json,md}
    → reports/reto1/insight_samples.md

40_reto1_chatbot_design  [pendiente]
    → intent classifier → semantic function → narrative renderer
    → bot demo interactivo
```

## Qué hace cada notebook

### `00_reto1_data_prep.ipynb`
Carga el Excel fuente, limpia, detecta duplicados, transforma wide → long, construye zone_master y valida 10 checks estructurales. Es el único notebook que toca `data/raw/`.

### `10_reto1_eda.ipynb`
EDA orientado a diseño de sistema. Audita dimensiones categóricas, distribuciones por métrica, outliers, correlaciones Spearman WoW, cobertura temporal y mismatch de zonas.

### `20_reto1_semantic_layer.ipynb`
Traduce hallazgos del EDA en artefactos gobernados: catálogo de métricas con capacidades analíticas + estado de validación, llave lógica de zona, peer groups evaluados con reglas de fallback, taxonomía de intents con unsupported_cases, reglas de lenguaje, 13 semantic checks (PASS/WARN/FAIL). Exporta contrato completo a CSV/MD y checks a JSON/MD.

### `30_reto1_insight_engine.ipynb`
Implementa el backend analítico gobernado del sistema de insights. Incluye 5 detectores trazables (anomalía puntual, deterioro persistente, brecha peer, oportunidad y posibles drivers asociados), scoring común con penalizaciones de gobernanza, narrativa templada y validación de edge cases semánticos.

### `40_reto1_chatbot_design.ipynb` _(placeholder)_
Implementará el flujo completo: intent → función semántica → narrativa auditada. Usará los intents de `config/question_types.yaml` y las reglas de lenguaje de `config/business_rules.yaml`.

## Artefactos generados

| Artefacto                                     | Generado por | Descripción                                                  |
| --------------------------------------------- | ------------ | ------------------------------------------------------------ |
| `data/interim/metrics_raw_cleaned.parquet`    | NB 00        | Métricas limpias, wide                                       |
| `data/interim/orders_raw_cleaned.parquet`     | NB 00        | Órdenes limpias, wide                                        |
| `data/processed/metrics_long.parquet`         | NB 00        | Métricas long, grano (COUNTRY,CITY,ZONE,METRIC,WEEK_OFFSET)  |
| `data/processed/orders_long.parquet`          | NB 00        | Órdenes long, mismo grano                                    |
| `data/processed/zone_master.parquet`          | NB 00        | Cobertura cruzada de zonas                                   |
| `reports/reto1/pipeline_validation.json`      | NB 00        | 10 checks estructurales                                      |
| `reports/reto1/semantic_layer_report.json`    | NB 20        | Resumen catálogo + peer groups + intents                     |
| `reports/reto1/semantic_contract_summary.csv` | NB 20        | Contrato completo: 13 métricas × 17 campos                   |
| `reports/reto1/semantic_contract_summary.md`  | NB 20        | Versión markdown del contrato                                |
| `reports/reto1/semantic_checks.json`          | NB 20        | 13 checks PASS/WARN/FAIL con implicación                     |
| `reports/reto1/semantic_checks.md`            | NB 20        | Versión markdown de los checks                               |
| `reports/reto1/insight_candidates.parquet`    | NB 30        | Tabla maestra de candidatos de insight                       |
| `reports/reto1/insight_candidates.csv`        | NB 30        | Versión tabular para revisión manual y QA                    |
| `reports/reto1/insight_engine_report.json`    | NB 30        | Resumen técnico del motor (scoring, penalizaciones, límites) |
| `reports/reto1/insight_engine_report.md`      | NB 30        | Reporte legible de resultados y top candidatos               |
| `reports/reto1/insight_samples.md`            | NB 30        | Ejemplos de narrativa templada por categoría                 |

## Decisiones de diseño clave

- **Sin imputación:** faltantes propagados como NaN con flag `has_missing_history`.
- **Sin fechas calendario:** solo offsets relativos `L8W`–`L0W`.
- **ZONE_KEY = COUNTRY|CITY|ZONE:** ZONE sola no es identificador único.
- **Peer group primario:** `(COUNTRY, ZONE_TYPE, ZONE_PRIORITIZATION)`, mínimo 10 zonas.
- **264 zonas ONLY_ORDERS:** mismatch estructural documentado, no error del pipeline.
- **Todas las direcciones son provisionales:** ninguna validada con negocio aún.

## Qué sigue

1. Calibrar thresholds en `config/business_rules.yaml` por métrica.
2. Validar `desired_direction` de las 13 métricas con el área de negocio.
3. Calibrar thresholds por métrica de NB 30 con validación de negocio.
4. Implementar NB 40 (chatbot) consumiendo `insight_candidates.*` y reglas de lenguaje.

## Referencias

- `docs/working_notes/reto1_data_prep_decisions.md` — decisiones técnicas del pipeline
- `docs/working_notes/reto1_bitacora.md` — historial de iteraciones
- `config/metrics.yaml`, `config/business_rules.yaml`, `config/question_types.yaml` — contratos semánticos
