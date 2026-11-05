# Local setup guide (macOS) — Team 7

Use this on a Mac to run the AMI baseline. Raw audio stays on your laptop and is never committed to GitHub.

## What you will have after setup

- Python 3.12 virtual environment (avoid 3.13/3.14 for the ML stack)
- AMI sample meeting `ES2002a` audio + manual annotations
- Hugging Face access for gated pyannote models
- A working command:

```bash
python -m src.pipeline.run_baseline --config configs/ami_sample.yaml
```

Default config runs the **first 60 seconds** of the meeting (~2 minutes on a typical Mac).

---

## 0. One-time Mac tools

Install Homebrew if you do not already have it: https://brew.sh

Then:

```bash
brew install git wget python@3.12
```

Confirm:

```bash
git --version
wget --version | head -n 1
python3.12 --version
```

---

## 1. Clone the repo

```bash
git clone https://github.com/aj1575/Real-Time-Multi-Speaker-Meeting-Intelligence.git
cd Real-Time-Multi-Speaker-Meeting-Intelligence
```

If you already cloned, pull the latest branch you were asked to use.

---

## 2. Create and activate a Python 3.12 venv

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

You should see `(.venv)` in your terminal prompt. Activate it again whenever you open a new terminal:

```bash
cd /path/to/Real-Time-Multi-Speaker-Meeting-Intelligence
source .venv/bin/activate
```

---

## 3. Install dependencies inside `.venv`

### Base packages

```bash
pip install -r requirements.txt
```

### ML stack (macOS)

On Mac, install PyTorch from the normal PyPI index (Apple Silicon and Intel both work with this path):

```bash
pip install "torch==2.5.1" "torchaudio==2.5.1"
pip install "transformers>=4.36,<5" "huggingface_hub>=0.20" "pyannote.audio>=3.1,<4"
```

Quick check:

```bash
python -c "import torch, torchaudio, pyannote.audio; print(torch.__version__, torchaudio.__version__, 'mps=', torch.backends.mps.is_available())"
```

`mps` may print `True` on Apple Silicon. The config uses `device: auto` and currently resolves to CPU-safe defaults in our pipeline; the important part is that imports succeed.

---

## 4. Hugging Face token and gated model access

1. Create a token: https://huggingface.co/settings/tokens  
2. Create your local env file:

```bash
cp .env.example .env
```

3. Edit `.env` and set:

```text
HF_TOKEN=hf_your_token_here
```

You can edit with TextEdit:

```bash
open -a TextEdit .env
```

4. In a browser, log into the **same** Hugging Face account and accept access on:

- https://huggingface.co/pyannote/speaker-diarization-3.1  
- https://huggingface.co/pyannote/segmentation-3.0  
- https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM  

Click **Agree and access repository** on each page.

5. Never commit `.env`. Never paste tokens into Slack, Linear, or GitHub.

Quick check:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); from huggingface_hub import HfApi; print(HfApi(token=os.getenv('HF_TOKEN')).whoami()['name'])"
```

---

## 5. Download the AMI sample (local only)

Meeting: **ES2002a**  
Audio: headset mix + individual headsets (~194 MB)  
Annotations: AMI manual annotations v1.6.2

### 5a. Download audio into `data/raw`

From the repo root:

```bash
mkdir -p data/raw
cd data/raw

wget -P amicorpus/ES2002a/audio https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2002a/audio/ES2002a.Mix-Headset.wav
wget -P amicorpus/ES2002a/audio https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2002a/audio/ES2002a.Headset-0.wav
wget -P amicorpus/ES2002a/audio https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2002a/audio/ES2002a.Headset-1.wav
wget -P amicorpus/ES2002a/audio https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2002a/audio/ES2002a.Headset-2.wav
wget -P amicorpus/ES2002a/audio https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2002a/audio/ES2002a.Headset-3.wav

