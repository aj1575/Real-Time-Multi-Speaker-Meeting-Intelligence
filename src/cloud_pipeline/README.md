# Cloud Data Pipeline — Real-Time Multi-Speaker Meeting Intelligence

## 1. Overview

This directory contains the cloud data pipeline for the **Real-Time Multi-Speaker Meeting Intelligence** project, developed as part of DATA 298A at San José State University.

The pipeline uses **Google Cloud Storage (GCS)** for storing raw and processed meeting data and **Apache Airflow** for scheduling, executing, and monitoring data transformations.

Two transformation workflows have been implemented:

1. **Sample transformation pipeline:** Processes one AMI meeting, validates speaker annotations, and generates five structured output files.
2. **Full-dataset transformation pipeline:** Processes 170 AMI meetings, validates speaker timestamps and audio metadata, and generates seven structured output files.

The full-dataset pipeline has been successfully executed and verified using Apache Airflow.

**Deployment:** Google Cloud Storage is cloud-hosted, while Apache Airflow runs locally using Docker Compose. Automatic scheduling works while the Airflow services are running. This is not a managed Google Cloud Composer deployment.

---

## 2. Pipeline Architecture

```text
                  AMI Meeting Corpus
                          |
                          v
                 Google Cloud Storage
                       raw/
                          |
            +-------------+-------------+
            |                           |
            v                           v
    Sample AMI Pipeline         Full AMI Dataset Pipeline
      (1 meeting)                    (170 meetings)
            |                           |
            v                           v
    Apache Airflow DAG          Apache Airflow DAG
            |                           |
            v                           v
    Python Transformation       Python Transformation
            |                           |
            v                           v
    Speaker Annotation          Speaker Annotation
    Parsing and Validation      Parsing and Validation
            |                           |
            v                           v
    processed/ami_sample_v1/     processed/ami_full_170_v1/
            |                           |
            v                           v
       5 Output Files               7 Output Files

                  Monitoring and Management
                          |
                          v
          Airflow Logs, Task Status, Retries,
                 and Failure Email Alerts
```

Airflow manages when the transformations run, tracks their execution, and reports task failures.

The Python scripts perform the data processing, while GCS stores the input and output files.

---

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Google Cloud Storage | Stores raw AMI data and processed outputs |
| Apache Airflow 3.1.5 | Workflow scheduling, orchestration, and monitoring |
| Docker Desktop | Runs the local Airflow environment |
| Docker Compose | Configures Airflow services |
| Python 3.12 | Executes transformation scripts |
| Google Cloud Storage Python SDK | Reads and uploads GCS objects |
| XML parsing | Extracts speaker segments from AMI annotations |
| CSV and JSON | Stores structured transformation results |
| PostgreSQL | Airflow metadata database |
| Redis | Message broker for Airflow's CeleryExecutor |
| SMTP | Failure notification emails |

The custom Dockerfile installs the required Python packages, including `google-cloud-storage==3.7.0` and `apache-airflow-providers-standard==1.10.0`.

---

## 4. Repository Structure

```text
src/cloud_pipeline/
|
|-- batch_170/
|   |-- transform_ami_batch_170.py
|
|-- dags/
|   |-- ami_cloud_pipeline_dag.py
|   |-- ami_full_170_pipeline_dag.py
|   |-- ami_corrupted_input_test_dag.py
|   |-- transform_ami_cloud.py
|   |-- alert_subject.txt
|   |-- alert_body.html
|
|-- docker-compose.yaml
|-- docker-compose.override.yaml
|-- Dockerfile
|-- requirements-airflow.txt
|-- airflow.env.example
|-- smtp.env.example
|-- README.md
```

### Important files

| File | Description |
|---|---|
| `ami_cloud_pipeline_dag.py` | Airflow DAG for the sample transformation |
| `ami_full_170_pipeline_dag.py` | Airflow DAG for the full 170-meeting transformation |
| `transform_ami_cloud.py` | Sample AMI transformation script |
| `transform_ami_batch_170.py` | Full-dataset transformation script |
| `ami_corrupted_input_test_dag.py` | Tests invalid-input handling and failure notifications |
| `docker-compose.yaml` | Main Airflow Docker configuration |
| `docker-compose.override.yaml` | Additional SMTP and credential configuration |
| `Dockerfile` | Builds the custom Airflow image |
| `alert_subject.txt` | Failure email subject template |
| `alert_body.html` | Failure email HTML template |

