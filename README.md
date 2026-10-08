# Real-Time Multi-Speaker Meeting Intelligence

Team 7 — Major Project 298A — Topic 21

This project studies real-time meeting intelligence for multi-speaker meetings. The system combines speaker diarization, automatic speech recognition, speaker-attributed transcripts, and grounded action-item extraction.

## Project scope

The 298A prototype will:

1. Prepare a reproducible AMI Meeting Corpus evaluation sample.
2. Run a pyannote.audio 2.1 diarization baseline.
3. Transcribe diarized speech and produce speaker-attributed output.
4. Extract action items with evidence from the transcript.
5. Measure diarization error rate, transcription quality, action-item quality, and latency.
6. Provide a simple local demo and a reproducible evaluation command.

AMI is the primary benchmark. NOTSOFAR-1 is reserved as a future far-field benchmark. QMSum may support initial transcript/action-item experiments, but its labels must not be treated as direct owner/deadline annotations without additional annotation.

## Team

| Member | Responsibility |
|---|---|
| Aashima Taneja | Dataset preparation, manifests, cleaning, and EDA |
| Anurag Sarma Josyula | Technical integration, baseline pipeline, and reproducibility |
| Chelsi Shulamite Elthuri | Project management, documentation, and workflow |
| Kanika Mamgain | Literature review, metrics, and evaluation |
| Shashira Guntuka | Demo, action-item presentation, risks, and failure analysis |

## Repository structure

```text
.
├── configs/              # Reproducible YAML configuration files
├── data/
│   ├── raw/              # Restricted/local data; never commit raw audio
│   ├── processed/        # Local processed data; ignored by Git
│   └── manifests/        # Shareable metadata/manifests only
├── docs/                 # Protocols, risks, literature, and demo notes
├── notebooks/            # Dataset exploration and analysis notebooks
├── outputs/              # Local predictions, metrics, and logs
├── src/
│   ├── demo/             # Local demonstration interface
│   ├── evaluation/       # DER, WER/tcpWER, action-item, and latency metrics
│   ├── extraction/       # Grounded action-item extraction
│   └── pipeline/         # Diarization, ASR, and orchestration
├── tests/                # Unit and smoke tests
├── .env.example          # Local environment-variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Important data rule

Do not commit AMI audio, restricted annotations, access tokens, Hugging Face tokens, `.env` files, model caches, or generated large outputs. Store restricted data locally and commit only scripts, configuration templates, documentation, and shareable metadata.

## Setup

### 1. Clone the repository

```bash
git clone <GITHUB-REPOSITORY-URL>
cd <REPOSITORY-DIRECTORY>
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure local credentials

```bash
cp .env.example .env
```

Fill in credentials only on your local machine. Never commit `.env`.

### 4. Add local data

Place downloaded or mounted AMI data under `data/raw/`. Follow `data/README.md` for the expected layout. The repository intentionally does not contain the raw dataset.

## Planned commands

The following commands define the intended interface for the first prototype. They will become runnable as the corresponding issues are implemented.

```bash
# Validate a local dataset manifest
python -m src.pipeline.validate_manifest --config configs/ami_sample.yaml

# Run the diarization + ASR baseline
python -m src.pipeline.run_baseline --config configs/ami_sample.yaml

# Evaluate generated predictions
python -m src.evaluation.evaluate --config configs/ami_sample.yaml

# Launch the local demo
python -m src.demo.app --input outputs/sample_transcript.json
```

## Evaluation protocol

The team will report results only after the run is completed and reproducible.

| Area | Planned measure |
|---|---|
| Speaker diarization | DER |
| Speech recognition | WER and/or tcpWER, depending on reference availability |
| Action items | Precision, recall, and F1 using a documented annotation protocol |
| Real-time behavior | End-to-end p95 latency; target below 3 seconds |
| Robustness | Categorized failures involving overlap, noise, attribution, and missing fields |

The published pyannote baseline value is a reference point, not a result of this project. Do not claim a reproduced score until the team has run the fixed protocol and saved the evidence.

## Development workflow

Each task must be traceable:

```text
Linear issue → feature branch → meaningful commit → pull request → review → merge → Linear Done
```

Use the exact Linear issue ID in the branch and commit message:

```bash
git checkout -b <LINEAR-ID>-short-description
git add <files>
git commit -m "<LINEAR-ID>: describe the implementation"
git push -u origin <LINEAR-ID>-short-description
```

Pull requests should explain:

- What changed
- Which Linear issue it addresses
- How to run it
- What test or evidence was produced
- Known limitations

Do not push directly to `main`.

## 298A success criteria

- A new contributor can install the project from this README.
- A dataset manifest can be validated without manually editing source code.
- A sample AMI meeting can pass through the baseline pipeline.
- The output contains timestamps, speaker labels, and transcript text.
- Evaluation produces a documented result or a clear pending status.
- Action items include supporting evidence and do not invent missing owners or deadlines.
- At least one smoke test and one categorized failure analysis are included.

## Current status

This initial commit establishes the repository structure and reproducibility contract. Model results, benchmark numbers, and final action-item scores remain pending until the team runs and documents them.