cd ../..
```

Optional: use the AMI chooser at https://groups.inf.ed.ac.uk/ami/download/  
Select **ES2002** + **a**, then **Headset mix** and **Individual headsets**, copy the **shell script**, save it as `data/raw/download_ami.sh`, then:

```bash
cd data/raw
chmod +x download_ami.sh
./download_ami.sh
cd ../..
```

### 5b. Download and unzip annotations

1. From the AMI site, download **AMI manual annotations v1.6.2**.
2. Move the zip into `data/raw/`:

```bash
# Example if it landed in Downloads:
mv ~/Downloads/ami_public_manual_1.6.2.zip data/raw/
cd data/raw
unzip -o ami_public_manual_1.6.2.zip
cd ../..
```

You should now see folders such as `data/raw/segments` and `data/raw/words`.

You can delete the zip after unzipping to save space:

```bash
rm data/raw/ami_public_manual_1.6.2.zip
```

### 5c. Confirm paths

```bash
test -f data/raw/amicorpus/ES2002a/audio/ES2002a.Mix-Headset.wav && echo "audio OK"
test -f data/raw/segments/ES2002a.A.segments.xml && echo "annotations OK"
```

Do **not** commit wav files, annotation zips, or large annotation dumps.

---

## 6. Validate and run the baseline

With `.venv` activated, from the repo root:

```bash
python -m src.pipeline.validate_manifest --config configs/ami_sample.yaml
python -m src.pipeline.run_baseline --config configs/ami_sample.yaml
```

Expected success:

- Terminal shows `Meeting: ES2002a` and a non-zero segment count
- Files created:
  - `outputs/ES2002a_transcript.json`
  - `outputs/ES2002a_transcript.txt`

Preview:

```bash
head -n 20 outputs/ES2002a_transcript.txt
```

Optional tests:

```bash
python -m pytest tests/test_smoke.py tests/test_pipeline_smoke.py -q
```

### Config notes (`configs/ami_sample.yaml`)

| Setting | Meaning |
|---|---|
| `data.meeting_id` | `ES2002a` |
| `data.audio_path` | Mix-Headset wav path |
| `pipeline.max_duration_seconds: 60` | Short smoke window |
| `pipeline.diarization.model` | `pyannote/speaker-diarization-3.1` |
| `pipeline.asr.model` | `openai/whisper-tiny` |

To process more audio, raise `max_duration_seconds` or set it to `null`. Full-meeting runs take much longer.

---

## 7. Demo the transcript (optional)

```bash
python -m src.demo.app --input outputs/ES2002a_transcript.json
```

---

## Troubleshooting (Mac)

| Problem | Fix |
|---|---|
| `command not found: python3.12` | `brew install python@3.12` and retry |
| `No module named 'torch'` / `pyannote` | `source .venv/bin/activate`, then reinstall section 3 |
| `Missing model access: set HF_TOKEN` | Create `.env` and set `HF_TOKEN` |
| Gated model 403 / restricted access | Accept all three pyannote pages while logged into the same HF account |
| `Missing audio` | Re-run the `wget` commands; confirm paths with `test -f ...` |
| `unzip: command not found` | `brew install unzip` |
| SSL / certificate errors on wget | Update Homebrew packages, or try `curl -L -o` for each file |
| Very slow first run | Normal: models download into `~/.cache/huggingface` once |

---

## Team rules

- Linear issue → feature branch (`298-XX-short-name`) → PR → review → merge
- Do not push raw AMI wav files, annotation zips, `.env`, or HF tokens
- Do not claim published DER / WER scores until evaluation evidence is saved
- Safe wording when metrics are incomplete:

```text
Baseline pipeline implemented; metric reproduction pending.
```

---

## Quick checklist

```text
[ ] brew install git wget python@3.12
[ ] Cloned repo
[ ] python3.12 -m venv .venv && source .venv/bin/activate
[ ] pip install -r requirements.txt
[ ] Installed torch / torchaudio / transformers / pyannote.audio
[ ] .env with HF_TOKEN
[ ] Accepted gated pyannote model access
[ ] Downloaded ES2002a audio into data/raw/amicorpus/...
[ ] Unzipped manual annotations into data/raw/
[ ] validate_manifest passes
[ ] run_baseline writes outputs/ES2002a_transcript.*
```