Local credentials, environment files, audio recordings, Python caches, and backup scripts are excluded from Git commits.

---

## 5. Google Cloud Storage Configuration

**Google Cloud project:** `charming-league-514219-g4`

**GCS bucket:** `meeting-intelligence-data-514219`

### GCS directory structure

```text
gs://meeting-intelligence-data-514219/
|
|-- raw/
|   |-- ami_sample.json
|   |-- ami_public_manual_1.6.2.zip
|   |-- amicorpus/
|   |-- ami_full_170/
|       |-- ami_full_170_manifest.json
|       |-- audio/
|           |-- 170 AMI Mix-Headset WAV recordings
|
|-- processed/
|   |-- ami_sample_v1/
|   |   |-- speaker_segments.csv
|   |   |-- speaker_segments.json
|   |   |-- speaker_stats.csv
|   |   |-- meeting_metadata.csv
|   |   |-- transformation_summary.json
|   |
|   |-- ami_full_170_v1/
|       |-- speaker_segments.csv
|       |-- speaker_segments.json
|       |-- speaker_stats.csv
|       |-- meeting_metadata.csv
|       |-- validation_issues.csv
|       |-- validation_issues.json
|       |-- transformation_summary.json
|
|-- tests/
    |-- corrupted_ami_manifest.json
```

The dataset files are stored in GCS and are not included in this Git repository.

---

## 6. AMI Dataset

The project uses the AMI Meeting Corpus, which contains meeting audio recordings and associated annotations.

For the full cloud pipeline, the following data has been uploaded and verified:

| Dataset information | Value |
|---|---:|
| Meeting recordings | 170 |
| Speaker annotation XML files | 683 |
| Audio storage size | Approximately 10.69 GiB |
| Audio format | WAV |
| Manifest entries | 170 |

### Dataset manifest

The full-dataset manifest is stored at:

```text
raw/ami_full_170/ami_full_170_manifest.json
```

It contains meeting IDs, corresponding GCS audio paths, speaker annotation filenames, and the number of annotation files associated with each meeting.

The pipeline uses the manifest to identify and validate the input data.

The original recordings and annotation files remain unchanged during transformation.

---

## 7. Sample AMI Transformation Pipeline

### Airflow configuration

**DAG ID:** `ami_cloud_transformation_pipeline`

**Task ID:** `transform_ami_data`

**DAG script:** `dags/ami_cloud_pipeline_dag.py`

**Transformation script:** `dags/transform_ami_cloud.py`

The original pipeline processes the AMI meeting sample `ES2002a`.

Its main steps are:

1. Read the sample input information from GCS.
2. Read the associated speaker annotations.
3. Validate speaker segments.
4. Generate structured speaker and meeting information.
5. Upload processed outputs to GCS.

### Sample transformation results

| Metric | Result |
|---|---:|
| Meetings | 1 |
| Speaker segments | 277 |
| Speakers | 4 |
| Reported validation issues | 0 |
| Output files | 5 |

### Sample output location

```text
gs://meeting-intelligence-data-514219/processed/ami_sample_v1/
```

This sample pipeline is preserved separately from the full-dataset pipeline.

---

## 8. Full 170-Meeting Transformation Pipeline

The full-dataset pipeline extends the sample workflow to process all 170 uploaded AMI meeting recordings.

### Airflow configuration

**DAG ID:** `ami_full_170_transformation_pipeline`

**Task ID:** `transform_ami_full_170`

**DAG file:** `dags/ami_full_170_pipeline_dag.py`

**Transformation script:** `batch_170/transform_ami_batch_170.py`

The Airflow DAG uses a BashOperator to execute the Python transformation script.

The tested Airflow environment executes the script at:

```text
/opt/airflow/dags/transform_ami_batch_170.py
```

In the tested local deployment, the script was copied from the repository's `batch_170` folder into the separately installed Airflow environment at:

```text
C:\Users\tarun\meeting-intelligence-airflow\dags\
```

The corresponding DAG file was also installed in that Airflow DAG folder.

The checked-in repository and the locally running Airflow environment are therefore separate locations. When deploying a new version, the relevant scripts must be made available to the Airflow containers.

### Transformation steps

The full-dataset transformation performs the following operations:

