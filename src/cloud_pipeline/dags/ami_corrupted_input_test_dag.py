from datetime import datetime, timedelta, timezone
import os

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="ami_corrupted_input_test",
    description="Test AMI pipeline validation using a corrupted GCS manifest",
    start_date=datetime(2026, 11, 9, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
	"email": os.environ["AIRFLOW_ALERT_EMAIL"],
	"email_on_failure": True,
	"email_on_retry": False,
    },
    tags=["meeting-intelligence", "validation", "failure-test"],
) as dag:

    validate_corrupted_input = BashOperator(
        task_id="validate_corrupted_input",
        bash_command=(
            "python /opt/airflow/dags/transform_ami_cloud.py "
            "--bucket meeting-intelligence-data-514219 "
            "--manifest-blob tests/corrupted_ami_manifest.json "
            "--output-prefix tests/failed_transformation"
        ),
    )