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

| Archivo | Contenido |
|---|---|
| `config/metrics.yaml` | Catálogo de 13 métricas: escala, dirección, confianza, riesgo de outlier |
| `config/business_rules.yaml` | Entidades, peer groups, reglas temporales, detectores, reglas de lenguaje |
| `config/question_types.yaml` | 7 intents del sistema con parámetros, funciones futuras y ejemplos |

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
