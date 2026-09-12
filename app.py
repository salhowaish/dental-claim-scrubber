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
    
    st.markdown("#### 📖 Grounding Engine Status")
    if cchi_index_text:
        st.success("✅ CCHI SBS v3 Dental Index Active (19 Pages Grounded)")
    else:
        st.warning("⚠️ `sbs_dental_index.pdf` not found in repo root. Using prompt fallback.")
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
    "*Grounded in Official CCHI SBS v3.0 Dental Index • ACHI 10th Ed • Customizable EMR Outputs*"
)
st.divider()

# ==========================================
# PROMPT LOGIC & DYNAMIC STRUCTURE BUILDER
# ==========================================
BASE_PRINCIPLES = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.
You are provided with the full text of the official Council of Health Insurance (CCHI) Saudi Billing System (SBS) Version 3 Dental Alphabetic Index.
You MUST search this index to identify the exact 9-digit SBS code, the 7-digit ACHI code, and the [Block] number for any dental intervention.

Enforce the following Universal Principles:
1. GROUNDING & ACTION FLAGS: Look up procedures using CCHI Lead Terms. Assign: [PRIMARY CLAIM ITEM], [CO-BILLABLE PROCEDURE], [CO-BILLABLE DIAGNOSTIC], or [PRIOR-AUTH / PLANNED FUTURE SERVICE]. Place competing alternatives for the same site in "⚠️ Mutually Exclusive Alternatives".
2. ZERO UNBUNDLING: Obey CCHI "omit code" instructions (e.g., temporary crowns/bridges, dressings/irrigations, sutures for hemorrhage, new denture adjustments are all bundled). Bimaxillary dentures must use omnibus 97719-00-00 [474]. Multi-surface restorations use single combination codes.
3. INHERENT COMPONENTS: Local anesthesia (Block 1909), isolation, cavity bases/liners, and impression trays/materials are strictly non-billable.
4. DIGIT VALIDATION: ACHI Code = strictly 7 digits (XXXXX-XX). SBS Code = strictly 9 digits (XXXXX-XX-XX). Always include the [Block].
5. MANDATORY BLANK PLACEHOLDERS: NEVER guess or pre-fill tooth numbers, measurements, or materials not stated by the user. Use strictly blank placeholders: `[Specify FDI Tooth: #___]`, `[Specify Probing Depth: ___ mm]`, `[Specify Material: ___]`.
"""

def construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style):
    instructions = [BASE_PRINCIPLES, "\nREQUIRED OUTPUT SECTIONS (Generate ONLY the sections explicitly listed below):\n"]
    sec_num = 1
    
    if inc_icd:
        instructions.append(f"""
{sec_num}. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM 10th Ed)
   - Specific ICD-10-AM code justified by clinical presentation. If site/cause is unspecified, provide code with `[Specify Tooth/Arch]` placeholder.
""")
        sec_num += 1

    if inc_billing:
        instructions.append(f"""
{sec_num}. BILLABLE CODING TABLE (SBS v3.0 & ACHI 10th Ed)
   - Table columns MUST strictly be:
     `Service Description` | `ACHI Code` | `SBS v3.0 Code` | `Block` | `Claim Action Flag` | `Govt Tariff (SAR)* [Art. 11]` | `Bundled Elements (NON-BILLABLE)`
   - Tariff Column: Output realistic numeric statutory rates benchmarked to Article 11 (e.g., 120.00, 450.00, 850.00).
   - Immediately below the table, include: `*Tariff prices are determined in accordance with Article 11: "Dental services pricing in government sector".`
   - If mutually exclusive alternatives exist, output a sub-table: "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)".
""")
        sec_num += 1

    if inc_checklist:
        instructions.append(f"""
{sec_num}. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES)
   - Concise single-line checkmarks:
     * [ ] **Anatomical Site:** Tooth / Arch identifier.
     * [ ] **Required Radiograph:** Mandatory imaging attachments.
     * [ ] **Clinical Justification:** Clear objective criteria.
     * [ ] **Prior Authorization:** Status under NPHIES rules.
     * [ ] **#1 Denial Trap:** Primary pitfall to avoid.
