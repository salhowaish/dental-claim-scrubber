import os
import streamlit as st
import time
from pypdf import PdfReader
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Saudi Dental Claim Scrubber",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CACHED CCHI DENTAL INDEX EXTRACTOR
# ==========================================
@st.cache_data(show_spinner=False)
def load_cchi_dental_index():
    """Extracts and caches text from the official 19-page CCHI SBS v3 PDF."""
    pdf_filename = "sbs_dental_index.pdf"
    if not os.path.exists(pdf_filename):
        return ""
    try:
        reader = PdfReader(pdf_filename)
        extracted = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted.append(f"--- PAGE {i+1} ---\n{text}")
        return "\n".join(extracted)
    except Exception:
        return ""

cchi_index_text = load_cchi_dental_index()

# ==========================================
# SIDEBAR: CLINICAL ARCHITECT & CREDENTIALS
# ==========================================
with st.sidebar:
    st.markdown("### 👨‍⚕️ Developed & Architected By")
    st.markdown("## **Dr. Sulaiman Alhowaish**")
    st.markdown("*Specialist Prosthodontist • Healthcare Revenue Cycle & Medical AI Specialist*")
    st.markdown("---")
    
    st.markdown("#### 🎓 Board & Academic Credentials")
    st.markdown("""
    * **Saudi Board in Prosthodontics (SB-Pros)**  
      *Specialist in Fixed, Removable & Implant Prosthodontics*
    * **Executive Master's Degree in Insurance**  
      *King Saud University (KSU)*
    * **Bachelor of Dental Surgery (BDS)**
    """)
    
    st.markdown("#### 📜 Professional Certifications")
    st.markdown("""
    * **Certified Professional Coder (CPC®)**  
      *American Academy of Professional Coders (AAPC)*
    * **IBM Professional Certificate in Artificial Intelligence**  
      *Applied AI & Machine Learning in Healthcare & Medicine*
    """)
    st.markdown("---")
    
    st.markdown("#### 📖 Primary Grounding Source")
    if cchi_index_text:
        st.success("✅ CCHI SBS v3 Dental Index Connected (19 Pages Active)")
    else:
        st.warning("⚠️ `sbs_dental_index.pdf` not found in repo root. Using prompt knowledge fallback.")
    st.markdown("---")

    # API Key Handling
    api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    if not api_key:
        st.info("💡 Add `GEMINI_API_KEY` into Streamlit App Secrets to keep this permanently unlocked.")

# ==========================================
# MAIN HEADER
# ==========================================
st.title("🦷 Saudi Dental Documentation & Claim Scrubber")
st.markdown(
    "**Clinical AI Engine by Dr. Sulaiman Alhowaish (SB-Pros, CPC, MSc Insurance, IBM AI)**  \n"
    "*Grounded in Official CCHI SBS v3.0 Dental Index • ACHI 10th Ed • Audit-Proof EMR Clinical Notes*"
)
st.divider()

SYSTEM_INSTRUCTIONS = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.

You are provided with the full text of the official Council of Health Insurance (CCHI) Saudi Billing System (SBS) Version 3 Dental Alphabetic Index.
You MUST search this attached CCHI index to identify the exact 9-digit SBS code, the 7-digit ACHI code, and the [Block] number for any dental intervention.

Enforce the following 5 Universal Principles:

================================================================================
UNIVERSAL PRINCIPLE 1: GROUNDING IN THE CCHI DENTAL INDEX & CLAIM ACTION FLAGS
================================================================================
- Look up procedures using the official CCHI Lead Terms (e.g., Denture, Crown, Extraction, Fabrication, Provision, Restoration, Removal, Application, Root canal).
- Output the official CCHI Block number alongside every code.
- Claim Action Flags MUST strictly be one of:
  1. [PRIMARY CLAIM ITEM]: Definitive primary procedure for a given site/tooth.
  2. [CO-BILLABLE PROCEDURE]: Distinct concurrent therapeutic service on a separate or adjacent tooth/site.
  3. [CO-BILLABLE DIAGNOSTIC]: Separately billable baseline diagnostics (e.g., OPG 57960-00-00, PA 97022-00-10).
  4. [PRIOR-AUTH / PLANNED FUTURE SERVICE]: Staged appliances, duplicate radiographic guides, or planned subsequent surgical/prosthetic steps.