1. Downloads the 170-meeting JSON manifest from GCS.
2. Downloads the AMI annotation ZIP archive.
3. Validates the archive and required annotation files.
4. Checks the availability of each WAV recording.
5. Reads WAV metadata, including audio duration, sample rate, and channel count.
6. Parses speaker annotation XML files.
7. Validates segment start and end timestamps.
8. Excludes invalid or completely out-of-bounds segments.
9. Clips segments that partially exceed the recording duration.
10. Records empty speaker annotation files.
11. Calculates speaker-level statistics.
12. Generates CSV and JSON outputs.
13. Uploads the seven processed files to GCS.

The transformation reads WAV metadata without downloading and processing the full audio signals.

This pipeline uses existing ground-truth AMI annotations. It does not perform speech recognition, diarization inference, or real-time meeting analysis.

---

## 9. Full-Dataset Transformation Results

The 170-meeting transformation was successfully executed in Google Colab and subsequently through Apache Airflow.

### Verified results

| Metric | Value |
|---|---:|
| Meetings processed | **170** |
| Annotation files | **683** |
| Valid speaker segments | **93,051** |
| Active speaker-meeting pairs | **678** |
| Total validation issues | **12** |
| Empty annotation files | 5 |
| Invalid timing segments excluded | 2 |
| Out-of-bounds segments excluded | 4 |
| Total excluded segments | **6** |
| Clipped segments | **1** |

### Data validation

Five speaker annotation files contained no segments:

- `EN2002c.D.segments.xml`
- `EN2003a.D.segments.xml`
- `EN2009b.D.segments.xml`
- `EN2009c.D.segments.xml`
- `IN1001.D.segments.xml`

These files were documented rather than treated as transformation failures.

Two segments with invalid timestamps were excluded.

Four segments were excluded because they were entirely outside their recording duration.

One segment was clipped so its end timestamp matched the recording duration.

All corrections and exclusions were recorded in the validation reports.

---

## 10. Full-Dataset Processed Outputs

The full transformation produces seven output files.

**GCS output location:**

```text
gs://meeting-intelligence-data-514219/processed/ami_full_170_v1/
```

| Output file | Description |
|---|---|
| `speaker_segments.csv` | Validated meeting, speaker, and timestamp records |
| `speaker_segments.json` | Speaker-segment records in JSON |
| `speaker_stats.csv` | Number of segments and speech duration per speaker |
| `meeting_metadata.csv` | Audio metadata and active speaker counts per meeting |
| `validation_issues.csv` | Records of invalid, clipped, and empty annotations |
| `validation_issues.json` | Validation records in JSON |
| `transformation_summary.json` | Overall transformation statistics |

All seven files were independently verified in GCS after the successful Airflow execution.

### Output refresh behavior

The pipeline uses a fixed output prefix. Each successful execution uploads new versions of these seven files to the same GCS object paths, replacing the previously stored versions.

The output filenames do not change between runs.

If an upload fails partway through, some objects may already have been replaced. The current implementation does not provide an atomic, all-or-nothing publication mechanism.

---

## 11. Airflow Scheduling and Automation

Both transformation pipelines use Apache Airflow for scheduling and workflow orchestration.

### Full-dataset schedule

```python
schedule="0 9 * * *"
```

This configures the pipeline to run every day at **09:00 UTC** (1:00 AM Pacific Standard Time or 2:00 AM Pacific Daylight Time).

Additional configuration includes:

```python
catchup=False
max_active_runs=1
```

The full-dataset DAG was successfully registered in Airflow and verified with:

```text
is_paused = False
has_import_errors = False
timetable_summary = 0 9 * * *
```

This confirms that the DAG is enabled for automatic scheduling.

### Manual testing versus automatic scheduling

The first full-dataset execution was deliberately triggered manually to verify the transformation.

The successful run does not, by itself, prove that a scheduled run has completed.

The automatic scheduling configuration has been verified, but evidence of the first automatically scheduled execution must be collected separately.

### Local deployment limitation

Airflow runs locally through Docker Compose. The Windows computer and Airflow services must remain running for scheduled transformations to execute.

The project does not currently use Google Cloud Composer or another always-on managed Airflow deployment.

---

## 12. Monitoring, Logs, Retries, and Alerts

Apache Airflow provides monitoring and management for both pipelines.

### Execution monitoring

The Airflow dashboard displays:

- DAG run history and execution states
- Task status
- Execution logs
- Retry attempts
- Failure information
- Scheduled and manually triggered runs

**Local Airflow dashboard:**

http://localhost:8080

### Retry configuration

Both main transformation DAGs are configured with:

