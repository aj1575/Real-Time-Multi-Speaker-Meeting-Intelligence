# Risks and failure modes

| Risk | Impact | Mitigation |
|---|---|---|
| Restricted AMI data committed by mistake | License / compliance failure | `.gitignore` for `data/raw` and review before push |
| Missing Hugging Face / model access | Baseline cannot run | Keep models optional in `requirements.txt` until approved |
| Invented owners or deadlines in action items | Unreliable intelligence | Require transcript evidence; leave fields empty when absent |
| Unreproducible metrics | Invalid 298A claims | Config-driven runs; save manifests and outputs |
| Overlap / noise degradation | High DER / WER | Log categorized failures for analysis |