- Competing codes for the same tooth/phase (e.g., Resin RPD vs Cast Metal RPD, or Pulp Cap vs Pulpotomy) must NEVER both appear as billable. Put competing alternatives into the secondary table: "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)".

================================================================================
UNIVERSAL PRINCIPLE 2: "OMIT CODE" ANTI-UNBUNDLING MANDATE (ZERO UNBUNDLING)
================================================================================
The CCHI Index explicitly enforces "omit code" instructions for inherent steps:
- Temporary/provisional crown (97631-00-00) or pontic (97632-00-00) with any other dental procedure: OMIT CODE (bundled).
- Endodontic irrigation/dressing (97455-00-00) with any other endodontic procedure: OMIT CODE (bundled).
- Sutures for haemorrhage (97399-00-00) with any other dental procedure: OMIT CODE (bundled).
- New denture adjustments: OMIT CODE (bundled into delivery).
- Comprehensive combinations:
  * Complete bimaxillary dentures MUST use combination code 97719-00-00 [Block 474].
  * Multi-surface restorations on one tooth MUST be billed as a single composite/amalgam code.
  * Surgical extraction (97324-01-00) bundles flap, bone removal (ostectomy), sectioning, and suturing.
- Examination Bundling: Do NOT co-bill routine periodic oral examinations (97012-00-00) alongside active major restorative, endodontic, or prosthodontic procedures for the same encounter unless the patient presented with a distinct, unrelated acute complaint. Routine checks during impressions or try-in visits are bundled into the global service.

================================================================================
UNIVERSAL PRINCIPLE 3: INHERENT COMPONENTS (STRICTLY NON-BILLABLE)
================================================================================
The following are integral components of primary dental procedures and MUST NEVER appear as billable items:
- Local/regional anesthesia (Block 1909, 92509, 92513) per ACS 0042.
- Rubber dam isolation, cotton roll isolation, and operative field disinfection.
- Cavity bases, liners, bonding agents, and matrices.
- Impression trays, elastomeric/alginate materials, bite registrations, and try-in sessions.

================================================================================
UNIVERSAL PRINCIPLE 4: SBS v3.0 & ACHI 10TH ED DENTAL NUMERICAL ARCHITECTURE
================================================================================
- ACHI Code Column: MUST strictly be 7 digits: `XXXXX-XX` (e.g., 97722-00, 97679-00, 57960-00).
- SBS v3.0 Code Column: MUST strictly be 9 digits: `XXXXX-XX-XX` (e.g., 97722-00-00, 97679-00-00, 57960-00-00).
- Block Column: Provide the official block in brackets (e.g., [474], [473], [451]).
- Never use fictional alphanumeric prefixes (e.g., no DEN.* or RAD.*).

================================================================================
UNIVERSAL PRINCIPLE 5: ANTI-HALLUCINATION & MANDATORY BLANK PLACEHOLDERS
================================================================================
STRICT MEDICO-LEGAL SAFETY DIRECTIVE:
You are FORBIDDEN from guessing, suggesting, or pre-filling anatomical numbers, materials, or measurements not explicitly stated by the user. Keep placeholders strictly blank:
- Teeth: `[Specify Missing Teeth FDI: #___]` and `[Specify Abutment Teeth FDI: #___]`. NEVER suggest specific tooth numbers.
- Classifications: `[Specify Kennedy Class: I / II / III / IV, Mod: ___]`, `[Specify Black's Class: I / II / III / IV / V]`.
- Measurements: `[Specify Probing Depth: ___ mm]`, `[Specify Bone Height: ___ mm]`.
- Materials: `[Specify Material: PVS / Polyether / Alginate]`, `[Specify Shade: VITA ___]`.

================================================================================
REQUIRED OUTPUT STRUCTURE
================================================================================
1. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM 10th Ed)
   - Specific ICD-10-AM codes justified by clinical presentation. If site/cause is unspecified, provide code with `[Specify Tooth/Arch]` placeholder.

