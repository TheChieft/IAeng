# Reto 1 - Bitácora Técnica y README Operativo

## 1) Objetivo del reto

Construir una base de datos operativa, limpia y auditable para el caso "Sistema de Análisis Inteligente para Operaciones Rappi", como fundamento para:

1. Un bot conversacional sobre métricas operativas.
2. Un sistema de insights automáticos.

## 2) Pregunta de negocio del reto

Cómo estructurar y preparar datos semanales por zona para habilitar análisis robusto posterior sin introducir sesgos por problemas de calidad o cobertura.

## 3) Artefactos que existen hoy

### Código de preparación

1. [src/data_prep/load_raw_data.py](src/data_prep/load_raw_data.py)
2. [src/data_prep/clean_metrics.py](src/data_prep/clean_metrics.py)
3. [src/data_prep/clean_orders.py](src/data_prep/clean_orders.py)
4. [src/data_prep/build_long_tables.py](src/data_prep/build_long_tables.py)
5. [src/data_prep/build_zone_master.py](src/data_prep/build_zone_master.py)
6. [src/data_prep/run_initial_data_profile.py](src/data_prep/run_initial_data_profile.py)
7. [src/data_prep/validate_pipeline.py](src/data_prep/validate_pipeline.py)

### Código de análisis

1. [notebooks/reto1_eda.ipynb](notebooks/reto1_eda.ipynb)

### Datos

1. Fuente cruda: [data/raw/Sistema de Análisis Inteligente para Operaciones Rappi - Dummy Data (1).xlsx](data/raw/Sistema%20de%20An%C3%A1lisis%20Inteligente%20para%20Operaciones%20Rappi%20-%20Dummy%20Data%20%281%29.xlsx)
2. Procesados (source of truth):
   - [data/processed/metrics_raw_cleaned.parquet](data/processed/metrics_raw_cleaned.parquet)
   - [data/processed/orders_raw_cleaned.parquet](data/processed/orders_raw_cleaned.parquet)
   - [data/processed/metrics_long.parquet](data/processed/metrics_long.parquet)
   - [data/processed/orders_long.parquet](data/processed/orders_long.parquet)
   - [data/processed/zone_master.parquet](data/processed/zone_master.parquet)

### Reportes

1. [reports/raw_schema_summary.json](reports/raw_schema_summary.json)
2. [reports/data_quality_report.md](reports/data_quality_report.md)
3. [reports/data_quality_report.json](reports/data_quality_report.json)
4. [reports/data_dictionary.md](reports/data_dictionary.md)
5. [reports/pipeline_validation_report.md](reports/pipeline_validation_report.md)
6. [reports/pipeline_validation_report.json](reports/pipeline_validation_report.json)

## 4) Qué se hizo en esta primera fase de data prep

1. Carga de RAW_INPUT_METRICS, RAW_ORDERS y RAW_SUMMARY.
2. Perfilado inicial de shapes, faltantes y duplicados exactos.
3. Estandarización de columnas semanales (ROLL y no-ROLL) a canónico L8W..L0W.
4. Dedupe exacto conservador en métricas (963 filas removidas) y none en órdenes.
5. Normalización de texto (trim + espacios), uppercase solo en COUNTRY.
6. Conversión numérica de semanas con control de coerción.
7. Transformación wide -> long en métricas y órdenes.
8. Construcción de zone_master para cobertura cruzada.
9. Reportes de calidad y diccionario.
10. Validación formal en 10 checks con resultado PASS.

## 5) Decisiones técnicas tomadas

1. Política de outputs: Parquet-only en [data/processed](data/processed) como formato principal.
2. CSV en processed pasa a ser derivado opcional bajo demanda, no persistido por defecto.
3. Duplicado exacto definido sobre columnas originales de cada hoja (no sobre columnas auxiliares).
4. No imputación de faltantes en fase de preparación.
5. No colapso automático de duplicados lógicos ambiguos.
6. Sin fechas calendario; solo offsets semanales relativos.

## 6) Problemas que aparecieron

