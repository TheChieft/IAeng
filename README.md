# IAeng — Rappi Technical Assessment

Repositorio para la prueba técnica de Rappi. Dos retos que comparten base de datos y arquitectura analítica:

- **Reto 1 — Operational Intelligence:** análisis de métricas operativas semanales por zona → bot conversacional + sistema de insights automáticos.
- **Reto 2 — Competitive Intelligence:** adquisición de datos públicos de competidores → soporte a decisiones de pricing/ops/strategy por zona.

---

## Estructura del repositorio

```
.
├── data/
│   ├── raw/            # Fuente inmutable (Excel workbook del caso)
│   ├── interim/        # Tablas limpias pre-melt (metrics_raw_cleaned, orders_raw_cleaned)
│   └── processed/      # Artefactos canónicos (metrics_long, orders_long, zone_master)
│
├── notebooks/          # Flujo de trabajo principal — ver sección siguiente
│
├── src/
│   └── helpers/        # Utilidades mínimas: paths.py, io.py
│
├── docs/
│   ├── retos/          # PDFs del caso + planteamientos de preguntas
│   ├── research/       # Investigación de diseño y contexto del sistema
│   ├── working_notes/  # Bitácora técnica y decisiones de data prep
│   └── architecture/   # Diseño del sistema analítico (en construcción)
│
└── reports/
    └── reto1/          # Reportes auditables: calidad, validación, diccionario
```

---

## Demo Streamlit — Reto 1

### Prerrequisitos

```bash
python -m venv .venv && source .venv/bin/activate
pip install pandas pyarrow pyyaml streamlit plotly nbconvert python-dotenv google-genai
```

### Configurar LLM (opcional — Gemini)

```bash
cp .env.example .env
# edita .env y pon tu GEMINI_API_KEY
```

`.env` está en `.gitignore` — nunca se commitea.

Para desactivar Gemini sin borrar la key: `USE_LLM=false` en `.env`.

### Correr la app

```bash
# desde la raíz del repo
source .venv/bin/activate
streamlit run app/reto1/streamlit_app.py
```

Abre en `http://localhost:8501`.  
Sin `.env`, corre con planner por keywords (100% funcional).

### Artifacts requeridos (ya generados)

| Archivo | Ubicación |
|---|---|
| `metrics_long.parquet` | `data/processed/` |
| `zone_master.parquet` | `data/processed/` |
| `streamlit_insights.parquet` | `reports/reto1/` |
| `top_insights_final.parquet` | `reports/reto1/` |
| `insight_candidates.parquet` | `reports/reto1/` |
| `metrics.yaml`, `business_rules.yaml`, `question_types.yaml` | `config/` |

Si necesitas regenerar los artifacts de insights:

```bash
source .venv/bin/activate
jupyter nbconvert --to notebook --execute --output-dir . \
    notebooks/reto1/30_reto1_insight_engine.ipynb
mv 30_reto1_insight_engine.ipynb notebooks/reto1/
```

### Preguntas soportadas

| Tipo | Ejemplo |
|---|---|
| Ranking | *Top 5 zonas por Perfect Orders en MX* |
| Comparación | *Compara Wealthy vs Non Wealthy en CO* |
| Tendencia | *Tendencia de Turbo Adoption en MX* |
| Insights | *Qué problemas tiene Argentina* |
| Hipótesis | *Qué podría explicar el crecimiento en MX* |
| Follow-up | *Solo en Colombia* · *Muéstralo en gráfico* |

### Limitaciones conocidas

- Dirección de todas las métricas es `provisional` — no validada con negocio.
- `lead_penetration` suspendida — el chatbot la rechaza con mensaje.
- Planner es keyword-based (Fase 1). LLM optional: `LLM_PROVIDER=anthropic LLM_API_KEY=sk-... streamlit run ...`
- Turbo Adoption excluido de benchmarks de peer group (cobertura baja).
- Sin fechas calendario — solo offsets relativos L0W–L8W.

---

## Flujo de trabajo recomendado

### Reto 1

**1. Ejecutar el pipeline de datos (una vez, o cuando cambia el raw):**

```
notebooks/reto1/00_reto1_data_prep.ipynb
```

Genera todos los artefactos en `data/interim/` y `data/processed/`.  
Incluye validación de 10 checks al final — todos deben ser PASS.

**2. Exploración y diseño del sistema:**

```
notebooks/reto1/10_reto1_eda.ipynb              # EDA formal orientado a diseño del sistema
notebooks/reto1/20_reto1_semantic_layer.ipynb   # Capa semántica y contratos de métricas
notebooks/reto1/30_reto1_insight_engine.ipynb   # Detectores de anomalías, curation, Streamlit outputs
notebooks/reto1/40_reto1_chatbot_design.ipynb   # Arquitectura del bot, tool contracts, golden flows
```

Ver `notebooks/reto1/README.md` para documentación completa del flujo.

---

## Artefactos generados por `00_reto1_data_prep.ipynb`

| Archivo | Ubicación | Descripción |
|---|---|---|
| `metrics_raw_cleaned.parquet` | `data/interim/` | Métricas limpias en formato wide |
| `orders_raw_cleaned.parquet` | `data/interim/` | Órdenes limpias en formato wide |
| `metrics_long.parquet` | `data/processed/` | Métricas en formato long — grano: (COUNTRY, CITY, ZONE, METRIC, WEEK\_OFFSET) |
| `orders_long.parquet` | `data/processed/` | Órdenes en formato long — mismo grano |
| `zone_master.parquet` | `data/processed/` | Cobertura de zonas entre tablas (COVERAGE\_CLASS: BOTH / ONLY\_METRICS / ONLY\_ORDERS) |

---

## Decisiones de diseño clave

- **Parquet-only** en `interim/` y `processed/`. CSV no se persiste por defecto.
- **Sin imputación** de faltantes en la capa de preparación. Los nulos se propagan con flag `has_missing_history`.
- **Sin fechas calendario.** Solo offsets relativos `L8W` (8 semanas atrás) – `L0W` (semana actual).
- **Deduplicación conservadora.** Solo duplicados exactos. Duplicados lógicos se reportan, no se colapsan.
- **Mismatch de cobertura es estructural.** 264 zonas en órdenes no tienen métricas — `zone_master` lo documenta.
- **Detectores transparentes** para el insight engine: WoW delta, decline streak, desviación vs. peer median, robust z-score (MAD).

---

## Reto 2 — Estado

Pendiente. La estructura del repo está preparada para absorber datos de Competitive Intelligence bajo el mismo flujo:

- Nuevos artefactos irían a `data/processed/` con prefijo `reto2_`.
- El notebook `00_data_prep_common.ipynb` es configurable por `RETO`.
- Los notebooks 2x–4x de Reto 2 seguirían la misma numeración.

---

## Helpers de src

```python
from src.helpers.paths import get_paths, default_excel
from src.helpers.io import load_sheet, detect_week_columns, coerce_numeric, write_parquet
```

Solo `paths.py` e `io.py`. Sin lógica de negocio — eso vive en los notebooks.
