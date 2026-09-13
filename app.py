import os
import re
import json
import time
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

st.set_page_config(
    page_title="FERRULE | Dr. Sulaiman Alhowaish",
    page_icon="favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ENTERPRISE CLINICAL CSS THEME (CANVAS-LOCKED)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Enforce Dark Canvas Across All Devices & OS Themes */
    html, body, .stApp {
        background-color: #0B0F19 !important;
        color: #F8FAFC !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Bar & Header Structure */
    .brand-header {
        margin-bottom: 1.25rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .brand-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.75rem;
    }
    .brand-title-group {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0.5rem 0.75rem;
    }
    .brand-title {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #F8FAFC !important;
        margin: 0;
        line-height: 1.1;
    }
    .brand-author {
        font-size: 1rem;
        font-weight: 600;
        color: #38BDF8 !important;
        letter-spacing: -0.01em;
        white-space: nowrap;
    }
    .brand-subtitle {
        font-size: 0.84rem;
        font-weight: 400;
        color: #94A3B8 !important;
        line-height: 1.45;
        margin-top: 0.4rem;
    }
    
    /* Tag Pills */
    .tag-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
    }
    .tag-pill {
        display: inline-block;
        padding: 0.22rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        background: rgba(14, 165, 233, 0.12);
        color: #38BDF8 !important;
        border: 1px solid rgba(56, 189, 248, 0.25);
    }
    .tag-pill-gold {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24 !important;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    
    /* Executive Profile Card (Sidebar) */
    .profile-card {
        background: rgba(30, 41, 59, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1.15rem;
        margin-bottom: 1.25rem;
    }
    .profile-name {
        font-size: 1.1rem;
        font-weight: 700;
        color: #F8FAFC !important;
        margin-bottom: 0.2rem;
    }
    .profile-role {
        font-size: 0.82rem;
        font-weight: 600;
        color: #38BDF8 !important;
        margin-bottom: 0.15rem;
    }
    .profile-org {
        font-size: 0.76rem;
        color: #94A3B8 !important;
        line-height: 1.4;
        margin-bottom: 0.75rem;
    }
    .profile-contact {
        font-size: 0.75rem;
        color: #CBD5E1 !important;
        line-height: 1.65;
        padding-top: 0.65rem;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }
    .profile-contact a {
        color: #38BDF8 !important;
        text-decoration: none;
    }
    .profile-contact a:hover {
        text-decoration: underline;
    }
    
    /* Typography & Section Titles */
    .sub-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94A3B8 !important;
        margin-top: 0.95rem;
        margin-bottom: 0.4rem;
    }
    
    /* Input Form Fields */
    .stTextArea textarea {
        background-color: #161F30 !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 8px !important;
        font-size: 0.88rem !important;
        line-height: 1.5 !important;
    }
    .stTextArea textarea::placeholder {
        color: #64748B !important;
    }
    
    /* Button Controls */
    div.stButton > button:first-child {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.88rem;
        letter-spacing: 0.01em;
        padding: 0.55rem 1.2rem;
    }

    /* Mobile Adaptations */
    @media (max-width: 768px) {
        .brand-top-row {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
        }
        .brand-title {
            font-size: 1.65rem;
        }
        .brand-author {
            font-size: 0.88rem;
        }
        .tag-container {
            margin-top: 0.2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CACHED REGULATORY GROUND TRUTH LOADERS
# ==========================================
@st.cache_data(show_spinner=False)
def load_cchi_regulatory_databases():
    # 1. Load SBS Procedure Index (PDF)
    pdf_text = ""
    pdf_filename = "sbs_dental_index.pdf"
    if os.path.exists(pdf_filename):
        try:
            reader = PdfReader(pdf_filename)
            extracted = [
                f"--- PAGE {i+1} ---\n{p.extract_text()}" 
                for i, p in enumerate(reader.pages) if p.extract_text()
            ]
            pdf_text = "\n".join(extracted)
        except Exception:
            pdf_text = ""

    # 2. Load ICD-10-AM Diagnostic Ground Truth (JSON)
    icd_list = []
    json_filename = "cchi_dental_icd10.json"
    if os.path.exists(json_filename):
        try:
            with open(json_filename, "r", encoding="utf-8") as f:
                icd_list = json.load(f)
        except Exception:
            icd_list = []

    # 3. Load & Auto-Sanitize Article 11 Tariffs (CSV)
    tariff_map = {}
    csv_filename = "cchi_article11_tariffs.csv"
    if os.path.exists(csv_filename):
        try:
            df = pd.read_csv(csv_filename, skiprows=1, encoding="utf-8", encoding_errors="ignore")
            df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)
            df.columns = df.columns.str.strip()
            
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.replace(r'[\r\n]+', '', regex=True).str.strip()
            
            for _, row in df.iterrows():
                hyphen_code = str(row.get("SBS code -Hyphenated", "")).strip()
                sbs_raw = row.get("SBSCode")
                sbs_num = ""
                if pd.notna(sbs_raw):
                    try:
                        sbs_num = str(int(float(sbs_raw))).zfill(9)
                    except Exception:
                        sbs_num = str(sbs_raw).strip()
                
                block_val = str(row.get("Block", "")).strip()
                if block_val.endswith(".0"):
                    block_val = block_val[:-2]

                entry = {
                    "sbs_hyphen": hyphen_code,
                    "sbs_code": sbs_num,
                    "price": str(row.get("Price", "")).strip(),
                    "short_desc": str(row.get("Short Description", "")).strip(),
                    "long_desc": str(row.get("Long Description", "")).strip(),
                    "block": block_val,
                    "specialty": str(row.get("Department/ Specialty", "")).strip()
                }
                
                if hyphen_code:
                    tariff_map[hyphen_code] = entry
                if sbs_num:
                    tariff_map[sbs_num] = entry
        except Exception:
            tariff_map = {}

    return pdf_text, icd_list, tariff_map

cchi_index_text, cchi_icd_db, cchi_tariff_map = load_cchi_regulatory_databases()

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

    api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    if not api_key:
        st.caption("Store `GEMINI_API_KEY` in Streamlit Secrets for unauthenticated sessions.")

# ==========================================
# MAIN INTERFACE HEADER
# ==========================================
st.markdown("""
<div class="brand-header">
    <div class="brand-top-row">
        <div class="brand-title-group">
            <h1 class="brand-title">FERRULE</h1>
            <span class="brand-author">by Dr. Sulaiman Alhowaish</span>
        </div>
        <div class="tag-container">
            <span class="tag-pill">SBS v3.0</span>
            <span class="tag-pill">ACHI 10th Ed</span>
            <span class="tag-pill-gold">NPHIES Core</span>
        </div>
    </div>
    <div class="brand-subtitle">
        Autonomous Clinical Documentation & NPHIES SBS v3.0 Revenue Assurance Engine
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# PROMPT LOGIC & REGULATORY PRINCIPLES
# ==========================================
BASE_PRINCIPLES = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.
You are provided with:
1. The full text of the official CCHI Saudi Billing System (SBS) Version 3 Dental Alphabetic Index.
2. The official ICD-10-AM Dental Diagnostic Ground Truth Concept Table.
3. The official Article 11 Statutory Government Sector Dental Price Schedule.

You MUST reference these sources to output exact 9-digit SBS codes, 7-digit ACHI codes, [Block] numbers, statutory SAR prices, and ICD-10-AM diagnoses.

================================================================================
CRITICAL RULE: NPHIES PRIOR-AUTHORIZATION (PA) DETERMINATION MATRIX
================================================================================
Evaluate billable procedures against official CCHI / NPHIES clearinghouse authorization tiers:

1. TIER 1: MANDATORY PRIOR AUTHORIZATION (Pre-Treatment Approval Required):
   - Fixed Prosthodontics: Single Crowns [Block 470], Bridges / Retainers [Block 471].
   - Removable Prosthodontics: Complete Dentures [Block 474], Cast Partial Dentures [Block 474].
   - Implantology: Fixture Placement [Block 400], Custom/Prefab Abutments & Crowns [Block 473].
   - Surgical Interventions: Impacted Tooth Surgical Extractions [Block 458], Periodontal Flap / Crown Lengthening [Block 456].
   - Orthodontics: Interceptive / Comprehensive Appliances [Blocks 480–483].
   * MANDATORY AUDIT REQUIREMENT: Must state required pre-operative radiograph (PA / Panoramic / CBCT) and clinical justification demonstrating restorability.

2. TIER 2: PA EXEMPT (Clean Direct Submission / Routine Encounters):
   - Oral Examinations & Consultations [Block 450].
   - Diagnostic Radiographs (PA, Bitewing, OPG) [Block 451].
   - Direct Restorations (Amalgam, Composite, GIC) [Blocks 460, 461].
   - Routine Non-Surgical Extractions [Block 457].
   - Prophylaxis & Scaling [Block 454].
   - Dental Emergency Relief of Pain [Block 484].

3. TIER 3: MULTI-VISIT ENDODONTICS (CONDITIONAL / STAGED):
   - Stage 1 (Pulpectomy / Emergency extirpation 97415-00-10): PA Exempt under acute pain protocol.
   - Stage 2 (Definitive Obturation 97417-00-10): Adjudicated under established episode authorization with post-operative PA radiograph verification.

================================================================================
CRITICAL RULE: ARTICLE 11 STATUTORY TARIFF ACCURACY
================================================================================
1. TARIFF PRICE ENFORCEMENT:
   - For all billable dental procedures, retrieve the exact statutory price from the Article 11 Tariff ground truth.
   - If an intermediate stage or component is listed as "part of main service and / or follow ups", or is part of an uncompleted multi-visit fabrication, its current encounter tariff MUST BE "0.00 SAR" with Claim Action Flag [IN-PROGRESS / BUNDLED ENCOUNTER - NON-BILLABLE].
   - When billing the definitive completed procedure (e.g. Denture Insertion 97719-01-70, Crown delivery, completed RCT), apply the full Article 11 statutory tariff.

================================================================================
CRITICAL RULE: ICD-10-AM SPECIFICITY & DIAGNOSTIC IMMUTABILITY
================================================================================
1. STRICT ADHERENCE TO GROUND TRUTH TABLE:
   - Select diagnostic codes strictly from the provided ICD-10-AM Concept Table.
   - Caries: K02.0, K02.1, K02.2, K02.3, K02.5.
   - Pulpal / Periapical: K04.0, K04.1, K04.2, K04.4, K04.5, K04.6, K04.7.
   - Periodontal: K05.1, K05.3.
   - Edentulism / Loss of teeth: K08.1.
   - Failures / Fractures: K08.81 (Pathological fracture of tooth), K08.88 (Other specified disorders).
   - Status: Z01.2 (Dental examination), Z96.5 (Presence of tooth-root and mandibular implants), Z97.2 (Presence of dental prosthetic device).
   - Trauma: S02.5 (Fracture of tooth), S03.2 (Dislocation of tooth).

2. DIAGNOSTIC IMMUTABILITY RULE (ANTI-DRIFT):
   - If clinician input contains an existing "[PRIMARY_ICD10]" inside an incoming CONTINUITY BLOCK, YOU MUST LOCK AND REPEAT THAT EXACT CODE.
   - DO NOT alter, generalize, or shift the ICD-10-AM code across follow-up encounters of the same episode.

================================================================================
UNIVERSAL MULTI-VISIT CONTINUITY & ANTI-UNBUNDLING RULES
================================================================================
1. RENDERED VS. PLANNED SCOPE DISCIPLINE:
   - ONLY bill procedures that were PHYSICALLY EXECUTED during today's encounter.
   - Services noted as "planned for next visit", "indicated in future", or "pending restorability" MUST NOT appear in the Billable Coding Table for today's encounter.
   - Diagnostic and Disassembly encounters (Comprehensive Exam 97011-00-00 [450] - 150 SAR, Radiographs [451] - 120 SAR, Crown sectioning 97655-00-00 [462] - 200 SAR) are FULLY BILLABLE fee-for-service events on Day 1.

2. MULTI-STAGE FABRICATION BUNDLING:
   - Intermediate visits (RPD/CD Visits 1-4, Indirect Crown Visit 1, Multi-visit RCT Stage 1) are non-billable components locked to 0.00 SAR.
   - Final Delivery / Obturation encounter unlocks the global statutory fee.

3. PREPARATORY EXCEPTIONS & ANATOMICAL MULTIPLICITY:
   - Post and core (97625-xx [463]) inherently includes the coronal core. NEVER bill core build-up (97627-00-00 [463]) on the same tooth receiving a post.

================================================================================
CRITICAL FORMATTING MANDATE FOR CASE CONTINUITY BLOCK
================================================================================
You MUST output the continuity metadata block enclosed STRICTLY between `<NPHIES_BLOCK>` and `</NPHIES_BLOCK>` tags at the very end of your response.

Format inside the tags strictly as:
<NPHIES_BLOCK>
[EPISODE_ID]: [Specialty]-[Procedure]-[FDI Tooth/Arch]
[PRIMARY_ICD10]: [Code] — [Accurate Description]
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
{sec_num}. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM)
   - Specific, valid ICD-10-AM code from the ground truth table. If site/cause is unspecified, provide code with `[Specify Tooth/Arch]` placeholder.
""")
        sec_num += 1

    if inc_billing:
        instructions.append(f"""
{sec_num}. BILLABLE CODING TABLE (SBS v3.0 & ACHI 10th Ed)
   - Columns MUST strictly be:
     `Service Description` | `ACHI Code` | `SBS v3.0 Code` | `Block` | `Claim Action Flag` | `Govt Tariff (SAR)* [Art. 11]` | `Bundled Elements (NON-BILLABLE)`
   - Tariff: 0.00 for intermediate locked visits; exact statutory Article 11 tariff for standalone or definitive procedures.
   - Immediately below table: `*Tariff prices are determined in accordance with Article 11: "Dental services pricing in government sector".`
   - Sub-table: "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)" if alternatives exist.
""")
        sec_num += 1

    if inc_checklist:
        instructions.append(f"""
{sec_num}. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES)
   - Single-line concise audit checks:
     * **Anatomical Site Verification:** [FDI tooth number / Quadrant / Arch].
     * **NPHIES Prior-Authorization (PA) Tier:** [MANDATORY (Pre-treatment approval required) / EXEMPT (Direct submission) / CONDITIONAL (Episode linked)].
     * **Mandatory Diagnostic Attachments:** [Pre-op PA / OPG / Clinical Photo / Periodontal Charting / None required].
     * **Clinical Justification Sentence:** [Concise 1-line justification satisfying medical necessity for clearinghouse audit].
     * **#1 Technical Denial Trap:** [The exact compliance mistake that causes rejection for this specific procedure].
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

def generate_scrubbed_package(client, doctor_input, cchi_text, icd_db, tariff_map, system_instruction):
    icd_reference = "\n".join([f"- {item['code']}: {item['title']} ({item['category']})" for item in icd_db]) if icd_db else "[Built-in ICD-10-AM Active]"

    tariff_sample = []
    if tariff_map:
        for k, v in list(tariff_map.items())[:120]:
            tariff_sample.append(f"{v['sbs_hyphen']} ({v['sbs_code']}) | Block {v['block']} | {v['short_desc']} -> SAR {v['price']}")
        tariff_reference = "\n".join(tariff_sample)
    else:
        tariff_reference = "[Article 11 Built-in Tariffs Active]"

    prompt_payload = f"""
OFFICIAL CCHI SBS VERSION 3 DENTAL ALPHABETIC INDEX (ACHI PROCEDURES GROUND TRUTH):
{cchi_text if cchi_text else "[Built-in ACHI/SBS Knowledge Active]"}

OFFICIAL ICD-10-AM DENTAL DIAGNOSTIC CONCEPT TABLE (MANDATORY DIAGNOSIS GROUND TRUTH):
{icd_reference}

OFFICIAL CCHI ARTICLE 11 STATUTORY DENTAL TARIFF SCHEDULE:
{tariff_reference}

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
            with st.spinner("Scrubbing documentation against CCHI SBS v3.0 & Article 11 Tariffs..."):
                try:
                    client = genai.Client(api_key=api_key)
                    dynamic_sys_instruction = construct_dynamic_instructions(
                        inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                    )
                    raw_result = generate_scrubbed_package(
                        client, doctor_input, cchi_index_text, cchi_icd_db, cchi_tariff_map, dynamic_sys_instruction
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