1. Inconsistencia de nomenclatura semanal entre documento del caso y archivo real.
2. Duplicados exactos relevantes en RAW_INPUT_METRICS.
3. Cobertura de zonas no idéntica entre métricas y órdenes.
4. Faltantes históricos en columnas semanales.

## 7) Qué se corrigió

1. Mapping semanal unificado con regex robusto para ROLL/VALUE/no-sufijo.
2. Lógica de deduplicación ajustada para no contaminarse con _SOURCE_ROW_NUMBER.
3. Validación matemática wide -> long y validación de grano sin duplicados.
4. Limpieza de repo: eliminación de CSV redundantes y cachés técnicas.
5. Generación de validación formal reproducible en reporte JSON + Markdown.

## 8) Qué queda pendiente

1. Definir catálogo oficial de métricas (unidad y orientación).
2. Definir catálogo maestro de zonas/cobertura esperada por ciudad.
3. Agregar tests automáticos de contrato de esquema y unicidad de grano en CI.
4. Decidir tratamiento analítico de zonas sin match entre tablas.
5. Definir estrategia de análisis para series con historia incompleta.
6. Versionar outputs de la capa semántica y contrato de funciones para bot.

## 9) Próximos pasos

1. Integrar tests de validación como paso obligatorio antes de EDA.
2. Revisar outliers y anomalías por métrica con guía de negocio.
3. Construir capa de modelado analítico para consultas y agregaciones repetibles.
4. Iniciar EDA formal sobre tablas long con reglas de cobertura explícitas.

## 10) Historial cronológico breve

1. Iteración 1:
   - Se construyó pipeline base de carga, limpieza, long, zone_master y reportes.
2. Iteración 2:
   - Se implementó validación formal del pipeline (10 checks, PASS).
   - Se adoptó política Parquet-only para processed.
   - Se limpió ruido de repo (CSV redundantes y __pycache__).
   - Se consolidó documentación de decisiones y bitácora.
3. Iteración 3:
   - Se creó EDA formal en [notebooks/reto1_eda.ipynb](notebooks/reto1_eda.ipynb).
   - Se validó estructura para capas futuras: semántica, benchmark por peers e insight engine.
   - Se documentaron detectores transparentes iniciales (WoW, rachas, desviación vs peer median, robust z-score).
   - Se dejó explícito el límite metodológico: hipótesis explicativas no equivalen a causalidad.

## Estructura final recomendada del repo

1. [data/raw](data/raw): fuentes de entrada inmutables del reto.
2. [data/processed](data/processed): únicamente datasets curados en Parquet (source of truth).
3. [src/data_prep](src/data_prep): scripts modulares de preparación y validación.
4. [reports](reports): evidencia auditable (perfilado, calidad, validación).
5. [docs](docs): contexto del reto, decisiones, bitácora y material de continuidad.

## Contexto teórico e investigación de diseño del sistema - pendiente de integración

Sección reservada para integrar posteriormente la investigación amplia del reto 1.
No se incorpora contenido en esta iteración.

---

## Iteración 5 — 2026-04-25: Reorganización, capa semántica y gobernanza

### Cambios estructurales

- Notebooks movidos a subdirectorios: `notebooks/reto1/` y `notebooks/reto2/`
- Notebook 00 renombrado: `00_data_prep_common.ipynb` → `00_reto1_data_prep.ipynb`
- Notebook 10 renombrado: `reto1_eda.ipynb` → `10_reto1_eda.ipynb`
- Creados READMEs en `notebooks/reto1/` y `notebooks/reto2/`
- `docs/working_notes/reto1_data_prep_decisions.md` reescrito: removidas referencias a `src/data_prep/` (eliminado en iter. 4), actualizado con estructura vigente
- Limpieza de reportes redundantes en `reports/reto1/`

### Archivos de configuración creados

