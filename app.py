import streamlit as st
import time
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Saudi Dental Claim Scrubber",
    page_icon="🦷",
    layout="wide"
)

# Header
st.title("🦷 Saudi Dental Documentation & Claim Scrubber")
st.caption("Standardized Epic SOAP Notes • CCHI MDS Compliance • SBS v3.0 & ACHI Bundling Engine")
st.divider()

# API Key handling
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.sidebar.info("💡 Add `GEMINI_API_KEY` into Streamlit App Secrets to keep this permanently unlocked.")

SYSTEM_INSTRUCTIONS = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.

Enforce Australian Coding Standards (ACS 0042), ACHI 10th Edition, SBS v3.0, and CCHI/NPHIES Medical Necessity & Anti-Unbundling Rules:

1. MANDATORY COMBINATION CODES (ZERO UNBUNDLING ACROSS ALL SPECIALTIES):
   - Whenever a single combination code exists in ACHI / SBS v3.0 that encompasses multiple concurrent services, YOU MUST USE THE COMBINATION CODE. Splitting into separate codes is strictly prohibited.
   - COMPLETE DENTURES (Full Mouth / Bimaxillary / Upper & Lower / 'u/l cd'): MUST code SBS `97719-00-00` / ACHI `97719-00` [Block 474] (Removable complete denture, maxillary and mandibular). NEVER split into separate upper (97711/97721) and lower (97712/97722) codes.
   - RESTORATIVE: Contiguous surfaces on the same tooth must be billed as a single multi-surface restoration code (1, 2, 3, 4, or 5 surfaces). NEVER bill separate 1-surface restorations for the same tooth.
   - ENDODONTICS: Global molar/premolar RCT codes must be prioritized over unbundling into separate prep and obturation lines.
   - SURGERY & PERIODONTICS: Quadrant codes (e.g., SRP 97222) cover up to 8 teeth; never unbundle per tooth. Flap elevation, ostectomy, sectioning, debridement, and suturing are all bundled into surgical extraction (97324-01).

2. BILLABLE CODING TABLE (SBS v3.0 & ACHI):
   - FORMAT: SBS v3.0 codes MUST strictly follow the 9-digit format: `XXXXX-XX-XX` (ACHI code + 2-digit SBS tariff suffix, e.g., `97719-00-00`, `97022-00-10`, `97324-01-00`).
   - NEVER use alphanumeric category shorthand (e.g., NEVER write `DEN.PRO.01`).
   - NEVER include chairside local anesthesia codes (Block 1909, 92509, 92513) in the billable table. Local anesthesia is bundled into primary care per ACS 0042.

3. RAPID CLINICIAN PRE-FLIGHT CHECKLIST:
   - Dynamic length based on clinical complexity: include all points necessary to prevent claim denial, but keep each point to a single, bold, scannable line that can be read chairside in seconds.
   - Format: `[ ] **Element:** Actionable clinical requirement`.
   - Strip out all IT schema and database error codes. Focus strictly on:
     * Anatomical Site / Arch qualifier (e.g., Arch 01 & 02 / Bimaxillary)
     * Mandatory imaging attachments (OPG, PA, bitewings)
     * Objective clinical criteria (ridge resorption, pocket depth, bone removal)
     * NPHIES prior authorization requirement (if applicable)
     * #1 Primary denial pitfall for this specific procedure

4. AUDIT-PROOF EPIC SOAP PROGRESS NOTE:
   - Clean, standardized, professional SOAP operative progress note ready to copy-paste directly into Epic.
"""

def generate_with_resilience(client, prompt):
    """
    Dual-engine resilience:
    1. Tries primary model (gemini-3.7-flash) with silent retry.
    2. Instantly falls back to high-capacity workhorse (gemini-2.0-flash) if 503 persists.
    """
    models = ["gemini-3.7-flash", "gemini-3.6-flash"]
    last_error = None

    for model_name in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.2,
                    )
                )
                return response.text
            except Exception as e:
                last_error = e
                err_text = str(e)
                # If server spikes with 503 or 429, wait briefly and retry
                if "503" in err_text or "429" in err_text:
                    time.sleep(2)
                    continue
                else:
                    break  # Break to fallback model on non-transient error
    raise last_error

col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.subheader("📝 Clinician Input")
    doctor_input = st.text_area(
        "Enter brief encounter notes:",
        placeholder="e.g., u/l cd, severe ridge resorption... OR #14 Crown prep... OR Extracted 48 impacted...",
        height=200
    )
    submit_btn = st.button("🚀 Audit Case & Generate Epic Note", type="primary", use_container_width=True)

with col_out:
    st.subheader("📋 Audit & Coding Package")
    if submit_btn:
        if not api_key:
            st.error("Missing Gemini API Key.")
        elif not doctor_input.strip():
            st.warning("Please type a case summary.")
        else:
            with st.spinner("Scrubbing against SBS v3.0 combination rules..."):
                try:
                    client = genai.Client(api_key=api_key)
                    result_text = generate_with_resilience(client, doctor_input)
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"Service temporarily busy. Please tap again: {str(e)}")
