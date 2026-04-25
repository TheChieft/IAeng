# Reto 1 — Decisiones Técnicas de Data Prep

> **Actualizado:** 2026-04-24 — alineado con estructura actual del repo post-migración.
> Las referencias históricas a `src/data_prep/` corresponden a iteraciones 1–3. Esa capa fue eliminada en la iteración 4.
> La lógica de pipeline vive ahora en `notebooks/reto1/00_reto1_data_prep.ipynb`.

---

## 1. Resumen ejecutivo

### Qué hace el pipeline

`notebooks/reto1/00_reto1_data_prep.ipynb` ejecuta en orden:

1. Carga de hojas crudas del Excel y perfilado base.
2. Estandarización de nombres de columnas.
3. Limpieza conservadora de texto y tipado numérico semanal.
4. Detección y remoción de duplicados exactos.
5. Transformación wide → long.
6. Construcción de zone master de cobertura.
7. Validación de 10 checks estructurales.
8. Generación de reporte de validación.

### Artefactos que deja listos

| Artefacto | Ubicación | Descripción |
|---|---|---|
| `metrics_raw_cleaned.parquet` | `data/interim/` | Métricas limpias, wide |
| `orders_raw_cleaned.parquet` | `data/interim/` | Órdenes limpias, wide |
| `metrics_long.parquet` | `data/processed/` | Métricas long, grano (COUNTRY, CITY, ZONE, METRIC, WEEK_OFFSET) |
| `orders_long.parquet` | `data/processed/` | Órdenes long, mismo grano |
| `zone_master.parquet` | `data/processed/` | Cobertura cruzada de zonas |
| `pipeline_validation.json/md` | `reports/reto1/` | Evidencia auditable de 10 checks |

### Qué no resuelve todavía

- Semántica de métricas (direccionalidad): → **Notebook 20**.
- Faltantes históricos (no hay imputación): → decisión de capa analítica futura.
- Reconciliación completa de cobertura de zonas.
- Scoring, causalidad, hallazgos de negocio.

---

## 2. Input real observado

**Fuente:** `data/raw/Sistema de Análisis Inteligente para Operaciones Rappi - Dummy Data (1).xlsx`

**Hojas usadas:**
1. `RAW_INPUT_METRICS`
2. `RAW_ORDERS`
3. `RAW_SUMMARY`

**Referencia de schema crudo:** `reports/reto1/raw_schema_summary.json`

**Shapes observados:**
- `RAW_INPUT_METRICS`: 12,573 × 15
- `RAW_ORDERS`: 1,242 × 13
- `RAW_SUMMARY`: 15 × 4

### Diferencias entre PDF del caso y archivo real

| Fuente | Columnas semanales en datos reales |
|---|---|
| RAW_INPUT_METRICS | Sufijo `_ROLL`: `L8W_ROLL` … `L0W_ROLL` |
| RAW_ORDERS | Sin sufijo: `L8W` … `L0W` |

**Decisión:** estandarizar ambas familias a canónico `L8W`–`L0W` vía regex extensible a `_VALUE`. Columnas originales conservadas en `interim/` para trazabilidad.

**Implementación:** `src/helpers/io.py` → `detect_week_columns()`.

---

## 3. Definición de duplicado

### Duplicado exacto

Fila idéntica en **todas** las columnas originales de la hoja, antes de agregar columnas auxiliares.

**Por qué sobre columnas fuente:** si se incluyera `_SOURCE_ROW_NUMBER` en el subset, nunca habría duplicados (cada fila tiene número único). Se capturan `source_columns` al cargar, antes de agregar auxiliares.

**Resultados actuales:**
- Métricas: **963** duplicados exactos removidos (keep='first').
- Órdenes: **0** duplicados exactos.

### No-duplicado (casos ambiguos)

Filas que comparten key lógica pero difieren en cualquier atributo o valor semanal → **no se tocan**. Se reportan para revisión. Resultado actual: 0 keys ambiguas post-dedup en ambas tablas.

---

## 4. Reglas de limpieza aplicadas

### Normalización de columnas

- Trim de espacios, reemplazo interno por `_`, uppercase.
- `src/helpers/io.py` → `normalize_col()`.

### Normalización de texto en dimensiones

- `COUNTRY`: trim + uppercase.
- `CITY`, `ZONE`, `ZONE_TYPE`, `ZONE_PRIORITIZATION`, `METRIC`: trim + normalización de espacios múltiples internos. **No se renombran valores.**
- Columnas `*_ORIGINAL` conservadas para trazabilidad.

### Tipado numérico

- Columnas canónicas `L8W`–`L0W` → `pd.to_numeric(errors='coerce')`.
- Fallas registradas por columna. Resultado: **0 fallas** en ambas tablas.

### Faltantes

- **No imputados** en esta capa.
- Flag `has_missing_history` = True si entidad tiene ≥1 semana nula.

### Trazabilidad completa

- `_SOURCE_ROW_NUMBER`: fila original en Excel (index + 2).
- `SOURCE_TABLE`: hoja origen.
- Columnas `*_ORIGINAL` para valores antes de normalización.
- Columnas `*_ROLL` (originales) conservadas en `interim/` junto a las canónicas.

---

## 5. Transformación wide → long

- Detección de columnas `L{n}W` (canónicas).
- `pd.melt()` con `id_vars` según tabla.
- Columnas generadas: `WEEK_OFFSET`, `week_offset_num` (0-8), `VALUE`, `is_current_week`, `has_missing_history`.
- `metric_group`: inferido del nombre de METRIC (antes del `>` o primer token). **Indicativo, no catálogo oficial.**

**Matemática verificada (PASS):**
- Métricas: 11,610 × 9 = **104,490** filas long. ✓
- Órdenes: 1,242 × 9 = **11,178** filas long. ✓

---

## 6. Zone master

| COVERAGE_CLASS | Zonas | Descripción |
|---|---|---|
| BOTH | 978 | En métricas y órdenes |
| ONLY_METRICS | 2 | Solo en métricas |
| ONLY_ORDERS | 264 | Solo en órdenes — mismatch estructural |

**El mismatch es estructural, no un error del pipeline.** El `zone_master` lo hace explícito. Los análisis deben declarar su política de join (inner = excluye 264 zonas; left/outer = las mantiene con nulls).

---

## 7. Validación del pipeline

10 checks estructurales en notebook 00, Sección 7. Todos PASS.

Evidencia en `reports/reto1/pipeline_validation.json`.

---

## 8. Riesgos y limitaciones abiertos

| Riesgo | Estado | Notebook responsable |
|---|---|---|
| Mismatch de cobertura zonas | Documentado, sin resolver | Decisión analítica en NB 20+ |
| Faltantes históricos sin imputar | Documentado | Decisión de capa analítica |
| Semántica de métricas incompleta | Bloqueante para bot | **NB 20** |
| Outliers extremos (Lead Penetration, Gross Profit UE) | Documentado en EDA | NB 20/30 |

**No asumir todavía:**
- Que valor alto siempre es mejor.
- Causalidad por co-movimiento.
- Completitud geográfica homogénea.

---

## 9. Historial de cambios

| Iteración | Cambio principal |
|---|---|
| 1–2 | Pipeline base en `src/data_prep/` (9 scripts). |
| 3 | EDA formal. |
| 4 | Migración notebook-first. `src/data_prep/` eliminado. Pipeline en `00_data_prep_common.ipynb`. |
| **5 (actual)** | Notebooks en `notebooks/reto1/`. Notebook 00 renombrado a `00_reto1_data_prep.ipynb`. Decisiones alineadas con estructura vigente. |