| Archivo                      | Contenido                                                                 |
| ---------------------------- | ------------------------------------------------------------------------- |
| `config/metrics.yaml`        | Catálogo de 13 métricas: escala, dirección, confianza, riesgo de outlier  |
| `config/business_rules.yaml` | Entidades, peer groups, reglas temporales, detectores, reglas de lenguaje |
| `config/question_types.yaml` | 7 intents del sistema con parámetros, funciones futuras y ejemplos        |

### Notebook 20 — Semantic Layer (primera iteración real)

`notebooks/reto1/20_reto1_semantic_layer.ipynb` implementado con:
- Carga y validación de los 3 YAMLs de configuración
- Catálogo enriquecido con estadísticas del dataset (min, mediana, max, flags de violación de escala)
- Matriz de capacidades analíticas por métrica
- Prueba empírica de ambigüedad de ZONE sola → llave lógica `(COUNTRY, CITY, ZONE)`
- Evaluación de peer groups: distribución por nivel de confianza (reliable / low_confidence / too_small)
- Visualización de taxonomía de intents y reglas de lenguaje
- 10 semantic contract checks (todos deben PASS antes de usar NB 30/40)
- Export: `reports/reto1/semantic_layer_report.{json,md}`

### Decisiones clave de esta iteración

- `ZONE_KEY = COUNTRY|CITY|ZONE` — materializado en zone_master
- Peer group primario confirmado: `(COUNTRY, ZONE_TYPE, ZONE_PRIORITIZATION)`
- Todas las `desired_direction` permanecen como `provisional` — sin validación de negocio aún
- `lead_penetration` excluida de rankings y benchmarks (outlier extremo 393.9)
- `turbo_adoption` excluida de peer benchmarks (cobertura <70% en algunos grupos)

### Qué habilita para NB 30

NB 30 puede ahora leer reglas de `config/business_rules.yaml` para los 4 detectores:
`wow_delta`, `decline_streak`, `vs_peer_median`, `robust_z` — con thresholds provisionales.

---

## Iteración 6 — 2026-04-25: Fortalecimiento del contrato semántico (NB 20 v2)

### Cambios en NB 20

NB 20 pasó de 22 a 29 celdas. No fue rehecho — se agregaron 7 celdas nuevas y se reforzó 1.

| Sección nueva                            | Qué hace                                                                                        |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `nb20-s2b` — Contrato semántico completo | Tabla unificada: capabilities + validation_status + outlier_risk por métrica. Export CSV + MD   |
| `nb20-s5b` — Peer group operativo        | Ejemplo real: zona → peer group → tamaño → confianza. Reglas de fallback. Lista "no comparable" |
| `nb20-s6b` — Intents operativos          | Tabla de intents con unsupported_cases, default_visualization, output_shape                     |
| `nb20-s9-checks` (reemplazado)           | 13 checks con nivel PASS/WARN/FAIL + implicación. Export semantic_checks.json + .md             |
| `nb20-s9b` — Decisiones abiertas         | Tabla: cerradas vs abiertas. Riesgos para NB 30. Mitigación propuesta                           |

### Cambios en archivos de configuración

**`config/metrics.yaml`** — 3 campos nuevos por métrica:
- `validation_status`: `pending_business_validation` (12 métricas) o `suspended_pending_definition` (lead_penetration)
- `validation_reason`: por qué la dirección es provisional y cuál es el riesgo específico
- `risk_if_wrong`: consecuencia concreta si la dirección declarada es incorrecta

**`config/question_types.yaml`** — 3 campos nuevos por intent:
- `unsupported_cases`: lista explícita de qué no puede manejar cada intent
- `default_visualization`: tipo de visualización por defecto
- `default_output_shape`: estructura esperada del output

**`config/business_rules.yaml`** — 2 secciones nuevas en `peer_groups`:
- `fallback_behavior`: qué hacer cuando grupo too_small, low_confidence, o no hay grupo
- `not_comparable`: lista explícita de comparaciones inválidas

### Nuevos artefactos generados por NB 20

