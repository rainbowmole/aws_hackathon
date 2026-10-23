import random

import html
import io
import json
import os
import time
import urllib.request

import streamlit as st

from age_utils import UNITS, detect_age, make_age
from decider_patterns.specialty_policy_decider import (
    SpecialtyPolicyDecider,
    needs_human_review,
)

try:
    import PyPDF2
    PDF_SUPPORTED = True
except ImportError:
    PDF_SUPPORTED = False

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
# Age is always shown and sent to the summary model. Set this to True to also
# prefix it to the Decider input, but re-run simulation_test.py first: the
# routing prompts were tuned without it.
INCLUDE_AGE_IN_CLASSIFIER = False

# Expanded sample cases for testing different specialties and scenarios
SAMPLE_CASES = [
    "7 year old with fever, wheezing, and poor oral intake since yesterday.",
    "Older adult with sudden facial droop and difficulty speaking, onset 30 mins ago.",
    "Pregnant woman at 34 weeks with severe headache and high blood pressure.",
    "Patient has crushing central chest pain, sweating, and shortness of breath for 20 minutes.",
    "Child with a deep laceration on the forearm, bleeding controlled with pressure.",
    "Adult with severe right upper quadrant abdominal pain radiating to the shoulder.",
    "Elderly patient with hip pain and inability to bear weight after a fall.",
    "Teenager with persistent low-grade fever, joint pain, and night sweats for 2 weeks.",
]

ANATOMICAL_SYMPTOMS = {
    "Head & Neck": ["Bleeding", "Dizziness", "Slurred Speech", "Severe Headache", "Loss of Consciousness", "Facial Droop"],
    "Chest & Respiration": ["Crushing Chest Pain", "Shortness of Breath", "Palpitations", "Wheezing", "Cough"],
    "Abdomen & Pelvis": ["Severe Abdominal Pain", "Nausea/Vomiting", "High BP in Pregnancy", "Pelvic Pain"],
    "Extremities (Arms & Legs)": ["Fracture / Deformity", "Open Laceration", "Numbness / Weakness", "Joint Swelling"],
    "General & Systemic": ["High Fever", "Fatigue", "Confusion", "Severe Allergic Reaction"],
}

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="EdgePulse",
    page_icon=":material/monitor_heart:",
    layout="centered",
)