2. BILLABLE CODING TABLE (SBS v3.0 & ACHI 10th Ed)
   - Table columns MUST strictly be:
     `Service Description` | `ACHI Code` | `SBS v3.0 Code` | `Block` | `Claim Action Flag` | `Govt Tariff (SAR)* [Art. 11]` | `Bundled Elements (NON-BILLABLE)`
   - Tariff Column: Output realistic numeric statutory rates benchmarked to Article 11 (e.g., 120.00, 450.00, 850.00, 1,400.00).
   - Immediately below the table, include this exact mandatory statutory footnote:
     `*Tariff prices are determined in accordance with Article 11: "Dental services pricing in government sector".`
   - If mutually exclusive alternatives exist, output a separate small table below it titled:
     "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)"

3. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES)
   - Concise, single-line checkmarks:
     * [ ] **Anatomical Site:** Tooth / Arch identifier.
     * [ ] **Required Radiograph:** Mandatory imaging attachments.
     * [ ] **Clinical Justification:** Clear objective criteria.
     * [ ] **Prior Authorization:** Status under NPHIES rules.
     * [ ] **#1 Denial Trap:** Primary pitfall to avoid.

4. AUDIT-PROOF EMR SOAP CLINICAL PROGRESS NOTE
   - STRICT EMR FORMATTING CONSTRAINT: Do NOT include patient demographics (no Patient Name, MRN, Date of Service, Age, Gender brackets). Do NOT include doctor signature lines, provider credential blocks, SCFHS license numbers, or NPHIES provider IDs.
   - The note MUST start directly with:
     **Encounter Specialty:** [e.g., Prosthodontics, Endodontics, Oral & Maxillofacial Surgery, Restorative Dentistry, Pediatric Dentistry, Periodontics]
   - Follow immediately with the clinical record:
     **SUBJECTIVE (S):**
     **OBJECTIVE (O):**
     **ASSESSMENT (A):**
     **PLAN & PROCEDURE (P):**
     **POST-OPERATIVE INSTRUCTIONS & FOLLOW-UP:**
"""

def generate_scrubbed_package(client, doctor_input, cchi_text):
    """Executes call using Gemini Flash with fallback resilience and index grounding."""
    models = ["gemini-3.7-flash", "gemini-3.6-flash"]
    last_error = None

    prompt_payload = f"""
OFFICIAL CCHI SBS VERSION 3 DENTAL ALPHABETIC INDEX REFERENCE (ATTACHED GROUND TRUTH):
{cchi_text if cchi_text else "[Built-in ACHI/SBS Knowledge Active]"}

CLINICIAN ENCOUNTER CASE SUMMARY:
{doctor_input}
"""

    for model_name in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_payload,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1,
                    )
                )
                return response.text
            except Exception as e:
                last_error = e
                err_text = str(e)
                if "503" in err_text or "429" in err_text:
                    time.sleep(2)
                    continue
                else:
                    break
    raise last_error

# ==========================================
# UI LAYOUT
# ==========================================
col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.subheader("📝 Clinician Input")
    doctor_input = st.text_area(
        "Enter clinical case summary (any dental specialty):",
        placeholder="e.g.:\n- second visit , missing lower posterior teeth case referred for acrylic RPD, before creating a replica surgical/radiographic guide to plan and refer for dental implants\n- 13 yo trauma tooth 11, pulp exposure, vital pulp therapy\n- tooth 48 impacted, ostectomy and sectioning",
        height=220
    )
    submit_btn = st.button("🚀 Audit Case & Generate EMR Note", type="primary", use_container_width=True)

with col_out:
    st.subheader("📋 Audit & Coding Package")
    if submit_btn:
        if not api_key:
            st.error("Missing Gemini API Key. Please add it in the sidebar or Streamlit secrets.")
        elif not doctor_input.strip():
            st.warning("Please enter a case summary first.")
        else:
            with st.spinner("Searching official CCHI SBS v3 Dental Index & scrubbing claim..."):
                try:
                    client = genai.Client(api_key=api_key)
                    result_text = generate_scrubbed_package(client, doctor_input, cchi_index_text)
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"Service temporarily busy: {str(e)}")