| Artefacto                                     | Descripción                                       |
| --------------------------------------------- | ------------------------------------------------- |
| `reports/reto1/semantic_contract_summary.csv` | Tabla completa: 13 métricas × 17 campos           |
| `reports/reto1/semantic_contract_summary.md`  | Versión markdown legible para revisión humana     |
| `reports/reto1/semantic_checks.json`          | 13 checks con status PASS/WARN/FAIL + implicación |
| `reports/reto1/semantic_checks.md`            | Versión markdown de los checks                    |

### Decisiones semánticas cerradas (usables en NB 30)

- ZONE_KEY = COUNTRY|CITY|ZONE (probado empíricamente)
- Peer group primario: (COUNTRY, ZONE_TYPE, ZONE_PRIORITIZATION)
- `lead_penetration` excluida de rankings y benchmarks
- `turbo_adoption` excluida de peer benchmarks
- `restaurants_markdowns_gmv` es lower_is_better — ranking debe invertir dirección

### Decisiones aún abiertas (antes de usar NB 30 en producción)

- Validar `desired_direction` de las 13 métricas con área de negocio (todas son `provisional`)
- Calibrar `alert_threshold_pct` del detector wow_delta (actualmente 10%)
- Calibrar `min_weeks_for_alert` del decline_streak (actualmente 3)
- Calibrar `anomaly_threshold` del robust_z (actualmente 2.5)
- Clarificar denominador de `lead_penetration`
- Definir si `turbo_adoption` NaN = no-disponible o adopción cero

---

## Iteración 7 — 2026-04-25: Implementación inicial del Insight Engine (NB 30)

### Cambios principales en `notebooks/reto1/30_reto1_insight_engine.ipynb`

Se construyó una primera versión funcional del backend analítico de insights, gobernado por NB20.

Secciones implementadas:
1. Setup y contexto del motor.
2. Carga y validación de inputs gobernados (configs + semantic checks + datasets).
3. Marco metodológico de detectores con límites explícitos.
4. Detector `anomaly_point` (modified z-score + WoW + materialidad).
5. Detector `persistent_deterioration` (rachas de empeoramiento).
6. Detector `peer_gap` (brecha vs mediana de peer group, con confianza del grupo).
7. Detector `opportunity` (mejora consistente y/o outperforming defendible).
8. Módulo `possible_driver` (asociación Spearman WoW por zona, no causal).
9. Capa común de scoring + penalizaciones de gobernanza.
10. Normalización a tabla maestra única de insights.
11. Narrativa templada por categoría (sin LLM libre).
12. Exportes técnicos y de muestras.
13. Validación interna con casos positivos/negativos y edge cases.

### Detectores implementados

- `anomaly_point`
- `persistent_deterioration`
- `peer_gap`
- `opportunity`
- `possible_driver`

### Reglas de gobernanza aplicadas

- Exclusión de `lead_penetration` (`suspended_pending_definition`) del motor.
- Exclusión de `turbo_adoption` de benchmarks peer.
- Respeto de dirección invertida en `restaurants_markdowns_gmv` (`lower_is_better`).
- Advertencia/caveat obligatoria para `direction_confidence=provisional`.
- Penalización de score para `validation_status=pending_business_validation`.
- No benchmark para peer groups `too_small`; `low_confidence` penalizado explícitamente.

### Scoring definido (provisional)

- `severity_score`: intensidad de señal del detector.
- `confidence_score`: calidad de evidencia + penalizaciones semánticas/peer.
- `business_priority_score`: mapeo desde `ZONE_PRIORITIZATION`.
- `final_rank_score`:
   - pesos base: severity 0.45, confidence 0.35, business priority 0.20.
   - penalizaciones multiplicativas:
      - direction provisional: 0.90
      - validation pending business: 0.90
      - peer low confidence: 0.85

### Artefactos nuevos generados

- `reports/reto1/insight_candidates.parquet`
- `reports/reto1/insight_candidates.csv`
- `reports/reto1/insight_engine_report.md`
- `reports/reto1/insight_engine_report.json`
- `reports/reto1/insight_samples.md`

### Riesgos y límites abiertos

