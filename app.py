import os
import re
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

    api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    if not api_key:
        st.info("💡 Add `GEMINI_API_KEY` into Streamlit App Secrets to keep this permanently unlocked.")

# ==========================================
# MAIN HEADER
# ==========================================
st.title("🦷 Saudi Dental Documentation & Claim Scrubber")
st.markdown(
    "**Clinical AI Engine by Dr. Sulaiman Alhowaish (SB-Pros, CPC, MSc Insurance, IBM AI)**  \n"
    "*Hospital-Grade Engine • Grounded in CCHI SBS v3.0 • ACHI 10th Ed • ICD-10-AM Diagnostic Locking*"
)
st.divider()

# ==========================================
# HARDENED GROUND-TRUTH SYSTEM INSTRUCTIONS
# ==========================================
BASE_PRINCIPLES = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.
You are provided with the full text of the official Council of Health Insurance (CCHI) Saudi Billing System (SBS) Version 3 Dental Alphabetic Index.
You MUST search this index to identify the exact 9-digit SBS code, the 7-digit ACHI code, and the [Block] number for any dental intervention.

================================================================================
CRITICAL RULE: ICD-10-AM 10TH EDITION SPECIFICITY & DIAGNOSTIC LOCK
================================================================================
1. USE ONLY AUSTRALIAN 10TH EDITION CODES (NEVER USE RETIRED CODES):
   - Edentulism / Loss of teeth: Use K08.41 (Complete edentulism, both jaws), K08.42 (Complete edentulism, single jaw), K08.43 (Partial edentulism, multiple missing), K08.44 (Partial edentulism, single missing). NEVER USE K08.1 (RETIRED).
   - Caries: K02.51, K02.52, K02.53 (Arrested/enamel/dentin with pulp involvement), K02.61, K02.62, K02.63 (Smooth surface), K02.71, K02.72 (Root caries).
   - Pulpal / Periapical: K04.01 (Reversible pulpitis), K04.02 (Irreversible pulpitis), K04.1 (Necrosis of pulp), K04.5 (Chronic apical periodontitis), K04.7 (Periapical abscess without sinus).
   - Periodontal: K05.10 (Chronic gingivitis), K05.31 (Chronic periodontitis, localized), K05.32 (Chronic periodontitis, generalized).
   - Surgical / Impacted: K01.1 (Impacted teeth), K01.0 (Embedded teeth).
   - Trauma: S02.51 (Fracture of tooth enamel only), S02.52 (Fracture of crown without pulp), S02.53 (Fracture of crown with pulp), S03.2X1 (Luxation of tooth).

2. DIAGNOSTIC IMMUTABILITY RULE (ANTI-DRIFT):
   - If clinician input contains an existing "[PRIMARY_ICD10]" in a CONTINUITY BLOCK, YOU MUST LOCK THAT EXACT CODE.
   - DO NOT alter, generalize, or shift the ICD-10-AM code across follow-up encounters of the same episode.

================================================================================
UNIVERSAL MULTI-VISIT CONTINUITY & ANTI-UNBUNDLING RULES
================================================================================
1. INTERMEDIATE VISITS (Global Bundling):
   - RPD/CD Visits 1-4, Indirect Crown/Bridge Visit 1, Multi-visit RCT Stage 1:
     * Primary Procedure Claim Action Flag MUST BE: `[IN-PROGRESS / BUNDLED ENCOUNTER - NON-BILLABLE]`.
     * Tariff MUST BE: `0.00 SAR`.
     * Explicitly bundle impressions, bite registrations, wax try-ins, dressing changes, and interim exams.
2. DEFINITIVE DELIVERY VISITS:
   - Unlock global code as `[PRIMARY CLAIM ITEM - GLOBAL DEFINITIVE]` with full Article 11 tariff.
3. CO-BILLABLE PREPARATORY EXCEPTIONS (NEVER OMIT ON VISIT 1):
   - Core build-up (97627-00-00 [463]), Post/core (97625-00-00 [463]), and Old crown removal (97655-00-00 [462]) ARE NOT BUNDLED into crown prep. Bill them on Visit 1 with their independent tariff.

