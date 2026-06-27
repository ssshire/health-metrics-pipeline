# health-metrics-pipeline

ELT pipeline for CDC PLACES chronic disease data using Airflow, dbt, and PostgreSQL.

## Architecture

```
CDC PLACES API
     ↓  ingest/ingest.py  (requests)
MinIO  →  s3://health-metrics-raw/raw/places_county_<date>.csv
     ↓  Airflow DAG  (weekly)
PostgreSQL  raw.places_county
     ↓  dbt staging
staging.stg_places_county  (view)
     ↓  dbt mart
marts.county_health_summary  (table)
```

## Dataset

Source: [CDC PLACES — Local Data for Better Health, County Data](https://data.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-County-Data-20/swc5-untb)

County-level prevalence estimates for chronic disease measures across the US (obesity, diabetes, hypertension, etc).

## Quickstart

```bash
cp .env.example .env
docker compose up
```

Airflow UI: http://localhost:8080  
MinIO console: http://localhost:9001

Enable the `health_metrics_ingest` DAG in the Airflow UI to trigger the first run.

## Stack

| Layer | Tool |
|---|---|
| Ingestion | Python + Apache Airflow 2.8 |
| Storage | MinIO (S3-compatible, local) |
| Transform | dbt + PostgreSQL 15 |
| CI/CD | GitHub Actions |

## Project structure

```
ingest/         # Python ingest script (CDC download → MinIO upload)
dags/           # Airflow DAG definitions
transform/      # dbt project (staging + marts models)
.github/        # GitHub Actions CI workflow
```

## Current status (v1)

| Component | Status | Notes |
|-----------|--------|-------|
| CDC PLACES download | Done | `ingest/ingest.py` — fetches full county CSV via Socrata API |
| MinIO upload | Done | Uploads to `health-metrics-raw/raw/places_county_<date>.csv` |
| Airflow DAG | Done | `dags/health_metrics_dag.py` — runs weekly, calls `ingest.run()` |
| dbt staging model | Done | `stg_places_county` — renames, casts, filters nulls |
| dbt mart model | Done | `county_health_summary` — materialized table for querying |
| dbt tests | Done | `not_null` checks on `county_fips`, `measure`, `data_value`, `year` |
| GitHub Actions CI | Done | Lints Python + parses dbt on every push and PR |
| MinIO → Postgres load | Not started | Blocks dbt from running end-to-end |
| Airflow container deps | Not started | Blocks DAG from executing in Docker |
| Terraform | Not started | Planned for v2 |

## Local testing

Run these before committing to catch the same issues CI checks.

**Setup (first time only)**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install ruff dbt-postgres
```

**Lint Python**
```bash
source venv/bin/activate
ruff check ingest/ dags/
```

**Validate dbt project structure**
```bash
source venv/bin/activate
cd transform
POSTGRES_USER=airflow POSTGRES_PASSWORD=airflow POSTGRES_DB=airflow dbt parse --profiles-dir .
```

Both commands should complete with no errors before pushing.

## Known gaps (v2 work)

These are not blocking CI but are required before the pipeline runs end-to-end locally.

- [ ] **MinIO → Postgres load missing** — `ingest.py` uploads the CSV to MinIO but nothing reads it back into `raw.places_county` in Postgres. dbt has no table to run against. Fix: add a `load_to_postgres()` function in `ingest.py` and a second task in the DAG.
- [ ] **Airflow container missing Python deps** — the stock `apache/airflow:2.8.0` image does not have `boto3` or `requests` installed. The DAG will crash on first run. Fix: add `_PIP_ADDITIONAL_REQUIREMENTS: "boto3==1.34.14 requests==2.31.0"` to the `airflow` service in `docker-compose.yml`.