1. Los thresholds de detectores siguen provisionales y requieren calibración por métrica.
2. El histórico de 9 semanas limita robustez de persistencia y asociaciones.
3. `desired_direction` sigue pendiente de confirmación de negocio para producción.
4. La categoría `possible_driver` debe tratarse como priorización exploratoria, no causalidad.

### Qué habilita para NB40

- Un contrato de salida único (`insight_candidates.*`) para que el chatbot consuma hallazgos.
- Narrativas base controladas por plantilla y caveats semánticos.
- Priorización cuantitativa reproducible para ordenar respuestas del bot.

---

## Iteración 8 — 2026-04-25: Diseño conversacional del chatbot (NB 40)

### Cambios principales en `notebooks/reto1/40_reto1_chatbot_design.ipynb`

Se implementó el diseño completo de la capa conversacional/orquestadora, sin duplicar cálculo analítico de NB20/NB30.

Secciones diseñadas:
1. Setup y contexto de la capa conversacional.
2. Arquitectura propuesta (qué hace y qué no hace el chatbot).
3. Catálogo operativo de intents mapeado a comportamiento conversacional.
4. Planner estructurado con schema explícito de ejecución.
5. Reglas de clarificación para evitar supuestos peligrosos.
6. Gestión de contexto conversacional mínima (state object).
7. Contrato de herramientas determinísticas (inputs/outputs/errores/caveats).
8. Contrato de respuesta del chatbot (estructura fija de salida).
9. Reglas de lenguaje y seguridad analítica (no causalidad, incertidumbre, peer weak).
10. UX conversacional propuesta (componentes y wireframe lógico).
11. Golden conversation flows (10 flujos).
12. Framework de evaluación conversacional.
13. Plan de implementación a app.
14. Exportes de documentación técnica.

### Arquitectura conversacional definida

- El chatbot funciona como **planner + orchestrator + renderer**.
- El cálculo permanece en funciones determinísticas y en outputs de NB30.
- El planner convierte lenguaje natural a plan estructurado (intent, params, alcance, modo de confianza, clarificación).
- La respuesta final siempre incluye evidencia, alcance, caveat y siguientes preguntas.

### Herramientas previstas para consumo del chatbot

- `get_metric_value`
- `aggregate_metric`
- `rank_by_metric`
- `get_trend`
- `compare_segments`
- `screen_by_conditions`
- `run_insight_detectors`
- `get_insight_candidates`
- `generate_hypothesis_candidates`
- `render_chart_data`

### Reglas críticas fijadas en diseño

1. El chatbot no calcula por sí mismo métricas analíticas.
2. En modo hipótesis, el lenguaje es explícitamente no causal.
3. Métricas pending/provisional deben reflejar caveat en respuesta.
4. Peer groups débiles deben reflejar caveat de confianza.
5. Comparaciones inválidas según NB20 deben rechazarse o reformularse.
6. Preguntas fuera de alcance no se improvisan.

### Golden flows definidos

Se diseñaron 10 flujos conversacionales incluyendo:
- ranking con métrica suspendida (debe rechazar y proponer alternativa),
- comparación por segmento válida,
- tendencia con posible ambigüedad de entidad,
- request de insight,
- hypothesis request con guardrail de no causalidad,
- follow-ups de filtro y visualización.

### Artefactos nuevos generados

- `docs/architecture/reto1_chatbot_contract.md`
- `reports/reto1/chatbot_design_summary.md`
- `reports/reto1/golden_conversation_flows.md`
- `reports/reto1/chatbot_planner_schema.json`

### Qué queda pendiente para implementación real

1. Implementar runtime de tools en app (ej. Streamlit/API) con validación de schemas.
2. Integrar state manager conversacional persistente y seguro.
3. Ejecutar evaluación sobre golden flows con métricas de accuracy/groundedness.
4. Endurecer políticas de fallback y manejo de errores en tiempo real.

---

## Iteración 7 — 2026-04-25: Diseño conversacional NB 40 (v2)

### Qué arquitectura conversacional se definió

**Principio rector:** el LLM no calcula — orquesta.

```
User input → LLM Planner → validate_plan() → tool calls → LLM Renderer (language guards) → respuesta
```

