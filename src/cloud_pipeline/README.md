# Cloud Data Pipeline — Real-Time Multi-Speaker Meeting Intelligence

## Overview

This directory contains the cloud data pipeline for the Real-Time Multi-Speaker Meeting Intelligence project (DATA 298A, Team 7).

The pipeline uses Google Cloud Storage (GCS) to store AMI meeting data and Apache Airflow to schedule, execute, and monitor data transformations.

The implemented pipeline processes an AMI sample, validates speaker annotations, and generates structured speaker-segment and meeting-level outputs.

**Deployment status:** Google Cloud Storage is cloud-hosted. Apache Airflow runs locally using Docker Compose. This is an automated pipeline while the Airflow services are running; it is not an always-on Cloud Composer deployment.

## Architecture

```
AMI Meeting Dataset
        |
        v
Google Cloud Storage — raw/
        |
        v
Apache Airflow — scheduled DAG
        |
        v
Python transformation and validation
        |
        v
Google Cloud Storage — processed/ami_sample_v1/
        |
        +--> Speaker segments (CSV/JSON)
        +--> Speaker statistics (CSV)
        +--> Meeting metadata (CSV)
        +--> Transformation summary (JSON)
Monitoring:
Airflow run status + task logs + 2 retries + failure email alerts
```

## Repository Structure

```
src/cloud_pipeline/
├── dags/
│   ├── ami_cloud_pipeline_dag.py
│   ├── ami_corrupted_input_test_dag.py
│   ├── transform_ami_cloud.py
│   ├── alert_subject.txt
│   └── alert_body.html
├── docker-compose.yaml
├── docker-compose.override.yaml
├── Dockerfile
├── requirements-airflow.txt
├── airflow.env.example
├── smtp.env.example
└── README.md
```

The following local files are intentionally excluded from Git:

- `.env`
- `.smtp.env`
- `credentials/airflow-service-account.json`

Never commit SMTP passwords, Google Cloud service-account keys, or restricted meeting audio.

## Software and Dependencies

- Docker Desktop with Docker Compose
- Apache Airflow 3.1.5
- Python 3.12 inside the Airflow container
- `google-cloud-storage==3.7.0`
- `apache-airflow-providers-standard==1.10.0`
- Google Cloud Storage access with appropriate permissions

The custom Dockerfile installs the required Python packages.

## Google Cloud Storage Layout

The current configuration uses:

**Project:** `charming-league-514219-g4`

**Bucket:** `meeting-intelligence-data-514219`

```
gs://meeting-intelligence-data-514219/
├── raw/
│   ├── ami_sample.json
│   └── AMI source audio/annotation files
├── processed/
│   └── ami_sample_v1/
│       ├── speaker_segments.csv
│       ├── speaker_segments.json
│       ├── speaker_stats.csv
│       ├── meeting_metadata.csv
│       └── transformation_summary.json
└── tests/
    └── corrupted_ami_manifest.json
```

The input files must already exist in the bucket before executing the DAG. The repository does not include restricted AMI recordings or private credentials.

This cloud pipeline demonstrates a sample transformation. It is separate from the team's full 170-meeting Notebook 01 workflow, which creates Parquet tables and a local DuckDB warehouse.

## Setup Instructions

### 1. Clone the project and select the branch

```
git clone https://github.com/aj1575/Real-Time-Multi-Speaker-Meeting-Intelligence.git
cd Real-Time-Multi-Speaker-Meeting-Intelligence
git switch feature/cloud-pipeline
cd src/cloud_pipeline
```

### 2. Create the Airflow environment file

Copy `airflow.env.example` to `.env`.

On Windows Command Prompt:

```
copy airflow.env.example .env
```

The file contains:

```
AIRFLOW_UID=50000
AIRFLOW_PROJ_DIR=.
```

### 3. Configure Google Cloud authentication

Use a Google Cloud service account with permission to read and write the required bucket objects.

Place its JSON key locally at:

```
credentials/airflow-service-account.json
```

The Docker Compose override mounts the key read-only inside the Airflow worker.

Never upload the key to GitHub. Other developers should obtain their own authorized credentials.

### 4. Configure email notifications

Copy the example SMTP configuration:

```
copy smtp.env.example .smtp.env
```

Edit `.smtp.env` locally to configure a permitted SMTP account and the recipient email address.

For Gmail, use an App Password rather than a normal account password, where supported.

The current setup also requires an Airflow SMTP connection with ID `smtp_default`, containing the SMTP login credentials.

Keep `.smtp.env` outside Git commits.

### 5. Build the Airflow Docker image

```
docker compose build
```

The Dockerfile installs the pinned Python packages.

### 6. Initialize Airflow

```
docker compose up airflow-init
```

