from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys

sys.path.insert(0, "/opt/airflow/ingest")
from ingest import run

with DAG(
    dag_id="health_metrics_ingest",
    start_date=datetime(2024, 1, 1),
    schedule="@weekly",
    catchup=False,
    tags=["health", "cdc", "ingest"],
) as dag:
    ingest_task = PythonOperator(
        task_id="ingest_cdc_places",
        python_callable=run,
    )