- **LLM Planner**: clasifica intent, extrae parámetros, construye `ChatbotExecutionPlan`
- **validate_plan()**: pre-flight semántico contra metrics.yaml + business_rules.yaml (nueva función en NB40)
- **Tool layer**: funciones determinísticas — `get_metric_value`, `rank_by_metric`, `get_trend`, etc.
- **NB30 routing**: `insight_request` no re-ejecuta detectores — lee `insight_candidates.parquet`
- **LLM Renderer**: aplica `response_contract` + 3 language guard functions:
  - `apply_direction_guard()`: neutral vs directional language según validation_status
  - `apply_hypothesis_guard()`: rechaza forbidden_terms causales
  - `build_uncertainty_caveat()`: caveat por validation_status + peer_n

### Herramientas que usará el chatbot

| Tool | Intent | NB30 o semántica |
|---|---|---|
| `get_metric_value` | query | semántica |
| `aggregate_metric` | aggregate | semántica |
| `rank_by_metric` | rank | semántica |
| `get_trend` | trend | semántica |
| `compare_segments` | compare | semántica |
| `screen_by_conditions` | multivariable_filter | semántica |
| `route_insight_request` | insight_request | NB30 (parquet) |
| `generate_hypothesis_candidates` | hypothesis_request | NB30 (correlaciones) |
| `render_chart_data` | follow_up_visualization | renderer |

### Reglas de clarificación fijadas

- ZONE sin COUNTRY y CITY → clarify (ZONE no es único)
- Métrica suspendida (`lead_penetration`) → clarify con alternativa
- Comparación inválida (cross-canal, cross-country sin controlar) → rechazar + proponer
- Pregunta causal fuerte ("causa", "explica") → rechazar + ofrecer hipótesis asociativa
- Peer group < 5 zonas → excluir y reportar; < 10 → low_confidence warning

### Golden flows definidos (10 flujos)

| ID | Tipo | Trigger |
|---|---|---|
| GF01 | Métrica suspendida | "Top 5 Lead Penetration" |
| GF02 | Comparación válida | "Wealthy vs Non Wealthy en México" |
| GF03 | Zona ambigua | "Evolución Gross Profit UE en Chapinero" |
| GF06 | Hipótesis no-causal | "¿Qué explica el crecimiento de órdenes?" |
| GF07 | Follow-up scope | "¿Y solo en Colombia?" |
| GF08 | Follow-up viz | "Muéstralo en gráfico" |
| GF09 | Insight request (NB30) | "¿Qué problemas tiene Bogotá esta semana?" |
| GF10 | Causalidad rechazada | "Demuéstrame que CVR causa orders" |

### Cambios en NB40 (28 → 33 celdas)

| Celda nueva | Qué agrega |
|---|---|
| `nb40-arch-diagram` | Diagrama ASCII del flujo completo (User → LLM → Tools → LLM → Response) |
| `nb40-planner-validate` | `validate_plan()`: 6 reglas semánticas, demo con 4 casos |
| `nb40-nb30-routing` | `route_insight_request()`: lookup en parquet, demo con filtro por país |
| `nb40-lang-guards` | 3 guard functions: direction, hypothesis, uncertainty_caveat |
| `nb40-golden-rich` | 8 diálogos completos (USER/PLAN/TOOL/BOT/CAVEAT/NEXT_Q) |
| Export reemplazado | Genera docs profundas: 4 archivos con contenido real (no solo tablas) |

### Qué falta para pasar de diseño a implementación real

1. **Planner como prompt LLM**: convertir `planner_schema` en system prompt con structured output
2. **Tool adapter layer**: implementar las 9 funciones del tool_contract con datos reales
3. **State manager**: clase `ChatSessionState` con serialización y expiración de contexto
4. **Golden flow tests**: pipeline de evaluación automática (intent accuracy, groundedness)
5. **App shell**: Streamlit o equivalente consumiendo contratos definidos en NB40
6. **Calibración de thresholds**: antes de activar `insight_request` en producción
