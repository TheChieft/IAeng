# Data Quality Report

## 1) Sanity Check Inicial

| Tabla | Filas | Columnas | Blank rows | Duplicados exactos en crudo |
| --- | --- | --- | --- | --- |
| RAW_INPUT_METRICS | 12573 | 15 | 0 | 963 |
| RAW_ORDERS | 1242 | 13 | 0 | 0 |
| RAW_SUMMARY | 15 | 4 | 0 | 0 |

## 2) Estandarización de Columnas

| SOURCE_TABLE | ORIGINAL_COLUMN | CANONICAL_COLUMN |
| --- | --- | --- |
| RAW_INPUT_METRICS | L0W_ROLL | L0W |
| RAW_INPUT_METRICS | L1W_ROLL | L1W |
| RAW_INPUT_METRICS | L2W_ROLL | L2W |
| RAW_INPUT_METRICS | L3W_ROLL | L3W |
| RAW_INPUT_METRICS | L4W_ROLL | L4W |
| RAW_INPUT_METRICS | L5W_ROLL | L5W |
| RAW_INPUT_METRICS | L6W_ROLL | L6W |
| RAW_INPUT_METRICS | L7W_ROLL | L7W |
| RAW_INPUT_METRICS | L8W_ROLL | L8W |
| RAW_ORDERS | L0W | L0W |
| RAW_ORDERS | L1W | L1W |
| RAW_ORDERS | L2W | L2W |
| RAW_ORDERS | L3W | L3W |
| RAW_ORDERS | L4W | L4W |
| RAW_ORDERS | L5W | L5W |
| RAW_ORDERS | L6W | L6W |
| RAW_ORDERS | L7W | L7W |
| RAW_ORDERS | L8W | L8W |

## 3) Limpieza y Tipado

| Tabla | Duplicados exactos removidos | Coerciones fallidas semanales |
| --- | --- | --- |
| metrics_raw_cleaned | 963 | 0 |
| orders_raw_cleaned | 0 | 0 |

## 4) Exploración Inicial Estructural

| Indicador | Valor |
| --- | --- |
| metrics_raw_cleaned shape | (11610, 32) |
| orders_raw_cleaned shape | (1242, 19) |
| metrics_long shape | (104490, 14) |
| orders_long shape | (11178, 11) |
| Países (metrics) | 9 |
| Países (orders) | 9 |
| Ciudades (metrics) | 270 |
| Ciudades (orders) | 342 |
| Zonas (metrics) | 980 |
| Zonas (orders) | 1242 |
| Métricas únicas | 13 |
| Week offsets metrics | L0W, L1W, L2W, L3W, L4W, L5W, L6W, L7W, L8W |
| Week offsets orders | L0W, L1W, L2W, L3W, L4W, L5W, L6W, L7W, L8W |

### Faltantes por columna (top)

| Tabla | Columna | Missing |
| --- | --- | --- |
| metrics_raw_cleaned | L8W | 102 |
| metrics_raw_cleaned | L8W_ROLL | 102 |
| metrics_raw_cleaned | L6W | 100 |
| metrics_raw_cleaned | L6W_ROLL | 100 |
| metrics_raw_cleaned | L7W | 98 |
| metrics_raw_cleaned | L7W_ROLL | 98 |
| metrics_raw_cleaned | L5W | 97 |
| metrics_raw_cleaned | L5W_ROLL | 97 |
| metrics_raw_cleaned | L4W | 87 |
| metrics_raw_cleaned | L4W_ROLL | 87 |
| metrics_raw_cleaned | L3W_ROLL | 60 |
| metrics_raw_cleaned | L3W | 60 |
| orders_raw_cleaned | L1W | 248 |
| orders_raw_cleaned | L0W | 244 |
| orders_raw_cleaned | L3W | 243 |
| orders_raw_cleaned | L2W | 242 |
| orders_raw_cleaned | L4W | 239 |
| orders_raw_cleaned | L5W | 226 |
| orders_raw_cleaned | L8W | 221 |
| orders_raw_cleaned | L6W | 221 |
| orders_raw_cleaned | L7W | 220 |
| orders_raw_cleaned | COUNTRY | 0 |
| orders_raw_cleaned | CITY | 0 |
| orders_raw_cleaned | ZONE_ORIGINAL | 0 |

### Overlap de zonas

| Métrica | Valor |
| --- | --- |
| zones_total | 1244 |
| zones_both | 978 |
| zones_only_metrics | 2 |
| zones_only_orders | 264 |

### Métricas por zona (distribución)

| Estadístico | Valor |
| --- | --- |
| count | 980.0 |
| mean | 11.847 |
| std | 1.726 |
| min | 1.0 |
| 25% | 12.0 |
| 50% | 12.0 |
| 75% | 13.0 |
| max | 13.0 |

### Resumen simple de rangos por métrica (top 25 por volumen)

| METRIC | rows | missing | min | p25 | median | p75 | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Non-Pro PTC > OP | 8788 | 5 | 0.0 | 0.659552 | 0.716683 | 0.767505 | 1.0 |
| % Restaurants Sessions With Optimal Assortment | 8691 | 3 | 0.0 | 0.01414 | 0.731967 | 0.901634 | 1.0 |
| Pro Adoption (Last Week Status) | 8636 | 13 | 0.0 | 0.224013 | 0.283835 | 0.366648 | 1.0 |
| Restaurants SS > ATC CVR | 8611 | 11 | 0.0 | 0.454681 | 0.531389 | 0.580348 | 0.866667 |
| Restaurants SST > SS CVR | 8611 | 11 | 0.116364 | 0.86269 | 0.895864 | 0.91905 | 1.0 |
| Gross Profit UE | 8514 | 117 | -229.193676 | -0.795288 | 0.792321 | 2.221495 | 12.842822 |
| Retail SST > SS CVR | 8489 | 25 | 0.0 | 0.851988 | 0.891836 | 0.920008 | 1.0 |
| % PRO Users Who Breakeven | 8367 | 3 | 0.0 | 0.202624 | 0.312903 | 0.434262 | 1.0 |
| Lead Penetration | 8326 | 53 | 0.001161 | 0.070524 | 0.144012 | 0.264482 | 393.9 |
| Perfect Orders | 8268 | 138 | 0.136713 | 0.838378 | 0.883352 | 0.906636 | 1.0 |
| MLTV Top Verticals Adoption | 8256 | 6 | 0.0 | 0.089687 | 0.135338 | 0.198113 | 1.0 |
| Restaurants Markdowns / GMV | 7909 | 74 | 0.021149 | 0.100631 | 0.126922 | 0.158853 | 0.431336 |
| Turbo Adoption | 2397 | 168 | 0.012831 | 0.149856 | 0.233559 | 0.34787 | 0.929155 |

## 5) Warnings para análisis posterior

- Metrics had 963 exact duplicate rows removed.
- Zone coverage differs between metrics and orders tables.

## 6) Decisiones y Trade-offs

- Se removieron solo duplicados exactos para mantener enfoque conservador y auditable.
- No se imputaron faltantes ni se resolvieron duplicados lógicos ambiguos automáticamente.
- No se asignaron fechas calendario; se preservó el modelo temporal por offsets L8W..L0W.