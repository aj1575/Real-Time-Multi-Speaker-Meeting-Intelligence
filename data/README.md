# Data layout

Restricted AMI audio and annotations stay on local machines only. Never commit wav files or private credentials.

## Current local sample (Part A)

| Item | Path |
|---|---|
| Meeting | `ES2002a` |
| Headset mix | `data/raw/amicorpus/ES2002a/audio/ES2002a.Mix-Headset.wav` |
| Individual headsets | `data/raw/amicorpus/ES2002a/audio/ES2002a.Headset-{0-3}.wav` |
| Manual annotations | `data/raw/` (unzipped `ami_public_manual_1.6.2`) |
| Segment XML | `data/raw/segments/ES2002a.*.segments.xml` |
| Shareable manifest | `data/manifests/ami_sample.json` |

## Datasets

### AMI Meeting Corpus (primary)

- Use for diarization, ASR, and speaker-attributed transcripts.
- Part A sample uses **headset-mix** audio for meeting `ES2002a`.
- Download signals from the AMI chooser; download **manual annotations v1.6.2**.
- License: CC BY 4.0 (`data/raw/CCBY4.0.txt` / `LICENCE.txt`).

### NOTSOFAR-1 (future)

Reserved as the far-field benchmark. Do not treat as required for the 298A sample pipeline.

### QMSum (text / action-item experiments)

May support early transcript and action-item experiments. Labels are **not** direct owner/deadline annotations unless the team adds further annotation.

## Expected tree

```text
data/
├── raw/                 # Local only; ignored by Git except placeholders
│   ├── amicorpus/
│   │   └── ES2002a/audio/*.wav
│   ├── segments/
│   └── ami_public_manual_1.6.2.zip
├── processed/           # Intermediate artifacts; ignored
└── manifests/           # Shareable metadata only
```

## Download / setup

1. Install `wget` on Windows.
2. From `data/raw`, run the AMI-generated batch script or `download_ami.bat`.
3. Download `ami_public_manual_1.6.2.zip` into `data/raw` and unzip there.
4. Confirm:

```powershell
Test-Path data\raw\amicorpus\ES2002a\audio\ES2002a.Mix-Headset.wav
Test-Path data\raw\segments\ES2002a.A.segments.xml
```

5. Validate the shareable manifest:

```bash
python -m src.pipeline.validate_manifest --config configs/ami_sample.yaml
```

## Rules

- Do not commit raw audio, full restricted annotation dumps beyond what the team agrees is shareable, access tokens, or `.env`.
- Commit only scripts, configuration templates, documentation, and shareable manifests.