""")
        sec_num += 1

    if note_style == "⚡ Concise SmartForm Macro (Hospital Template)":
        instructions.append(f"""
{sec_num}. AUDIT-PROOF EMR CLINICAL NOTE (CONCISE SMARTFORM MACRO)
   - STRICT FORMAT RULE: Do NOT generate multi-paragraph SOAP essays. Output a rapid, modular EMR Macro matching native hospital SmartForms.
   - NO patient demographics or doctor signature blocks.
   - Structure strictly as follows:
     **Encounter Specialty:** [Specialty Name]
     **Procedure:** [Definitive Procedure Name]
     **Tooth / Site:** [Tooth FDI #___ / Arch / Quadrant]
     **Anesthesia:** [None / Infiltration: Specify Agent & Dose]
     **Radiographs:** [None / Pre-op PA / Post-op PA: Specify Finding]
     **Patient Status:** [Cooperative / Mild Sensitivity / Asymptomatic]
     **Clinical Procedure:** [Short factual lines detailing steps: provisional removal, debridement, prep verification, try-in checks].
     **Materials / Delivery:** [Use discrete multi-choice pickers: e.g., [RelyX Luting / Resin Cement / GI Cement]].
     **Post-Op & Follow-Up:** [Concise 1-line home care instruction and recall timeframe].
""")
    elif note_style == "📋 Elaborate SOAP Note (Academic / Hospital Narrative)":
        instructions.append(f"""
{sec_num}. AUDIT-PROOF EMR SOAP CLINICAL PROGRESS NOTE (NARRATIVE)
   - Comprehensive narrative medical record. NO patient demographics or signature blocks.
   - Structure:
     **Encounter Specialty:** [Specialty Name]
     **SUBJECTIVE (S):** Detailed chief complaint, HPI, and medical history.
     **OBJECTIVE (O):** Detailed extraoral, intraoral, periodontal charting, and radiographic findings.
     **ASSESSMENT (A):** Definitive diagnoses linked to ICD-10-AM and clinical rationale.
     **PLAN & PROCEDURE (P):** Detailed itemized execution steps, isolation, materials, and staged plan.
     **POST-OPERATIVE INSTRUCTIONS & FOLLOW-UP:** Home care protocols, pain management, and recall interval.
""")

    return "".join(instructions)

def generate_scrubbed_package(client, doctor_input, cchi_text, system_instruction):
    """Executes call using Gemini Flash with dynamic configuration."""
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
                        system_instruction=system_instruction,
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
        placeholder="e.g.:\n- second visit, missing lower posterior teeth case referred for acrylic RPD, before creating a replica surgical guide\n- crown cementation tooth 26 zirconia\n- 9yo vital pulp therapy tooth 34",
        height=180
    )
    
    # Customization Controls
    st.markdown("##### ⚙️ Customize Output Package")
    c1, c2, c3 = st.columns(3)
    with c1:
        inc_icd = st.checkbox("ICD-10-AM Diagnosis", value=True)
    with c2:
        inc_billing = st.checkbox("SBS v3.0 / ACHI Table", value=True)
    with c3:
        inc_checklist = st.checkbox("NPHIES Checklist", value=True)
        
    note_style = st.radio(
        "Clinical Note Format:",
        [
            "⚡ Concise SmartForm Macro (Hospital Template)",
            "📋 Elaborate SOAP Note (Academic / Hospital Narrative)",
            "🚫 Skip Clinical Note (Coding Only)"
        ],
        index=0
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    submit_btn = st.button("🚀 Audit Case & Generate Package", type="primary", use_container_width=True)

with col_out:
    st.subheader("📋 Audit & Coding Output")
    if submit_btn:
        if not api_key:
            st.error("Missing Gemini API Key. Please enter it in the sidebar or Streamlit secrets.")
        elif not doctor_input.strip():
            st.warning("Please enter a case summary first.")
        elif not (inc_icd or inc_billing or inc_checklist or note_style != "🚫 Skip Clinical Note (Coding Only)"):
            st.warning("Please select at least one output section to generate.")
        else:
            with st.spinner("Auditing claim against CCHI SBS v3 Index & generating customized package..."):
                try:
                    client = genai.Client(api_key=api_key)
                    dynamic_sys_instruction = construct_dynamic_instructions(
                        inc_icd, inc_billing, inc_checklist, note_style
                    )
                    result_text = generate_scrubbed_package(
                        client, doctor_input, cchi_index_text, dynamic_sys_instruction
                    )
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"Service temporarily busy: {str(e)}")