================================================================================
CRITICAL FORMATTING MANDATE FOR CASE CONTINUITY BLOCK
================================================================================
You MUST output the continuity block enclosed STRICTLY within `<NPHIES_BLOCK>` and `</NPHIES_BLOCK>` tags at the very end of your response.
DO NOT use markdown headers, equal signs, or formatting inside or around these tags.

Format inside the tags strictly as:
<NPHIES_BLOCK>
[EPISODE_ID]: [Specialty]-[Procedure]-[FDI Tooth/Arch]
[PRIMARY_ICD10]: [Code] — [Accurate 10th Ed Description]
[PRIMARY_SBS_CODE]: [SBS 9-digit Code] [Block]
[CURRENT_STAGE]: Visit [X] of [Total Visits] — [Description of Today's Step]
[BILLING_STATUS]: [IN_PROGRESS - CLAIM LOCKED (0.00 SAR) / GLOBAL CLAIM DELIVERED (Tariff SAR)]
[NEXT_VISIT_EXPECTED]: Visit [X+1] — [Description of Next Clinical Step]
[ANTI-UNBUNDLING_LOCK]: LOCKED — Inherent intermediate steps must NOT be billed separately.
</NPHIES_BLOCK>
"""

def construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway):
    instructions = [BASE_PRINCIPLES]
    
    if is_staged and staged_pathway != "Auto-detect from case input":
        instructions.append(f"\nACTIVE WORKFLOW PRE-SET: Clinician selected pathway: {staged_pathway}. Align stage numbering and tariff locks strictly with this clinical pathway.\n")
        
    instructions.append("\nREQUIRED OUTPUT SECTIONS (Generate ONLY the sections explicitly requested below):\n")
    sec_num = 1
    
    if inc_icd:
        instructions.append(f"""
{sec_num}. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM 10th Ed)
   - Specific, modern ICD-10-AM code. If site/cause is unspecified, provide code with `[Specify Tooth/Arch]` placeholder.
""")
        sec_num += 1

    if inc_billing:
        instructions.append(f"""
{sec_num}. BILLABLE CODING TABLE (SBS v3.0 & ACHI 10th Ed)
   - Columns MUST strictly be:
     `Service Description` | `ACHI Code` | `SBS v3.0 Code` | `Block` | `Claim Action Flag` | `Govt Tariff (SAR)* [Art. 11]` | `Bundled Elements (NON-BILLABLE)`
   - Tariff: 0.00 for intermediate locked visits; realistic statutory Article 11 tariff for definitive delivery.
   - Immediately below table: `*Tariff prices are determined in accordance with Article 11: "Dental services pricing in government sector".`
   - Sub-table: "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)" if alternatives exist.
""")
        sec_num += 1

    if inc_checklist:
        instructions.append(f"""
{sec_num}. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES)
   - Single-line checks: Anatomical Site, Required Radiograph, Clinical Justification, Prior Authorization/Episode Status, #1 Denial Trap.
