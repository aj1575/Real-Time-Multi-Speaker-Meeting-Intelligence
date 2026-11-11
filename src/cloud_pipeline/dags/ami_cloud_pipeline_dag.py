
import os
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="ami_cloud_transformation_pipeline",
    description="Scheduled AMI dataset transformation using GCS",
    start_date=datetime(2026, 11, 9, tzinfo=timezone.utc),
    schedule="0 9 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "email": os.environ["AIRFLOW_ALERT_EMAIL"],
        "email_on_failure": True,
        "email_on_retry": False,
    },
    tags=["meeting-intelligence", "gcs", "transformation"],
) as dag:

    transform_ami_data = BashOperator(
        task_id="transform_ami_data",
        bash_command=(
            "python /opt/airflow/dags/transform_ami_cloud.py "
            "--bucket meeting-intelligence-data-514219 "
            "--output-prefix processed/ami_sample_v1"
        ),
    )
