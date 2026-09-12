import os
import re
import streamlit as st
import time
from pypdf import PdfReader
from google import genai
from google.genai import types

st.set_page_config(
    page_title="FERRULE | Dr. Sulaiman Alhowaish",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ENTERPRISE CLINICAL CSS THEME
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Bar & Branding */
    .brand-header {
        margin-bottom: 1.5rem;
        padding-bottom: 1.1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .brand-title-row {
        display: flex;
        align-items: baseline;
        gap: 0.75rem;
        margin-bottom: 0.35rem;
    }
    .brand-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #F8FAFC;
    }
    .brand-author {
        font-size: 1.05rem;
        font-weight: 600;
        color: #38BDF8;
        letter-spacing: -0.01em;
    }
    .brand-subtitle {
        font-size: 0.88rem;
        font-weight: 400;
        color: #94A3B8;
        line-height: 1.45;
    }
    
    /* Tag Pills */
    .tag-pill {
        display: inline-block;
        padding: 0.22rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        background: rgba(14, 165, 233, 0.12);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.25);
        margin-right: 0.35rem;
    }
    .tag-pill-gold {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    
    /* Executive Profile Card */
    .profile-card {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1.25rem;
    }
    .profile-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.2rem;
        letter-spacing: -0.01em;
    }
    .profile-role {
        font-size: 0.82rem;
        font-weight: 600;
        color: #38BDF8;
        margin-bottom: 0.15rem;
    }
    .profile-org {
        font-size: 0.76rem;
        color: #94A3B8;
        line-height: 1.4;
        margin-bottom: 0.75rem;
    }
    .profile-contact {
        font-size: 0.75rem;
        color: #CBD5E1;
        line-height: 1.65;
        padding-top: 0.65rem;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    .profile-contact a {
        color: #38BDF8;
        text-decoration: none;
    }
    .profile-contact a:hover {
        text-decoration: underline;
    }
    
    /* Section Headings */
    .sub-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748B;
        margin-top: 0.95rem;
        margin-bottom: 0.4rem;
    }
    
    /* Input Container Box */
    .stTextArea textarea {
        border-radius: 8px !important;
        font-size: 0.88rem !important;
        line-height: 1.5 !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background-color: rgba(15, 23, 42, 0.5) !important;
    }
    
    /* Primary Button Styling */
    div.stButton > button:first-child {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.88rem;
        letter-spacing: 0.01em;
        padding: 0.55rem 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

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
# SIDEBAR: EXECUTIVE ARCHITECT & CREDENTIALS
# ==========================================
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <div class="profile-name">Dr. Sulaiman Alhowaish</div>
        <div class="profile-role">Deputy Manager, Dental Department</div>
        <div class="profile-org">
            Alyamamah Hospital<br>
            Riyadh Second Health Cluster (R2)
        </div>
        <div class="profile-contact">
            <strong>Mobile:</strong> <a href="tel:+966508172926">+966 50 817 2926</a><br>
            <strong>Email:</strong> <a href="mailto:s.alhowaish@gmail.com">s.alhowaish@gmail.com</a><br>
            <strong>Focus:</strong> Prosthodontics & Revenue Cycle Architecture
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sub-section-title">Clinical & Regulatory Qualifications</div>', unsafe_allow_html=True)
    st.markdown("""
    * **SB-Pros** | Saudi Board in Prosthodontics  
    * **MSc** | Executive Master in Health Insurance (KSU)  
    * **BDS** | Bachelor of Dental Surgery  
    * **CPC®** | Certified Professional Coder (AAPC)  
    * **IBM AI** | Professional Certificate in Artificial Intelligence
    """)

    st.markdown('<div class="sub-section-title">Clearinghouse & Grounding Integrity</div>', unsafe_allow_html=True)
    if cchi_index_text:
        st.success("CCHI SBS v3.0 Ground Truth: Active (19 Pages)")
    else:
        st.warning("Index PDF missing. Relying on verified internal nomenclature.")

    api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    if not api_key:
        st.caption("Store `GEMINI_API_KEY` in Streamlit Secrets for unauthenticated sessions.")

# ==========================================
# MAIN INTERFACE HEADER
# ==========================================
st.markdown("""
<div class="brand-header">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <div class="brand-title-row">
                <span class="brand-title">FERRULE</span>
                <span class="brand-author">by Dr. Sulaiman Alhowaish</span>
            </div>
            <div class="brand-subtitle">
                Autonomous Clinical Documentation & NPHIES SBS v3.0 Revenue Assurance Engine
            </div>
        </div>
        <div style="text-align: right; padding-top: 0.25rem;">
            <span class="tag-pill">SBS v3.0</span>
            <span class="tag-pill">ACHI 10th Ed</span>
            <span class="tag-pill-gold">NPHIES Core</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# PROMPT LOGIC & REGULATORY PRINCIPLES
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
   - Defective Restorations: Use K08.51 (Aesthetic failure), K08.52 (Overhang/defective margin/gap), K08.53 (Fractured restoration). NEVER USE K08.87.
   - Caries: K02.51, K02.52, K02.53 (Arrested/enamel/dentin with pulp involvement), K02.61, K02.62, K02.63 (Smooth surface), K02.71, K02.72 (Root caries).
   - Pulpal / Periapical: K04.01 (Reversible pulpitis), K04.02 (Irreversible pulpitis), K04.1 (Necrosis of pulp), K04.5 (Chronic apical periodontitis), K04.7 (Periapical abscess without sinus).
   - Periodontal: K05.10 (Chronic gingivitis), K05.31 (Chronic periodontitis, localized), K05.32 (Chronic periodontitis, generalized).
   - Surgical / Impacted: K01.1 (Impacted teeth), K01.0 (Embedded teeth).
   - Trauma: S02.51 (Enamel fracture), S02.52 (Crown fracture without pulp), S02.53 (Crown fracture with pulp), S03.2X1 (Luxation).

2. DIAGNOSTIC IMMUTABILITY RULE (ANTI-DRIFT):
   - If clinician input contains an existing "[PRIMARY_ICD10]" in a CONTINUITY BLOCK, YOU MUST RETAIN THAT EXACT CODE.
   - DO NOT alter, generalize, or shift the ICD-10-AM code across follow-up encounters of the same clinical episode.

================================================================================
UNIVERSAL MULTI-VISIT CONTINUITY & ANTI-UNBUNDLING RULES
================================================================================
1. RENDERED VS. PLANNED SCOPE DISCIPLINE:
   - ONLY bill procedures that were PHYSICALLY EXECUTED during today's visit.
   - Services noted as "planned for next visit", "indicated in future", or "pending restorability" MUST NOT appear in the Billable Coding Table for today's encounter.
   - Day 1 Disassembly / Diagnostic encounters (Exams, Radiographs, Crown sectioning 97655-00-00 [462]) are FULLY BILLABLE fee-for-service events. Do NOT lock them at 0.00 SAR.

2. MULTI-STAGE FABRICATION BUNDLING:
   - RPD/CD Visits 1-4, Indirect Crown/Bridge Visit 1, Multi-visit RCT Stage 1:
     * Primary Procedure Claim Action Flag: `[IN-PROGRESS / BUNDLED ENCOUNTER - NON-BILLABLE]`.
     * Tariff: `0.00 SAR`.
   - Final Insertion Encounters (e.g., Crown cementation, Denture delivery, RCT obturation):
     * Unlock code as `[PRIMARY CLAIM ITEM - GLOBAL DEFINITIVE]` with full statutory Article 11 tariff.

3. PREPARATORY EXCEPTIONS & ANATOMICAL MULTIPLICITY:
   - Crown removal (97655-00-00 [462]) must include specific quantity and FDI tooth identifiers (billed per unit).
   - Post and core (97625-xx [463]) includes the core. NEVER bill core build-up (97627-00-00 [463]) on the same tooth receiving a post.

================================================================================
CRITICAL FORMATTING MANDATE FOR CASE CONTINUITY BLOCK
================================================================================
You MUST output the continuity metadata block enclosed STRICTLY between `<NPHIES_BLOCK>` and `</NPHIES_BLOCK>` tags at the very end of your response.

Format inside the tags strictly as:
<NPHIES_BLOCK>
[EPISODE_ID]: [Specialty]-[Procedure]-[FDI Tooth/Arch]
[PRIMARY_ICD10]: [Code] — [Accurate 10th Ed Description]
[PRIMARY_SBS_CODE]: [SBS 9-digit Code] [Block]
[CURRENT_STAGE]: Visit [X] of [Total Visits] — [Description of Today's Step]
[BILLING_STATUS]: [IN_PROGRESS - CLAIM LOCKED (0.00 SAR) / BILLABLE ENCOUNTER (Tariff SAR) / GLOBAL CLAIM DELIVERED (Tariff SAR)]
[NEXT_VISIT_EXPECTED]: Visit [X+1] — [Description of Next Step]
[ANTI-UNBUNDLING_LOCK]: [LOCKED / EPISODE_ACTIVE / EPISODE_CLOSED]
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
   - Tariff: 0.00 for intermediate locked visits; realistic statutory Article 11 tariff for standalone or definitive procedures.
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

    if note_style == "Concise SmartForm Macro (Hospital Standard)":
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
    elif note_style == "Detailed SOAP Clinical Note (Hospital / Academic)":
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
# UI LAYOUT & WORKFLOW CONTROLS
# ==========================================
col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.markdown('<div class="sub-section-title">Clinical Encounter & Episode Record</div>', unsafe_allow_html=True)
    doctor_input = st.text_area(
        label="Clinical Case Input",
        label_visibility="collapsed",
        placeholder="Enter encounter details, clinical findings, or paste the NPHIES Case Continuity Token from a prior appointment...",
        height=180
    )
    
    st.markdown('<div class="sub-section-title">Audit Package Configuration</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        inc_icd = st.checkbox("ICD-10-AM Diagnosis", value=True)
    with c2:
        inc_billing = st.checkbox("SBS v3.0 / ACHI Table", value=True)
    with c3:
        inc_checklist = st.checkbox("NPHIES Checklist", value=True)
        
    note_style = st.radio(
        "EMR Documentation Format:",
        [
            "Concise SmartForm Macro (Hospital Standard)",
            "Detailed SOAP Clinical Note (Hospital / Academic)",
            "Coding & Regulatory Audit Only (Skip Note)"
        ],
        index=0
    )
    
    st.markdown('<div class="sub-section-title">Episode Staging Engine</div>', unsafe_allow_html=True)
    is_staged = st.checkbox(
        "Enable Multi-Visit Episode Continuity Guard", 
        value=True, 
        help="Locks intermediate stages to 0.00 SAR to protect against unbundling rejections, releasing the global tariff on definitive delivery."
    )
    staged_pathway = "Auto-detect from case input"
    if is_staged:
        staged_pathway = st.selectbox(
            "Target Clinical Pathway:",
            [
                "Auto-detect from case input",
                "Indirect Crown / Bridge — [Prep/Provisional -> Delivery]",
                "Removable Partial Denture (RPD) — [4-Stage Protocol]",
                "Complete Dentures (Bimaxillary) — [5-Stage Protocol]",
                "Endodontics (RCT) — [Biomechanical -> Obturation]",
                "Implant Prosthetics — [Surgical -> Uncovery -> Impression -> Delivery]"
            ]
        )
    
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    submit_btn = st.button("Audit Claim & Generate Documentation", type="primary", use_container_width=True)

with col_out:
    st.markdown('<div class="sub-section-title">Compliance Audit & Scrubbed Record</div>', unsafe_allow_html=True)
    if submit_btn:
        if not api_key:
            st.error("Missing Gemini API credentials. Configure GEMINI_API_KEY in repository secrets.")
        elif not doctor_input.strip():
            st.warning("Please supply an encounter narrative or case summary.")
        elif not (inc_icd or inc_billing or inc_checklist or note_style != "Coding & Regulatory Audit Only (Skip Note)"):
            st.warning("Select at least one output section to compile.")
        else:
            with st.spinner("Scrubbing documentation against CCHI SBS v3.0 & validating NPHIES state..."):
                try:
                    client = genai.Client(api_key=api_key)
                    dynamic_sys_instruction = construct_dynamic_instructions(
                        inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                    )
                    raw_result = generate_scrubbed_package(
                        client, doctor_input, cchi_index_text, dynamic_sys_instruction
                    )
                    
                    # Robust Dual-Pattern Token Matcher
                    nphies_match = re.search(r"<NPHIES_BLOCK>(.*?)</NPHIES_BLOCK>", raw_result, re.DOTALL)
                    if nphies_match:
                        block_content = nphies_match.group(1).strip()
                        clean_markdown = re.sub(r"<NPHIES_BLOCK>.*?</NPHIES_BLOCK>", "", raw_result, flags=re.DOTALL).strip()
                    else:
                        fallback_match = re.search(r"(\[EPISODE_ID\].*?\[ANTI-UNBUNDLING_LOCK\].*?$)", raw_result, re.DOTALL)
                        if fallback_match:
                            block_content = fallback_match.group(1).strip()
                            clean_markdown = raw_result[:fallback_match.start()].strip()
                            clean_markdown = re.sub(r"(?:🔄\s*)?(?:NPHIES Case Continuity Token.*?$|NPHIES CASE CONTINUITY BLOCK.*?$)", "", clean_markdown, flags=re.MULTILINE).strip()
                        else:
                            block_content = None
                            clean_markdown = raw_result.strip()
                    
                    st.markdown(clean_markdown)
                    
                    if block_content:
                        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
                        st.caption("NPHIES Episode Continuity Token (Persist across multi-visit encounters):")
                        st.code(block_content, language="text")
                    
                except Exception as e:
                    st.error(f"Audit engine execution failed: {str(e)}")
