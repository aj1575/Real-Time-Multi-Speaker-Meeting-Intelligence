# Data layout

Restricted AMI audio and annotations stay on local machines only.

## Expected layout

```text
data/
├── raw/                 # Downloaded AMI (or mounted) audio + annotations
├── processed/           # Intermediate artifacts from the pipeline
└── manifests/           # Shareable metadata only (safe to commit)
```

## Rules

- Do not commit raw audio, full transcripts with restricted licenses, or access tokens.
- Commit only manifests and documentation that contain no restricted content.
- Point `configs/ami_sample.yaml` at your local paths after download.
