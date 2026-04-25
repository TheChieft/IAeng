# Reto 1 Rappi - Decisiones Técnicas del Data Prep

## 1. Resumen ejecutivo

### Qué hace el pipeline

El pipeline implementado en [src/data_prep](src/data_prep) ejecuta, en orden:

1. Carga de hojas crudas del Excel y perfilado base.
2. Estandarización de nombres de columnas.
3. Limpieza conservadora de texto y tipado numérico semanal.
4. Detección y remoción de duplicados exactos.
5. Transformación de tablas semanales de formato wide a long.
6. Construcción de un zone master para cobertura entre fuentes.
7. Generación de reportes y diccionario de datos.

La orquestación completa está en [src/data_prep/run_initial_data_profile.py](src/data_prep/run_initial_data_profile.py).

### Qué deja listo

1. Datasets limpios y trazables en [data/processed](data/processed).
2. Tablas long con grano analítico por zona, métrica y offset semanal.
3. Reglas explícitas de mapeo semanal y limpieza en [reports/data_dictionary.md](reports/data_dictionary.md).
4. Validaciones estructurales y métricas de calidad en [reports/data_quality_report.json](reports/data_quality_report.json) y [reports/data_quality_report.md](reports/data_quality_report.md).

### Qué no resuelve todavía

1. No resuelve semántica de negocio de métricas (direccionalidad mejor o peor).
2. No resuelve faltantes históricos (no hay imputación).
3. No resuelve reconciliación completa de universo de zonas entre métricas y órdenes.
4. No ejecuta scoring, causalidad ni hallazgos de negocio finales.

## 2. Input real observado

### Hojas del Excel

Fuente observada: [data/raw/Sistema de Análisis Inteligente para Operaciones Rappi - Dummy Data (1).xlsx](data/raw/Sistema%20de%20An%C3%A1lisis%20Inteligente%20para%20Operaciones%20Rappi%20-%20Dummy%20Data%20%281%29.xlsx)

Hojas usadas:

1. RAW_INPUT_METRICS
2. RAW_ORDERS
3. RAW_SUMMARY

Referencia de resumen crudo: [reports/raw_schema_summary.json](reports/raw_schema_summary.json)

### Shapes observados

1. RAW_INPUT_METRICS: 12573 x 15
2. RAW_ORDERS: 1242 x 13
3. RAW_SUMMARY: 15 x 4

### Columnas originales relevantes

RAW_INPUT_METRICS incluye dimensiones geográficas y semanales tipo L8W_ROLL ... L0W_ROLL.

RAW_ORDERS incluye dimensiones geográficas y semanales tipo L8W ... L0W.

### Diferencias entre PDF del caso y archivo real

Hecho observado en data real:

1. En métricas existen columnas semanales con sufijo ROLL.
2. En órdenes existen columnas semanales sin sufijo.

Decisión tomada:

1. Estandarizar ambas familias a un esquema canónico L8W ... L0W vía regex, manteniendo columnas originales para trazabilidad.
2. Regla extensible también a columnas tipo VALUE (si aparecen en otras versiones de archivo).

Implementación: [src/data_prep/common.py](src/data_prep/common.py)

## 3. Definición de duplicado

### Qué se definió como duplicado exacto

Duplicado exacto se definió como fila idéntica en todas las columnas originales de la hoja, antes de agregar columnas auxiliares.

### Qué columnas participaron

Se usa subset con source_columns, que captura columnas originales de la hoja al cargarla.

1. Métricas: todas las columnas originales de RAW_INPUT_METRICS.
2. Órdenes: todas las columnas originales de RAW_ORDERS.

Implementación:

1. [src/data_prep/clean_metrics.py](src/data_prep/clean_metrics.py)
2. [src/data_prep/clean_orders.py](src/data_prep/clean_orders.py)

### Cuántos duplicados exactos se encontraron

1. Métricas: 963 duplicados exactos removidos.
2. Órdenes: 0 duplicados exactos removidos.

Fuente: [reports/data_quality_report.json](reports/data_quality_report.json)

### Qué acción se tomó

1. Se conservó la primera ocurrencia.
2. Se eliminaron ocurrencias exactas posteriores.
3. Se preservó trazabilidad con _SOURCE_ROW_NUMBER en las filas retenidas.

