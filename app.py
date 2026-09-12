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

    api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    if not api_key:
        st.info("💡 Add `GEMINI_API_KEY` into Streamlit App Secrets to keep this permanently unlocked.")

# ==========================================
# MAIN HEADER
# ==========================================
st.title("🦷 Saudi Dental Documentation & Claim Scrubber")
st.markdown(
    "**Clinical AI Engine by Dr. Sulaiman Alhowaish (SB-Pros, CPC, MSc Insurance, IBM AI)**  \n"
    "*Grounded in Official CCHI SBS v3.0 Dental Index • ACHI 10th Ed • Multi-Visit Episode Protection*"
)
st.divider()

# ==========================================
# PROMPT LOGIC & DYNAMIC STRUCTURE BUILDER
# ==========================================
BASE_PRINCIPLES = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.
You are provided with the full text of the official Council of Health Insurance (CCHI) Saudi Billing System (SBS) Version 3 Dental Alphabetic Index.
You MUST search this index to identify the exact 9-digit SBS code, the 7-digit ACHI code, and the [Block] number for any dental intervention.

Enforce the following 6 Universal Principles:
1. GROUNDING & ACTION FLAGS: Look up procedures using CCHI Lead Terms. Assign: [PRIMARY CLAIM ITEM], [CO-BILLABLE PROCEDURE], [CO-BILLABLE DIAGNOSTIC], [IN-PROGRESS / BUNDLED ENCOUNTER - NON-BILLABLE], or [PRIOR-AUTH / PLANNED FUTURE SERVICE]. Place competing alternatives for the same site in "⚠️ Mutually Exclusive Alternatives".
2. ZERO UNBUNDLING: Obey CCHI "omit code" instructions (e.g., temporary crowns/bridges, dressings/irrigations, sutures for hemorrhage, new denture adjustments are all bundled). Bimaxillary dentures must use omnibus 97719-00-00 [474]. Multi-surface restorations use single combination codes.
3. INHERENT COMPONENTS: Local anesthesia (Block 1909), isolation, cavity bases/liners, impression trays/materials, bite registrations, and try-ins are strictly non-billable.
4. DIGIT VALIDATION: ACHI Code = strictly 7 digits (XXXXX-XX). SBS Code = strictly 9 digits (XXXXX-XX-XX). Always include the [Block].
5. MANDATORY BLANK PLACEHOLDERS: NEVER guess or pre-fill tooth numbers, measurements, or materials not stated by the user. Use strictly blank placeholders: `[Specify FDI Tooth: #___]`, `[Specify Probing Depth: ___ mm]`, `[Specify Material: ___]`.

================================================================================
UNIVERSAL PRINCIPLE 6: MULTI-VISIT CONTINUITY & EPISODE BUNDLING LOCK
================================================================================
1. EPISODE STAGING ADJUDICATION:
   - If the clinician's input contains an existing "NPHIES CASE CONTINUITY BLOCK", or if the case is identified as an intermediate stage of a global service (e.g., RPD Visit 1-3, Crown Prep Visit 1, or RCT Step 1):
     * Intermediate Visits: The primary procedure Claim Action Flag MUST be set to `[IN-PROGRESS / BUNDLED ENCOUNTER - NON-BILLABLE]`.
     * The Tariff MUST be output as `0.00 SAR` (Claim locked until final delivery/cementation/obturation per CCHI global pricing rules).
     * Strictly warn against unbundling routine exams (97012-00-00), impressions, or jaw relations on intermediate visits.
   - Final Delivery Visits (e.g., RPD Insertion Visit 4, Crown Cementation Visit 2, or RCT Final Obturation):
     * The procedure unlocks as `[PRIMARY CLAIM ITEM - GLOBAL DEFINITIVE]`.
     * The full Article 11 tariff is billed (e.g., 850.00 SAR for RPD, 1,250.00 SAR for Zirconia crown).

2. MANDATORY CASE CONTINUITY BLOCK FORMATTING:
   At the very end of EVERY generated output, append a copy-pasteable metadata block.
   CRITICAL FORMATTING RULE: 
   - You MUST enclose the entire block inside a Markdown text code block (using triple backticks: ```text ... ```).
   - NEVER output raw `===` divider lines outside of a code fence, as Markdown interprets them as giant H1 heading underlines.
   
   Structure inside the code block exactly as follows:
   ```text
   ================================================================================
   NPHIES CASE CONTINUITY BLOCK (Copy & paste into next visit prompt)
   ================================================================================
   [EPISODE_ID]: [Specialty]-[Procedure]-[FDI Site]
   [PRIMARY_SBS_CODE]: [SBS 9-digit Code] [Block]
   [CURRENT_STAGE]: Visit [X] of [Total Estimated Visits] — [Description of Today's Step]
   [BILLING_STATUS]: [IN_PROGRESS - CLAIM LOCKED (0.00 SAR) / GLOBAL CLAIM DELIVERED (Tariff SAR)]
   [NEXT_VISIT_EXPECTED]: Visit [X+1] — [Description of Next Clinical Step]
   [ANTI-UNBUNDLING_LOCK]: LOCKED — Inherent intermediate steps must NOT be billed separately.
   ================================================================================
   ```
"""

def construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway):
    instructions = [BASE_PRINCIPLES]
    
    if is_staged and staged_pathway != "Auto-detect from case input":
        instructions.append(f"\nACTIVE WORKFLOW PRE-SET: Clinician selected multi-visit pathway: {staged_pathway}. Accurately align the episode stages and billing locks with this pathway.\n")
        
    instructions.append("\nREQUIRED OUTPUT SECTIONS (Generate ONLY the sections explicitly listed below):\n")
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
   - Tariff Column: Output realistic numeric statutory rates benchmarked to Article 11 (e.g., 0.00 for locked in-progress visits; 850.00 for definitive RPD delivery).
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
     * [ ] **Prior Authorization / Episode Status:** Status under NPHIES rules.
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
     **Clinical Procedure:** [Short factual lines detailing steps performed today].
     **Materials / Delivery:** [Use discrete multi-choice pickers: e.g., [PVS / Polyether / Alginate] or [RelyX / Resin / GI]].
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
    """Executes call using Gemini 3.7 Flash with retry resilience."""
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
                    temperature=0.1,
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
        "Enter clinical case summary (paste previous Continuity Block here for follow-up visits):",
        placeholder="e.g.:\n- crown prep and temp tooth 26\n- second visit, missing lower posterior teeth case referred for acrylic RPD\n- or paste the [NPHIES CASE CONTINUITY BLOCK] from the previous appointment along with today's notes",
        height=170
    )
    
    st.markdown("##### ⚙️ Output Package Customization")
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
        help="Locks intermediate stages to 0.00 SAR to prevent premature unbundled billing, unlocking the global fee only at final delivery."
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
            with st.spinner("Auditing claim against CCHI SBS v3 Index & checking episode continuity..."):
                try:
                    client = genai.Client(api_key=api_key)
                    dynamic_sys_instruction = construct_dynamic_instructions(
                        inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                    )
                    result_text = generate_scrubbed_package(
                        client, doctor_input, cchi_index_text, dynamic_sys_instruction
                    )
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"Service error: {str(e)}")
