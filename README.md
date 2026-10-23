# EdgePulse: Rural Triage & Specialist Dispatch Agent

An AWS hackathon prototype that routes messy rural patient notes to a medical specialty and uses Amazon Bedrock to generate a cautious clinical summary.

The system implements a **hybrid edge-cloud architecture**:
1. **Local Routing (Edge)**: A local Strands Decider 2B classifier performs fast, typed policy classification to determine both urgency (Emergency vs. Stable) and the best-fit medical specialty.
2. **Clinical Summary (Cloud/Local)**: Amazon Bedrock turns the patient note and routing result into a professional clinical hand-off summary. If the cloud is unavailable, the system falls back to a local Ollama model (`qwen2.5:0.5b`) or a deterministic "Safe Mode" fallback.

This is routing support, not diagnosis. Do not use it as the sole basis for medical or emergency decisions.

## Architecture: Two-Decision Logic
To prevent over-routing to Emergency Medicine, EdgePulse splits routing into two independent decisions:
- **Urgency Check**: A binary decision on whether the case is a life-threatening emergency.
- **Specialty Selection**: A separate classification into specialized fields (e.g., Cardiology, Neurology).

Cases are flagged for **Human Clinical Review** if:
- The urgency certainty is low (`max(p, 1-p) < 0.70`).
- The specialty score margin is low (`top_score - second_score < 0.10`).
- Two or more specialties score $\ge 0.50$ (conflicting high confidence).

## Files

```text
app.py                                Streamlit dashboard (UI)
agent.py                                Bedrock agent loop
decider_patterns/
  __init__.py                             Package export
  specialty_policy_decider.py             Reusable Decider wrapper
simulation_test.py                         Holdout set accuracy & latency tests
test_triage.py                             Wrapper unit tests
requirements.txt                           Runtime dependencies
README.md                                  This guide
LICENSE                                    MIT license
```

## Prerequisites

- Python 3.11 or newer.
- AWS credentials configured through an AWS profile, SSO, or role.
- AWS CLI v2 recommended for checking credentials and Bedrock access.
- A local `strands-decider` installation.
- Bedrock model access and quota in the selected AWS region.

Never put AWS credentials or patient data in source files, command history,
logs, or committed environment files.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The repository's existing `.venv` can be reused:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Check the local tools and AWS identity:

```bash
strands-decider --help
aws --version
aws sts get-caller-identity
```

If `aws sts get-caller-identity` fails, authenticate before continuing. The
application cannot invoke Bedrock without valid credentials.

## Run the system

### Option 1: Streamlit Dashboard (Recommended)
1. Start the Strands Decider server (see below).
2. Run: `streamlit run app.py`

### Option 2: CLI Agent
1. Start the Strands Decider server (see below).
2. Run:
```bash
AWS_REGION=us-east-1 \
BEDROCK_MODEL=us.amazon.nova-lite-v1:0 \
.venv/bin/python agent.py \
"patient with crushing chest pain, sweating, and shortness of breath"
```

### Starting Strands Decider (Required for both)
In a separate terminal:
```bash
strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8000
```
Wait for the model to load, then verify it:
```bash
curl --fail http://127.0.0.1:8000/health
```

## Test the Decider without Bedrock

With the Decider server running:
```bash
.venv/bin/python simulation_test.py
```
This runs the original smoke tests and a 20+ case holdout set, printing:
- selected specialty;
- expected specialty;
- accuracy and median latency.

## Run automated tests

The unit tests do not require a running Decider server or live Bedrock:
```bash
.venv/bin/python -m unittest -v test_triage.py
```

Run syntax validation:
```bash
.venv/bin/python -m compileall -q agent.py decider_patterns simulation_test.py
```

## Reusable Decider pattern

`decider_patterns/specialty_policy_decider.py` exposes `SpecialtyPolicyDecider`.
It uses typed `noul` questions for urgency and each specialty.

The returned dictionary has this shape:
```python
{
    "best_choice": "neurology",
    "raw_scores": {
        "cardiology": 0.18,
        "neurology": 0.91,
        "pediatrics": 0.10,
        # ...
    },
    "confidence": 0.91,
    "margin": 0.36,
    "is_emergency": True,
    "urgency_confidence": 0.85,
    "latency_ms": 420.0,
}
```

## Limitations & Safety

- **Prototype Status**: This is a hackathon prototype. It has not been clinically validated.
- **Routing only**: It provides routing support, not diagnosis.
- **Human-in-the-loop**: Low-margin or low-certainty cases MUST be reviewed by a clinician.
- **Privacy**: This prototype does not implement HIPAA-compliant data retention or encryption.
- **Bedrock Dependence**: Generative summaries require AWS connectivity; local fallback is provided but less capable.
- **Calibration Note**: The review rules were calibrated after the initial simulation run. The holdout set was re-run after implementing the multi-specialty rule.
- **Model Detail**: Raw scores are not normalized probabilities. There is currently no specific 'Trauma' option. Patient life stage is collected in the UI but not used by the edge classifier.

## Safety and production checklist

Before any real pilot:
- obtain clinical review and governance approval;
- use a de-identified, clinician-labeled evaluation set;
- implement an emergency override independent of model confidence;
- send low-margin or conflicting cases to a qualified human;
- add authentication, authorization, encryption, audit logging, and retention
  controls for patient data;
- avoid logging raw patient notes;
- evaluate Bedrock Guardrails and PII logging implications;
- replace printed output with an authenticated dispatch workflow;
- test failure modes, stale data, network loss, and model unavailability.