### Por qué la acción fue razonable

1. Es una regla auditable y de bajo riesgo de sobre-limpieza.
2. Evita sesgo por doble conteo en agregaciones y modelos.
3. No colapsa registros que difieren en algún valor (casos ambiguos quedan fuera de esta regla).

Problema corregido explícitamente en la versión actual:

1. La deduplicación se calcula contra columnas fuente y no contra columnas auxiliares, para evitar que _SOURCE_ROW_NUMBER impida detectar duplicados reales.

## 4. Definición de no-duplicado

### Qué casos parecidos no se eliminaron

No se eliminaron filas que comparten key lógica pero difieren en cualquier atributo o valor semanal.

Ejemplos conceptuales:

1. Misma zona y métrica con alguna semana distinta.
2. Misma zona y métrica con diferencia en columnas categóricas.

### Qué se consideró ambiguo

Cualquier multiplicidad no exacta sobre key lógica se trata como caso potencial de negocio o carga, no como duplicado técnico automático.

### Qué se dejó abierto para revisión posterior

Se reporta conteo de claves lógicas no exactas en el perfil para revisión manual.

Resultado actual:

1. Métricas: 0 keys lógicas no exactas post dedup exacto.
2. Órdenes: 0 keys lógicas no exactas post dedup exacto.

Fuente: [reports/data_quality_report.json](reports/data_quality_report.json)

## 5. Reglas de limpieza aplicadas

### Normalización de nombres de columnas

1. Trim de espacios.
2. Reemplazo de espacios internos por guion bajo.
3. Uppercase de nombres de columnas.

Implementación: [src/data_prep/common.py](src/data_prep/common.py)

### Conversión de tipos

1. Columnas semanales canónicas L8W ... L0W se convierten a numérico con coerción controlada.
2. Se registra cantidad de coerciones fallidas por columna.

Resultado actual:

1. Fallas de coerción semanales en métricas: 0.
2. Fallas de coerción semanales en órdenes: 0.

### Manejo de strings

1. Trim en extremos.
2. Normalización de espacios múltiples internos.
3. Uppercase solo para COUNTRY.
4. CITY, ZONE y otras dimensiones mantienen semántica textual (no se renombran manualmente).

### Manejo de faltantes

1. Se contabilizan faltantes por columna.
2. No se imputan faltantes.
3. Se propaga bandera has_missing_history en tablas long para identificar historia incompleta por entidad.

### Trazabilidad preservada

1. _SOURCE_ROW_NUMBER: número de fila original en Excel.
2. SOURCE_TABLE: hoja origen.
3. Columnas *_ORIGINAL para dimensiones textuales normalizadas.
4. Conservación de columnas semanales originales junto a canónicas en tablas cleaned.

## 6. Reglas de transformación

### Cómo se pasó de wide a long

1. Se detectan columnas semanales canónicas L8W ... L0W.
2. Se aplica melt con id_vars según tabla.
3. Se genera WEEK_OFFSET y VALUE.
4. Se generan week_offset_num e is_current_week.

Implementación: [src/data_prep/build_long_tables.py](src/data_prep/build_long_tables.py)

### Dimensiones finales

Métricas long incluye:

1. COUNTRY, CITY, ZONE, ZONE_TYPE, ZONE_PRIORITIZATION, METRIC
2. SOURCE_TABLE, _SOURCE_ROW_NUMBER
3. WEEK_OFFSET, week_offset_num, VALUE
4. metric_group, is_current_week, has_missing_history

Órdenes long incluye:

1. COUNTRY, CITY, ZONE, METRIC
2. SOURCE_TABLE, _SOURCE_ROW_NUMBER
3. WEEK_OFFSET, week_offset_num, VALUE
4. is_current_week, has_missing_history

### Qué significa week_offset

1. L8W: ocho semanas atrás.
2. L0W: semana actual relativa.
3. No se asignan fechas calendario reales.

### Transformaciones estructurales vs semánticas

Estructurales:

1. Estandarización de columnas semanales a canónico.
2. Conversión wide a long.
3. Tipado numérico.
4. Dedupe exacto.

Semánticas ligeras:

1. metric_group inferido desde texto de METRIC (antes del símbolo > o primer token).

Punto discutible:

