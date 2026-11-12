
import os
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="ami_full_170_transformation_pipeline",
    description="Scheduled transformation of all 170 AMI meetings using GCS",
    start_date=datetime(2026, 11, 12, tzinfo=timezone.utc),
    schedule="0 9 * * *",
    catchup=False,
    is_paused_upon_creation=True,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "email": os.environ["AIRFLOW_ALERT_EMAIL"],
        "email_on_failure": True,
        "email_on_retry": False,
    },
    tags=[
        "meeting-intelligence",
        "gcs",
        "full-dataset",
        "transformation",
    ],
) as dag:

    transform_ami_full_170 = BashOperator(
        task_id="transform_ami_full_170",
        bash_command=(
            "python /opt/airflow/dags/transform_ami_batch_170.py "
            "--bucket meeting-intelligence-data-514219 "
            "--manifest-blob raw/ami_full_170/ami_full_170_manifest.json "
            "--output-prefix processed/ami_full_170_v1 "
            "--output-dir /tmp/ami_full_170_processed"
        ),
    )