```python
"retries": 2,
"retry_delay": timedelta(minutes=2),
"email_on_failure": True,
"email_on_retry": False
```

When a task fails, Airflow is configured to retry it up to two times before marking it as failed.

### Failure email alerts

The pipeline uses SMTP email notifications.

The original sample pipeline includes:

- `alert_subject.txt` for the email subject
- `alert_body.html` for the formatted email body
- `.smtp.env` for local SMTP configuration
- The Airflow SMTP connection `smtp_default`

A corrupted-input test was previously used to verify retry behavior and failure notifications.

The full 170-meeting DAG has failure email notifications configured, but a separate intentional failure test of that DAG has not been performed.

---

## 13. Real Airflow Execution Evidence

The full-dataset pipeline was successfully executed through Apache Airflow.

### Execution details

| Field | Value |
|---|---|
| DAG ID | `ami_full_170_transformation_pipeline` |
| Task ID | `transform_ami_full_170` |
| Run type | Manual test |
| Run ID | `manual__2026-11-12T06:36:32.023477+00:00` |
| Start time | November 12, 2026, 06:40:39 UTC |
| Completion time | November 12, 2026, 06:51:12 UTC |
| Final status | **Success** |

### Actual execution log excerpt

The following excerpt is shortened from the real successful Airflow run:

```text
2026-11-12 06:50:57 INFO [167/170] TS3012a | 201 segments | 4 active speakers
2026-11-12 06:51:00 INFO [168/170] TS3012b | 751 segments | 4 active speakers
2026-11-12 06:51:02 INFO [169/170] TS3012c | 890 segments | 4 active speakers
2026-11-12 06:51:05 INFO [170/170] TS3012d | 769 segments | 4 active speakers

2026-11-12 06:51:07 INFO Uploaded speaker_segments.csv
2026-11-12 06:51:11 INFO Uploaded speaker_segments.json
2026-11-12 06:51:11 INFO Uploaded speaker_stats.csv
2026-11-12 06:51:11 INFO Uploaded meeting_metadata.csv
2026-11-12 06:51:11 INFO Uploaded validation_issues.csv
2026-11-12 06:51:12 INFO Uploaded validation_issues.json
2026-11-12 06:51:12 INFO Uploaded transformation_summary.json

2026-11-12 06:51:12 INFO TRANSFORMATION COMPLETE
2026-11-12 06:51:12 INFO Command exited with return code 0
2026-11-12 06:51:12 INFO Task instance in success state
```

The final transformation summary reported:

```text
Meetings processed: 170
Annotation files: 683
Speaker segments: 93051
Active speaker-meeting pairs: 678
Validation issues: 12
Excluded segments: 6
Clipped segments: 1
Empty annotation files: 5
```

The successful task execution and output data were also verified using the Airflow dashboard and Google Cloud Storage.

---

## 14. Corrupted-Input Validation Test

A separate DAG is available for testing the pipeline's error-handling behavior.

**DAG ID:** `ami_corrupted_input_test`

**Test manifest:**

```text
gs://meeting-intelligence-data-514219/tests/corrupted_ami_manifest.json
```

The test manifest contains an intentionally invalid meeting identifier.

The transformation validation rejects inconsistent input data instead of generating misleading processed results.

An earlier test produced the following error:

```text
ValueError: Unexpected segment filename: ES2002a.A.segments.xml
```

The test task was retried twice before receiving a final failure status.

The original source data remained unchanged.

The corrupted-input DAG should remain paused except during intentional testing.

### Failure notification evidence

The earlier test generated a customized failure email with the subject:

```text
[FAILED] Meeting Intelligence | ami_corrupted_input_test
```

The alert contained task information, error details, and a reference to the Airflow logs.

---

## 15. Local Setup Instructions

### Step 1 — Clone the repository

```bash
git clone https://github.com/aj1575/Real-Time-Multi-Speaker-Meeting-Intelligence.git
cd Real-Time-Multi-Speaker-Meeting-Intelligence
git switch feature/cloud-pipeline
cd src/cloud_pipeline
```

### Step 2 — Create the Airflow environment file

On Windows Command Prompt:

```cmd
copy airflow.env.example .env
```

Configure the required Airflow environment variables.

### Step 3 — Configure GCS credentials

Obtain an authorized Google Cloud service-account key and place it locally at:

```text
credentials/airflow-service-account.json
```

Do not commit this credential file.

