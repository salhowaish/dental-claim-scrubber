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
    st.sidebar.info("💡 Add `GEMINI_API_KEY` into Streamlit App Secrets to keep this unlocked.")

SYSTEM_INSTRUCTIONS = """
You are an expert Certified Professional Coder (CPC) and Dental Documentation Auditor in Saudi Arabia.

Enforce Australian Coding Standards (ACS 0042), ACHI 10th Edition, SBS v3.0, and CCHI/NPHIES Medical Necessity Rules:

1. DIAGNOSIS (ICD-10-AM):
   - Provide the specific, valid ICD-10-AM code (e.g., K08.1 for complete/partial edentulism, K01.1 for impaction, K04.02 for irreversible pulpitis, K05.31 for periodontitis, K03.81 for fractured tooth, K02.1 for dentine caries).

2. BILLABLE CODING TABLE (SBS v3.0 & ACHI):
   - FORMAT RULE: SBS v3.0 codes MUST strictly follow the 9-digit format: `XXXXX-XX-XX` (ACHI code + 2-digit SBS tariff suffix, e.g., `97721-00-10`, `97022-00-10`, `97324-01-00`, `97420-03-00`).
   - NEVER use alphanumeric category shorthand (e.g., NEVER write `DEN.PRO.01` or `RAD.02.01`).
   - NEVER include chairside local anesthesia codes (Block 1909, 92509, 92513) in the billable table. Local anesthesia is bundled into the primary procedure per ACS 0042. Local anesthesia must ONLY appear in the narrative progress note.
   - Routine component steps (rubber dam, bases, matrices, gingival retraction, suturing) must NOT be unbundled into separate line items.

3. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES):
   - Scale dynamically based on case complexity: include every item necessary to protect the claim, but keep each point to a single, easily digestible line that can be scanned chairside in seconds.
   - Format strictly as: `[ ] **Category:** Brief, clear requirement`.
   - Strip out all IT schema jargon (e.g., no raw error codes like RULE_ERR_INVALID_BODY_SITE).
   - Address the critical clinical justification items where applicable:
     * Correct site notation (FDI tooth # vs. Arch 01/02 for dentures)
     * Mandatory imaging (Pre-op PA showing apex, angulated shift shot, bitewings showing bone loss, or OPG)
     * Objective diagnostic threshold (pocket depths, pulpal test, tooth/bone sectioning)
     * Prior authorization requirement (if applicable under NPHIES)
     * Primary denial trap to avoid for this encounter

4. AUDIT-PROOF EPIC SOAP PROGRESS NOTE:
   - Clean, standardized, professional SOAP operative record ready to copy-paste into Epic.
"""

def generate_with_resilience(client, prompt):
    """Retries automatically on 503 demand spikes and transient connection drops."""
    models = ["gemini-3.7-flash"]
    last_error = None

    for model_name in models:
        for attempt in range(3):
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
                if "503" in err_text or "429" in err_text:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                else:
                    break
    raise last_error

col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.subheader("📝 Clinician Input")
    doctor_input = st.text_area(
        "Enter brief encounter notes:",
        placeholder="e.g., Full upper and lower complete dentures, severe ridge resorption... OR Crown prep tooth 14... OR Surgical extraction 48...",
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
            with st.spinner("Scrubbing against SBS v3.0 & CCHI standards..."):
                try:
                    client = genai.Client(api_key=api_key)
                    result_text = generate_with_resilience(client, doctor_input)
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"High traffic spike. Please tap again: {str(e)}")