""")
        sec_num += 1

    if note_style == "⚡ Concise SmartForm Macro (Hospital Template)":
        instructions.append(f"""
{sec_num}. AUDIT-PROOF EMR CLINICAL NOTE (CONCISE SMARTFORM MACRO)
   - DO NOT write multi-paragraph narratives. Output rapid, modular SmartForm lines.
   - Structure:
     **Encounter Specialty:** [Specialty Name]
     **Procedure:** [Definitive Procedure Name]
     **Tooth / Site:** [Tooth FDI #___ / Arch / Quadrant]
     **Anesthesia:** [None / Infiltration: Specify Agent & Dose]
     **Radiographs:** [None / Pre-op PA / Post-op PA: Specify Finding]
     **Patient Status:** [Cooperative / Mild Sensitivity / Asymptomatic]
     **Clinical Procedure:** [Short factual lines detailing steps performed today].
     **Materials / Delivery:** [Multi-choice pickers: e.g., [PVS / Polyether] or [RelyX / Resin / GI]].
     **Post-Op & Follow-Up:** [Concise 1-line home care instruction and recall timeframe].
""")
    elif note_style == "📋 Elaborate SOAP Note (Academic / Hospital Narrative)":
        instructions.append(f"""
{sec_num}. AUDIT-PROOF EMR SOAP CLINICAL PROGRESS NOTE (NARRATIVE)
   - Comprehensive narrative medical record: Subjective, Objective, Assessment, Plan & Procedure, Post-Operative Instructions.
""")

    return "".join(instructions)

def generate_scrubbed_package(client, doctor_input, cchi_text, system_instruction):
    prompt_payload = f"""
OFFICIAL CCHI SBS VERSION 3 DENTAL ALPHABETIC INDEX REFERENCE (ATTACHED GROUND TRUTH):
{cchi_text if cchi_text else "[Built-in ACHI/SBS Knowledge Active]"}

CLINICIAN ENCOUNTER CASE SUMMARY:
{doctor_input}
"""
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model="gemini-3.7-flash",
                contents=prompt_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.05,
                )
            )
            return response.text
        except Exception as e:
            if attempt == 0:
                time.sleep(1)
                continue
            raise e

# ==========================================
# UI LAYOUT
# ==========================================
col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.subheader("📝 Clinician Input")
    doctor_input = st.text_area(
        "Enter clinical encounter details (paste previous Continuity Block here for follow-up visits):",
        placeholder="e.g.:\n- second visit, missing lower posterior teeth case referred for acrylic RPD\n- crown prep and temp tooth 46\n- or paste the Continuity Block from the previous visit along with today's note",
        height=170
    )
    
    st.markdown("##### ⚙️ Output Customization")
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
    
    st.markdown("---")
    is_staged = st.checkbox(
        "🔄 Multi-Visit / Staged Episode Tracker", 
        value=True, 
        help="Enforces CCHI Episode Billing Rules: Locks intermediate visits to 0.00 SAR and unlocks the full tariff upon final delivery."
    )
    staged_pathway = "Auto-detect from case input"
    if is_staged:
        staged_pathway = st.selectbox(
            "Select Clinical Pathway (Preset Workflow):",
            [
                "Auto-detect from case input",
                "Indirect Crown / Bridge — [2 Visits: Prep/Impression/Provisional -> Final Cementation]",
                "Removable Partial Denture (RPD) — [4 Visits: Primary Imp -> Master Imp/Bite -> Try-In -> Delivery]",
                "Complete Dentures (Full Arch / Bimaxillary) — [5 Visits: Imp 1 -> Border Mold/Imp 2 -> Jaw Relation -> Try-In -> Delivery]",
                "Multi-Visit Endodontics (RCT) — [2 Visits: Emergency Pulpectomy/Dressing -> Final Obturation]",
                "Implant Stage Protocol — [Staged: Surgical Placement -> Stage-2 Exposure -> Final Impression -> Prosthesis Delivery]"
            ]
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
            with st.spinner("Auditing claim against CCHI SBS v3 Index & validating episode state..."):
                try:
                    client = genai.Client(api_key=api_key)
                    dynamic_sys_instruction = construct_dynamic_instructions(
                        inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                    )
                    raw_result = generate_scrubbed_package(
                        client, doctor_input, cchi_index_text, dynamic_sys_instruction
                    )
                    
                    # ==========================================
                    # DETERMINISTIC PYTHON SEPARATION (NO UI BREAKS)
                    # ==========================================
                    # Extract the NPHIES Continuity Block from custom tags
                    nphies_match = re.search(r"<NPHIES_BLOCK>(.*?)</NPHIES_BLOCK>", raw_result, re.DOTALL)
                    clean_markdown = re.sub(r"<NPHIES_BLOCK>.*?</NPHIES_BLOCK>", "", raw_result, flags=re.DOTALL).strip()
                    
                    # Display the clean clinical audit and notes
                    st.markdown(clean_markdown)
                    
                    # Display the Continuity Block inside a dedicated, isolated code box
                    if nphies_match:
                        st.markdown("---")
                        st.markdown("##### 🔄 NPHIES Case Continuity Token (Copy for next visit):")
                        block_content = nphies_match.group(1).strip()
                        st.code(block_content, language="text")
                    
                except Exception as e:
                    st.error(f"Execution error: {str(e)}")