1. metric_group es útil para navegación, pero no debe tomarse como taxonomía oficial de negocio sin catálogo formal.

## 7. Validaciones realizadas

### Coerción numérica

1. Se registran fallas por columna semanal canónica.
2. Resultado actual: 0 fallas en ambas tablas.

### Conteos antes y después

1. Métricas: 12573 crudo -> 11610 cleaned.
2. Órdenes: 1242 crudo -> 1242 cleaned.

### Validación matemática de wide a long

1. Métricas: 11610 x 9 semanas = 104490 filas long.
2. Órdenes: 1242 x 9 semanas = 11178 filas long.

Los conteos coinciden con salida reportada.

### Verificación de unicidad del grano

Hecho validado:

1. No se detectan claves lógicas duplicadas no exactas en tablas cleaned.

Limitación:

1. No hay una aserción explícita en código para unicidad de grano final en tablas long.
2. Se recomienda agregar test formal de unicidad por grano objetivo.

### Cobertura de zonas entre tablas

1. Zone master total: 1244 zonas.
2. Zonas en ambas tablas: 978.
3. Solo métricas: 2.
4. Solo órdenes: 264.

Esto confirma mismatch estructural entre fuentes.

Fuente: [data/processed/zone_master.csv](data/processed/zone_master.csv)

### Problemas corregidos en esta versión del pipeline

1. Se resolvió la ambigüedad técnica de nomenclatura semanal entre fuentes al mapear a L8W ... L0W canónico.
2. Se fijó la lógica de deduplicación para que opere sobre columnas fuente y no sobre columnas auxiliares de trazabilidad.
3. Se incorporó validación explícita de cobertura de zonas entre métricas y órdenes para visibilizar mismatch estructural.

## 8. Riesgos y limitaciones abiertos

### Mismatch entre métricas y órdenes

Riesgo:

1. No existe correspondencia uno a uno de zonas entre fuentes.
2. Cualquier análisis combinado puede sesgarse por cobertura desigual.

### Faltantes históricos

Riesgo:

1. Existen faltantes semanales en ambas tablas.
2. Comparaciones temporales por zona o métrica pueden mezclar series completas e incompletas.

### Diferencias semánticas PDF vs data real

Riesgo:

1. El contrato documental del caso no coincide completamente con el contrato observado en datos.
2. Decisiones de modelado deben apoyarse en el input real y no solo en el PDF.

### Cosas que no deben asumirse todavía

1. No asumir que valor alto siempre es mejor.
2. No asumir causalidad por co-movimiento.
3. No asumir equivalencia semántica entre métricas con prefijos similares.
4. No asumir completitud geográfica homogénea entre tablas.

## 9. Recomendaciones antes del EDA formal

### Qué revisar

1. Zonas solo en órdenes y solo en métricas, con catálogo de cobertura esperado.
2. Métricas con rangos extremos y unidades dudosas.
3. Consistencia de codificación de texto en CITY y ZONE para prevenir issues de encoding.

### Qué tests agregar

1. Test de unicidad de grano en long para métricas usando COUNTRY, CITY, ZONE, METRIC, WEEK_OFFSET.
2. Test de unicidad de grano en long para órdenes usando COUNTRY, CITY, ZONE, METRIC, WEEK_OFFSET.
3. Test de conservación de volumen wide -> long por tabla.
4. Test de contratos de esquema esperado por hoja.
5. Test de integridad de mapeo semanal (todas las semanas L8W..L0W presentes).

### Qué catálogos faltan

1. Catálogo oficial de zonas válidas por ciudad y país.
2. Catálogo de definición de métricas y unidad.
3. Catálogo de orientación analítica por métrica (sube o baja deseable).

### Qué no deberíamos hacer aún

1. Scoring de zonas problemáticas.
2. Ranking de performance global sin ajustar cobertura y faltantes.
3. Conclusiones causales o recomendaciones operativas finales.

---

## Hechos, decisiones y riesgos trazables

Hechos (medidos): shapes, duplicados exactos, faltantes, cobertura y conteos long.

Decisiones (implementadas): dedupe exacto conservador, estandarización semanal canónica, sin imputación, sin colapso ambiguo.

Riesgos (abiertos): cobertura desigual, faltantes históricos, semántica incompleta de métricas y diferencias documento vs dato real.