The Docker Compose override mounts the credential file read-only into the Airflow worker.

### Step 4 — Configure SMTP

Create the local SMTP configuration file:

```cmd
copy smtp.env.example .smtp.env
```

Configure an authorized SMTP account and the appropriate failure notification recipient.

Ensure that the Airflow connection `smtp_default` is configured when required by the installed SMTP provider.

Never commit SMTP passwords or private tokens.

### Step 5 — Build the Airflow image

```bash
docker compose build
```

### Step 6 — Initialize Airflow

```bash
docker compose up airflow-init
```

### Step 7 — Start Airflow

```bash
docker compose up -d
```

Open:

http://localhost:8080

### Step 8 — Verify DAG registration

```bash
docker compose exec airflow-dag-processor airflow dags list
```

Check for:

```text
ami_cloud_transformation_pipeline
ami_full_170_transformation_pipeline
ami_corrupted_input_test
```

Check import errors:

```bash
docker compose exec airflow-dag-processor airflow dags list-import-errors
```

Expected result:

```text
No data found
```

### Step 9 — Make the batch script available to Airflow

The tested full-dataset DAG expects the transformation script at:

```text
/opt/airflow/dags/transform_ami_batch_170.py
```

For the included repository layout, copy the batch script into the configured Airflow DAG folder before executing the full-dataset DAG.

From the repository's `src/cloud_pipeline` directory on Windows:

```cmd
copy batch_170\transform_ami_batch_170.py dags\transform_ami_batch_170.py
```

If using a separate Airflow installation, copy the script and DAG into that installation's mounted DAG directory instead.

The repository contains the source script in `batch_170/`, while the active Airflow worker must have access to a deployed copy at the path expected by the DAG.

### Step 10 — Verify the outputs

After a successful full-dataset execution, inspect:

```text
gs://meeting-intelligence-data-514219/processed/ami_full_170_v1/
```

Verify that the seven expected files exist and that `transformation_summary.json` contains the correct meeting and segment counts.

---

## 16. Current Limitations and Future Improvements

### Repeated processing

The existing full-dataset pipeline processes the same 170 AMI meetings on every scheduled run.

Because the input data is currently fixed, repeated executions generally produce the same segment counts and replace the same seven output objects.

### Planned improvements

Future improvements may include:

- Detecting new or modified input files before transformation
- Skipping unchanged datasets
- Incrementally processing only new or modified meetings
- Maintaining processing history and input-version metadata
- Publishing output versions without overwriting previous successful results
- Adding additional automated data-quality checks

These capabilities are proposed improvements and are **not currently implemented**.

### Pipeline scope

The cloud pipeline prepares structured AMI annotation data for downstream processing.

It is separate from the team's full 170-meeting Notebook 01 workflow, which creates Parquet tables and a local DuckDB warehouse.

It also does not independently provide real-time audio ingestion, ASR, model-generated diarization, or the complete user-facing meeting intelligence application.

---

## 17. Demonstration Checklist

For the cloud pipeline demonstration, the following evidence can be presented:

1. Raw 170-meeting AMI dataset stored in GCS.
2. Full-dataset manifest and speaker annotations.
3. Python transformation script and Airflow DAG source code.
4. Airflow scheduling configuration showing the DAG is unpaused.
5. Successful manual Airflow run of the 170-meeting pipeline.
6. Real Airflow task execution logs.
7. Seven processed GCS output files.
8. Transformation summary showing 93,051 validated speaker segments.
9. Validation report documenting the 12 recorded issues.
10. Corrupted-input test showing failure handling, automatic retries, and email notification.
11. A successful automatically scheduled run, once independently verified.

---

## 18. Security and Best Practices

- Do not commit Google Cloud service-account JSON files.
- Do not commit SMTP credentials or `.env` files.
- Do not commit restricted AMI audio recordings.
- Use appropriately scoped GCS permissions.
- Preserve original source data.
- Review staged Git files before committing.
- Use the local Docker setup only for development and demonstration unless additional security and availability controls are implemented.
- Rotate any credential immediately if accidentally exposed.

---

## 19. Project Information

**Project:** Real-Time Multi-Speaker Meeting Intelligence

**Course:** DATA 298A

**Team:** Team 7

**Section:** 11

**Component:** Google Cloud Storage and Apache Airflow Data Pipeline

**Current implementation:** Full 170-meeting transformation completed successfully, with automated Airflow scheduling enabled and a successful manually triggered execution verified.