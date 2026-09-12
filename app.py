import streamlit as st
import time
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Saudi Dental Claim Scrubber",
    page_icon="🦷",
    layout="wide"
)

st.title("🦷 Saudi Dental Documentation & Claim Scrubber")
st.markdown("Automated CCHI/NPHIES Medical Necessity Engine • SBS v3.0 & ACHI Coding • Audit-Proof Epic Notes")
st.divider()

# Get API key from Secrets or sidebar
api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("Gemini API Key", type="password")

SYSTEM_INSTRUCTIONS = """
You are an expert Certified Professional Coder (CPC), Dental Revenue Cycle Auditor, and Clinical Documentation Specialist in Saudi Arabia.

Enforce Australian Coding Standards (ACS 0042), ACHI 10th Edition, SBS v3.0, and CCHI/NPHIES Medical Necessity & Bundling Rules:

1. MISSING DIAGNOSIS: If the clinician does not supply an exact diagnosis, infer the most specific, medically justified ICD-10-AM codes (e.g., K01.1 for impactions, K04.02 for irreversible pulpitis, K05.31 for periodontitis, K03.81 for fractured tooth, K02.1 for dentine caries).

2. BILLABLE CODING TABLE:
   - Provide exact SBS v3.0 codes, ACHI codes, and standard tariffs.
   - CRITICAL COMPLIANCE CONSTRAINT: NEVER include local/regional anesthesia codes (Block 1909, 92509, 92513) in the Billable Coding Table. Local anesthesia is bundled into the primary procedure per ACS 0042. Local anesthesia must ONLY appear in the narrative progress note.
   - Component steps (rubber dam, cavity bases, matrices, gingival retraction, suturing) must NOT be unbundled into separate line items.

3. CCHI / NPHIES AUDIT CHECKLIST:
   - List the mandatory Minimum Data Set (MDS) elements required to prevent denial (tooth FDI number, required pre-op/post-op X-rays, vitality test results, periodontal probing depths).
   - Detail the Top 3 denial pitfalls for this specific encounter.

4. AUDIT-PROOF EPIC SOAP PROGRESS NOTE:
   - Generate a standardized, legally defensible, accreditation-ready (CCHI / CBAHI) SOAP note ready to copy directly into Epic.
"""

def generate_with_retry(client, prompt, max_retries=3):
    """Retries silently if Google servers experience momentary high demand (503/429)."""
    models_to_try = ["gemini-3.7-flash", "gemini-2.0-flash"]
    
    for model_name in models_to_try:
        for attempt in range(max_retries):
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
                err_str = str(e)
                # If server is overloaded (503) or rate-limited (429), wait and retry
                if ("503" in err_str or "429" in err_str) and attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                elif attempt == max_retries - 1 and model_name != models_to_try[-1]:
                    # Move to fallback model
                    break
                else:
                    raise e

col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.subheader("📝 Clinician Encounter Input")
    doctor_input = st.text_area(
        "Enter what you did, where, and why (brief sentence or notes):",
        placeholder="Example inputs:\n- #14 Crown removal and restorability assessment\n- Surgical extraction tooth 48 impacted, cut bone and sectioned tooth\n- RCT tooth 16, 4 canals found and filled\n- Deep cleaning lower right quadrant, pockets 5-6mm",
        height=220
    )
    submit_btn = st.button("🚀 Audit Case & Generate Epic Note", type="primary", use_container_width=True)

with col_out:
    st.subheader("📋 Audit & Coding Package")
    if submit_btn:
        if not api_key:
            st.error("Missing Gemini API Key.")
        elif not doctor_input.strip():
            st.warning("Please type a case summary on the left.")
        else:
            with st.spinner("Scrubbing against CCHI standards (handling server traffic)..."):
                try:
                    client = genai.Client(api_key=api_key)
                    result_text = generate_with_retry(client, doctor_input)
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"System busy. Please tap Generate again in a few seconds: {str(e)}")
