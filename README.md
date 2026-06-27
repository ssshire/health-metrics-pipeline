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

## Running the project

### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python 3.11+

### 2. Start the services

```bash
cp .env.example .env
docker compose up
```

This starts three containers: Postgres, MinIO, and Airflow.

| Service | URL | Credentials |
|---------|-----|------------|
| Airflow UI | http://localhost:8080 | check terminal for generated password |
| MinIO console | http://localhost:9001 | `minioadmin` / `minioadmin` |

### 3. Run the ingest script locally (v1)

> The Airflow DAG cannot run the ingest inside Docker yet (see Known gaps). Run it locally against the Docker MinIO instead.

First update `MINIO_ENDPOINT` in your `.env` — the default points to the Docker-internal hostname which only works inside the container network:

```bash
# in .env, change:
MINIO_ENDPOINT=http://localhost:9000
```

Then run:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python ingest/ingest.py
```

On success you will see:
```
Downloading CDC PLACES data...
Uploaded XXXXX bytes to s3://health-metrics-raw/raw/places_county_<date>.csv
```

Open the MinIO console at http://localhost:9001 → `health-metrics-raw` bucket to verify the file landed.

### 4. dbt (not yet runnable end-to-end)

dbt reads from `raw.places_county` in Postgres. That table does not exist until the MinIO → Postgres load step is built (v2). You can validate the project structure without a database connection:

```bash
source venv/bin/activate
cd transform
POSTGRES_USER=airflow POSTGRES_PASSWORD=airflow POSTGRES_DB=airflow dbt parse --profiles-dir .
```

### 5. Airflow DAG (not yet runnable end-to-end)

The `health_metrics_ingest` DAG will appear in the Airflow UI at http://localhost:8080 but triggering it will fail until the v2 gaps are resolved (missing deps and env vars in the container).

## Stack

| Layer | Tool |
|-------|------|
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
- [ ] **Airflow container missing Python deps and env vars** — the stock `apache/airflow:2.8.0` image does not have `boto3` or `requests` installed, and the `airflow` service in `docker-compose.yml` does not pass the `MINIO_*` variables that `ingest.py` reads. The DAG will crash on import (`ModuleNotFoundError`) and even if deps are installed, `MINIO_ENDPOINT` and `MINIO_BUCKET` will be `None` at runtime. Fix requires two changes in `docker-compose.yml` under the `airflow` service:
  - Add `_PIP_ADDITIONAL_REQUIREMENTS: "boto3==1.34.14 requests==2.31.0"` to install deps at container startup
  - Add `MINIO_ENDPOINT`, `MINIO_BUCKET`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` to the `environment` block so `ingest.py` can read them via `os.getenv()`