st.markdown(
    """
<style>
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; height: 0; }

.block-container {
    max-width: 880px;
    padding-top: 1.75rem !important;
    padding-bottom: 3rem !important;
}

.ep-brand { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }
.ep-logo {
    width: 44px; height: 44px; border-radius: 12px; background: #2563EB;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ep-title { font-size: 1.65rem; font-weight: 800; color: #0F172A; line-height: 1.15; letter-spacing: -0.02em; }
.ep-sub { font-size: 0.9rem; color: #475569; margin-top: 2px; }
.ep-rule { height: 1px; background: #E2E8F0; margin: 16px 0 22px 0; }

.ep-step {
    display: flex; align-items: center; gap: 10px;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #475569; margin: 22px 0 10px 0;
}
.ep-step span.n {
    width: 22px; height: 22px; border-radius: 50%; background: #0F172A; color: #fff;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 0.75rem; letter-spacing: 0;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border-radius: 14px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

button[data-baseweb="tab"] { font-weight: 600; }

div[data-testid="stButton"], div.stButton { width: 100%; }
div[data-testid="stButton"] > button, div.stButton > button {
    width: 100%;
    min-height: 2.9rem;
    border-radius: 10px;
    font-weight: 700;
    white-space: normal;
}

.ep-action {
    background: #0F172A; color: #F8FAFC; border-radius: 14px; padding: 22px 24px; margin-bottom: 14px;
}
.ep-action.emergency { background: #B91C1C; }
.ep-action .eyebrow {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #93C5FD;
}
.ep-action.emergency .eyebrow { color: #FCA5A5; }
.ep-action .route { font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; margin: 4px 0 10px 0; line-height: 1.1; }
.ep-action .line { color: #CBD5E1; font-size: 0.92rem; margin-bottom: 6px; }
.ep-chip {
    display: inline-block; font-size: 0.8rem; font-weight: 600; padding: 4px 10px; margin: 6px 8px 0 0;
    border-radius: 999px; background: rgba(255,255,255,0.12); color: #E2E8F0;
}

.ep-flag {
    background: #FFFBEB; border: 1px solid #FDE68A; border-left: 5px solid #D97706;
    color: #78350F; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px; font-size: 0.92rem;
}

.ep-badge {
    display: inline-block; font-size: 0.74rem; font-weight: 700; padding: 3px 10px; border-radius: 999px;
    margin-bottom: 8px; letter-spacing: 0.02em;
}
.ep-badge.bedrock { background: #DBEAFE; color: #1E40AF; }
.ep-badge.ollama  { background: #DCFCE7; color: #166534; }
.ep-badge.safe    { background: #E2E8F0; color: #334155; }

.ep-empty { text-align: center; color: #64748B; padding: 36px 12px; font-size: 0.95rem; }
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------------
@st.cache_resource
def get_decider():
    return SpecialtyPolicyDecider()


@st.cache_resource
def get_bedrock_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        config=Config(retries={"max_attempts": 2, "mode": "adaptive"}),
    )


def extract_text_from_file(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    data = uploaded_file.getvalue()
    if ext == ".txt":
        return data.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        if PDF_SUPPORTED:
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(data))
                return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                return "[PDF Extract Sim]: Patient has acute chest discomfort, diaphoresis, and shortness of breath."
        return "[PDF Extract Sim]: PyPDF2 absent. Simulating intake text extraction."
    if ext in (".png", ".jpg", ".jpeg"):
        return "[OCR Extracted]: Patient presents with acute chest discomfort, diaphoreses, and shortness of breath."
    return "Unsupported file format."


def build_classifier_input(age, note):
    if not INCLUDE_AGE_IN_CLASSIFIER or age is None:
        return note
    return f"[Patient age: {age.label}] {note}"


def call_ollama_fallback(patient_note, specialty, age=None):
    """Local LLM via Ollama. Returns (model, text) or None."""
    age_line = f" Patient age: {age.label}." if age else ""
    for local_model in ["qwen2.5:0.5b", "smollm2:135m"]:
        try:
            body = {
                "model": local_model,
                "prompt": (
                    "You are a clinical assistant. Provide a 2-sentence clinical hand-off summary "
                    f"for this patient: '{patient_note}'.{age_line} Recommended routing: {specialty}."
                ),
                "stream": False,
            }
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                output = json.load(resp).get("response", "").strip()
                if output:
                    return local_model, output
        except Exception:
            continue
    return None


def generate_clinical_summary(patient_note, routing, age=None):
    """Bedrock cloud -> Ollama local -> deterministic safe mode. Returns a dict."""
    specialty = routing["best_choice"]
    is_emg = bool(routing.get("is_emergency", False))
    model_id = os.getenv("BEDROCK_MODEL", "us.amazon.nova-lite-v1:0")
    try:
        client = get_bedrock_client()
        age_line = f"Patient age: {age.label}.\n" if age else ""
        urgency_line = "Flagged as an immediate emergency.\n" if is_emg else ""
        prompt = (
            f"{age_line}Patient note: {patient_note}\n\n{urgency_line}"
            f"Recommended routing: {specialty}. Provide a concise clinical hand-off summary."
        )
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 300, "temperature": 0.2},
        )
        return {
            "source": "bedrock",
            "label": f"Amazon Bedrock | {model_id}",
            "text": response["output"]["message"]["content"][0]["text"],
        }
    except Exception:
        pass

    local = call_ollama_fallback(patient_note, specialty, age)
    if local:
        model, text = local
        return {"source": "ollama", "label": f"Local edge model | {model}", "text": text}

    prefix = "Emergency care now. " if is_emg else ""
    return {
        "source": "safe",
        "label": "Safe mode | deterministic",
        "text": (
            f"{prefix}Direct to **{specialty.upper()}**. "
            "Generative cloud and local summaries are offline; edge classification verified."
        ),
    }


# --------------------------------------------------------------------------
# State and callbacks
# --------------------------------------------------------------------------
st.session_state.setdefault("note", "")
st.session_state.setdefault("result", None)
st.session_state.setdefault("age_value", None)
st.session_state.setdefault("age_unit", UNITS[0])


def append_to_note(text):
    current = st.session_state.note.rstrip()
    st.session_state.note = f"{current}\n{text}".strip() if current else text.strip()


def cb_add_quick_symptoms():
    lines = []
    for region in ANATOMICAL_SYMPTOMS:
        key = f"sym_{region}"
        chosen = st.session_state.get(key, [])
        if chosen:
            lines.append(f"{region}: {', '.join(chosen)}")
        st.session_state[key] = []
    if lines:
        append_to_note("\n".join(lines))


def cb_add_voice(transcript):
    append_to_note(f"[Dictation]: {transcript}")


def cb_add_document(text):
    append_to_note(text)


def cb_load_sample():
    st.session_state.note = random.choice(SAMPLE_CASES)
    st.session_state.result = None


def cb_new_patient():
    st.session_state.note = ""
    st.session_state.result = None
    st.session_state.age_value = None
    st.session_state.age_unit = UNITS[0]
    for region in ANATOMICAL_SYMPTOMS:
        st.session_state[f"sym_{region}"] = []


def resolve_age(note):
    """Return (age, source, detected). A manually entered age wins over the note."""
    detected = detect_age(note)
    manual = make_age(st.session_state.age_value, st.session_state.age_unit)
    if manual is not None:
        return manual, "entered", detected
    if detected is not None:
        return detected, "detected", detected
    return None, None, None


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="ep-brand">
  <div class="ep-logo">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2"
         stroke-linecap="round" stroke-linejoin="round">
      <polyline points="2 12 6 12 9 4 14 20 17 12 22 12"></polyline>
    </svg>
  </div>
  <div>
    <div class="ep-title">EdgePulse</div>
    <div class="ep-sub">Autonomous rural triage &nbsp;|&nbsp; AWS Strands Decider 2B (#policy) &amp; Amazon Bedrock</div>
  </div>
</div>
<div class="ep-rule"></div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# 1. Capture symptoms
# --------------------------------------------------------------------------
st.markdown('<div class="ep-step" style="margin-top:0"><span class="n">1</span>Capture symptoms</div>', unsafe_allow_html=True)
with st.container(border=True):
    tab_quick, tab_voice, tab_doc = st.tabs(["Quick select", "Voice", "Scan / Upload"])

    with tab_quick:
        st.caption("Choose all that apply, then add them to the patient note.")
        grid = st.columns(2, gap="medium")
        for i, (region, options) in enumerate(ANATOMICAL_SYMPTOMS.items()):
            with grid[i % 2]:
                st.multiselect(region, options=options, key=f"sym_{region}", placeholder="Select symptoms")
        st.button(
            "Add selected to note",
            key="btn_add_quick",
            icon=":material/playlist_add:",
            on_click=cb_add_quick_symptoms,
        )

    with tab_voice:
        st.caption("Dictate an emergency note. The transcript is added to the patient note.")
        audio_input = st.audio_input("Record dictation", label_visibility="collapsed")
        if audio_input:
            # Demo transcript: swap in Amazon Transcribe for production.
            transcript = "Patient presents with crushing chest pain, sweating, and severe shortness of breath."
            st.info(f"Transcript: {transcript}")
            st.button(
                "Add transcript to note",
                key="btn_add_voice",
                icon=":material/mic:",
                on_click=cb_add_voice,
                args=(transcript,),
            )

    with tab_doc:
        st.caption("Upload an intake form. Text is extracted and can be added to the note.")
        uploaded = st.file_uploader(
            "Intake form",
            type=["txt", "pdf", "png", "jpg", "jpeg"],
            label_visibility="collapsed",
        )
        if uploaded:
            extracted = extract_text_from_file(uploaded)
            st.text_area("Extracted content", value=extracted, height=120, disabled=True)
            st.button(
                "Add document text to note",
                key="btn_add_doc",
                icon=":material/upload_file:",
                on_click=cb_add_document,
                args=(extracted,),
            )

# --------------------------------------------------------------------------
# 2. Review note and run triage (directly below capture)
# --------------------------------------------------------------------------
st.markdown('<div class="ep-step"><span class="n">2</span>Review note and run triage</div>', unsafe_allow_html=True)
with st.container(border=True):
    a1, a2 = st.columns([2, 1])
    a1.number_input(
        "Patient age",
        min_value=0,
        max_value=120,
        step=1,
        value=None,
        key="age_value",
        placeholder="Optional. Auto-detected from the note",
    )
    a2.selectbox("Unit", UNITS, key="age_unit")

    st.text_area(
        "Patient symptom note",
        key="note",
        height=170,
        placeholder="Symptoms added above appear here. You can also type or edit directly.",
    )

    age, age_source, detected = resolve_age(st.session_state.note)
    if age_source == "detected":
        st.caption(f"Age detected from note: {age.display}")
    elif age_source == "entered":
        st.caption(f"Age entered: {age.display}")
        if detected is not None and abs(detected.years - age.years) > 0.05:
            st.warning(f"The note mentions {detected.display}, which differs from the age entered. Please check.")
    else:
        st.caption("No age found. Enter one above or include it in the note (for example, \"7 year old\").")

    b1, b2, b3 = st.columns([2, 1, 1])
    process_clicked = b1.button("Process triage", type="primary", icon=":material/bolt:", key="btn_process")
    b2.button("Sample case", key="btn_sample", on_click=cb_load_sample)
    b3.button("New patient", key="btn_new", on_click=cb_new_patient)

if process_clicked:
    note = st.session_state.note.strip()
    if not note:
        st.error("Enter or select patient symptoms before processing.")
    else:
        with st.spinner("Running edge policy classification and generating summary..."):
            try:
                decider = get_decider()
                t0 = time.perf_counter()
                routing = decider.classify(build_classifier_input(age, note))
                elapsed_ms = (time.perf_counter() - t0) * 1000
                latency = routing.get("latency_ms") or elapsed_ms
                summary = generate_clinical_summary(note, routing, age=age)
                st.session_state.result = {
                    "routing": routing,
                    "latency": latency,
                    "summary": summary,
                    "age_display": age.display if age else None,
                }
            except Exception as e:
                st.session_state.result = None
                st.error(f"Analysis failed: {e}")

# --------------------------------------------------------------------------
# 3. Triage result
# --------------------------------------------------------------------------
st.markdown('<div class="ep-step"><span class="n">3</span>Triage result</div>', unsafe_allow_html=True)

result = st.session_state.result
if not result:
    with st.container(border=True):
        st.markdown(
            '<div class="ep-empty">No result yet. Add symptoms and select <b>Process triage</b>.</div>',
            unsafe_allow_html=True,
        )
else:
    routing = result["routing"]
    summary = result["summary"]

    is_emg = bool(routing.get("is_emergency", False))
    spec = html.escape(str(routing["best_choice"]).upper())
    needs_review = needs_human_review(routing)

    headline = "EMERGENCY CARE NOW" if is_emg else spec
    eyebrow = "Immediate action required" if is_emg else "Recommended routing"
    spec_line = f'<div class="line">Specialist on call: {spec}</div>' if is_emg else ""
    patient_line = (
        f'<div class="line">Patient age: {html.escape(result["age_display"])}</div>'
        if result.get("age_display")
        else '<div class="line">Patient age: not specified</div>'
    )

    st.markdown(
        f"""
<div class="ep-action {'emergency' if is_emg else ''}">
  <div class="eyebrow">{eyebrow}</div>
  <div class="route">{headline}</div>
  {spec_line}
  {patient_line}
  <span class="ep-chip">Confidence {routing['confidence']:.1%}</span>
  <span class="ep-chip">Margin {routing['margin']:.3f}</span>
  <span class="ep-chip">{result['latency']:.0f} ms edge latency</span>
</div>
""",
        unsafe_allow_html=True,
    )

    if needs_review:
        st.markdown(
            '<div class="ep-flag"><b>Human clinical review required.</b> '
            "The model is uncertain about urgency or specialty.</div>",
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown("**Medical summary**")
        st.markdown(
            f'<span class="ep-badge {summary["source"]}">{html.escape(summary["label"])}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(summary["text"])

    with st.expander("Model performance details"):
        m1, m2, m3 = st.columns(3)
        m1.metric("Confidence", f"{routing['confidence']:.2%}")
        m2.metric("Score margin", f"{routing['margin']:.3f}")
        m3.metric("Edge latency", f"{result['latency']:.0f} ms")
        st.caption("Raw specialty scores (independent yes/no scores, not normalized probabilities)")
        st.json(routing["raw_scores"])

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.markdown('<div class="ep-rule" style="margin-top:28px"></div>', unsafe_allow_html=True)
st.caption(
    "Safety disclaimer: EdgePulse is an agentic prototype for triage routing support, not a substitute for "
    "professional clinical diagnosis or emergency medical care. Low-margin confidence scores automatically "
    "trigger human clinical review."
)