For the included development Compose setup, Airflow's initial local administrator credentials follow the configuration in `docker-compose.yaml`. Change default credentials before any nonlocal deployment.

### 7. Start Airflow

```
docker compose up -d
```

Open the local Airflow dashboard:

[http://localhost:8080](http://localhost:8080/)

The services must be running for scheduled executions and notifications to operate.

### 8. Verify DAG imports

```
docker compose exec airflow-dag-processor airflow dags list-import-errors
```

Expected result:

```
No data found
```

This verifies that Airflow has not detected import errors; it does not by itself prove successful execution.

## Main Transformation DAG

**DAG ID:** `ami_cloud_transformation_pipeline`

**Task ID:** `transform_ami_data`

The DAG invokes `transform_ami_cloud.py`, which reads the configured AMI sample from GCS, validates the source information, transforms speaker annotations, and writes the processed outputs back to GCS.

Current schedule:

```
schedule="0 9 * * *"
```

This schedules the DAG daily at 09:00 UTC.

Other settings include:

- `catchup=False`
- `max_active_runs=1`
- Two automatic retries
- Two-minute retry delay
- Failure notification enabled
- No email on intermediate retries

## Transformation Outputs and Verification

The verified sample transformation generated:

| Output file | Description |
|---|---|
| `speaker_segments.csv` | Speaker-segment records |
| `speaker_segments.json` | Speaker segments in JSON |
| `speaker_stats.csv` | Aggregated speaker-level statistics |
| `meeting_metadata.csv` | Meeting-level metadata |
| `transformation_summary.json` | Processing and validation summary |

Previously verified sample statistics:

| Metric | Result |
|---|---:|
| Speaker segments | 277 |
| Speakers | 4 |
| Reported validation issues | 0 |

To verify the data, open the processed GCS prefix and inspect the generated objects, CSV headers, sample rows, and transformation summary.

These values describe the tested AMI sample, not the full 170-meeting dataset.

## Monitoring and Logs

Use the Airflow dashboard to inspect:

- DAG run history and execution state
- Automatically scheduled successful runs
- Task logs from `transform_ami_data`
- Retry attempts and failure states
- Automatic failure notifications

For the ISA demonstration, select a real successful **scheduled** run and open its task logs.

The earlier schedule was every 30 minutes for automation verification. It was subsequently changed to once daily to avoid unnecessary repeated processing.

## Corrupted-Input Sanity Test

**Test DAG ID:** `ami_corrupted_input_test`

This DAG uses an intentionally corrupted manifest stored separately at:

```
gs://meeting-intelligence-data-514219/tests/corrupted_ami_manifest.json
```

The corrupted manifest contains an invalid meeting identifier.

The validation script rejects the inconsistent source data. An earlier test produced:

```
ValueError: Unexpected segment filename: ES2002a.A.segments.xml
```

The failed task was retried twice and then marked as failed.

The original input remained unchanged.

The test DAG should remain paused except when performing an intentional demonstration.

## Email Failure Alerts

Automatic failure notifications are sent after the configured retry attempts have been exhausted.

The project uses:

- `alert_subject.txt` for the subject
- `alert_body.html` for the formatted message
- `.smtp.env` for private SMTP settings
- Airflow connection `smtp_default` for SMTP authentication

The verified test generated a customized notification with the subject:

```
[FAILED] Meeting Intelligence | ami_corrupted_input_test
```

The message contains task details, the attempt number, error information, and a link to Airflow logs.

The main DAG has also been configured to send failure notifications, but no intentional production-DAG failure was performed.

## Demonstration Checklist

For Checkpoint 3B, demonstrate:

1\. Raw AMI files stored in GCS.

2\. The active scheduled Airflow DAG.

3\. A successful automatically scheduled run.

4\. A real task execution log.

5\. The five processed GCS output files and their schemas.

6\. The corrupted-input sanity-check failure.

7\. Automatic retries and final failure status.

8\. The received customized failure email.

## Limitations

This implementation is a sample cloud data pipeline rather than the complete deployed meeting-intelligence prototype.

Airflow currently runs locally through Docker and stops scheduling when its services are unavailable.

The full team prototype must separately demonstrate a publicly reachable interface, an audience-selected input, a team-built or adapted model, and a real scored output connected to pipeline data.

A successful Docker build or Airflow DAG import does not establish that the full prototype is deployed.

## Security

- Never commit `.env`, `.smtp.env`, or service-account JSON files.
- Never commit restricted AMI audio.
- Use least-privilege Google Cloud permissions.
- Use development defaults only for local testing.
- Verify Git staging before pushing changes.
- Rotate credentials immediately if they are accidentally exposed.

## Project

DATA 298A — Real-Time Multi-Speaker Meeting Intelligence
Team 7 — Section 11
Checkpoint 3 — Cloud Pipeline Demonstration
