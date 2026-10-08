# Evaluation protocol

Results are reported only after a completed, reproducible run.

| Area | Measure | Notes |
|---|---|---|
| Speaker diarization | DER | Against AMI reference RTTM |
| Speech recognition | WER and/or tcpWER | Depends on reference availability |
| Action items | Precision, recall, F1 | Documented annotation protocol required |
| Real-time behavior | End-to-end p95 latency | Target below 3 seconds |
| Robustness | Categorized failures | Overlap, noise, attribution, missing fields |

Published pyannote baseline numbers are reference points only. Do not claim a reproduced score until the fixed protocol has been run and evidence is saved under `outputs/`.
