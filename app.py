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
    
    html, body, .stApp {
        background-color: #0B0F19 !important;
        color: #F8FAFC !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
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
        font-size: 0.80rem;
        font-weight: 600;
        color: #38BDF8 !important;
        margin-bottom: 0.15rem;
        line-height: 1.35;
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
    
    .sub-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94A3B8 !important;
        margin-top: 0.95rem;
        margin-bottom: 0.4rem;
    }
    
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
    
    div.stButton > button:first-child {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.88rem;
        letter-spacing: 0.01em;
        padding: 0.55rem 1.2rem;
    }

    .interactive-card {
        background: rgba(14, 165, 233, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

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
# SESSION STATE INITIALIZATION
# ==========================================
if "discovery_questions" not in st.session_state:
    st.session_state.discovery_questions = None
if "pending_case_input" not in st.session_state:
    st.session_state.pending_case_input = ""
if "final_scrubbed_output" not in st.session_state:
    st.session_state.final_scrubbed_output = None

# ==========================================
# CACHED REGULATORY GROUND TRUTH LOADERS
# ==========================================
@st.cache_data(show_spinner=False)
def load_cchi_regulatory_databases():
    # 1. SBS Procedure Index (PDF)
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

    # 2. ICD-10-AM Diagnostic Ground Truth (JSON)
    icd_list = []
    json_filename = "cchi_dental_icd10.json"
    if os.path.exists(json_filename):
        try:
            with open(json_filename, "r", encoding="utf-8") as f:
                icd_list = json.load(f)
        except Exception:
            icd_list = []

    # 3. Complete Article 11 Statutory Tariff Schedule (All 712 Procedures)
    tariff_entries = []
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
                hyphen = str(row.get("SBS code -Hyphenated", "")).strip()
                block = str(row.get("Block", "")).split(".")[0].strip()
                desc = str(row.get("Short Description", "")).strip()
                price = str(row.get("Price", "")).strip()
                spec = str(row.get("Department/ Specialty", "")).strip()
                if hyphen:
                    tariff_entries.append(f"{hyphen} [Block {block}] ({spec}) {desc} -> SAR {price}")
        except Exception:
            tariff_entries = []

    tariff_text = "\n".join(tariff_entries) if tariff_entries else "[Article 11 Built-in Tariffs Active]"
    return pdf_text, icd_list, tariff_text

cchi_index_text, cchi_icd_db, cchi_tariff_reference = load_cchi_regulatory_databases()

# ==========================================
# SIDEBAR: EXECUTIVE ARCHITECT & CREDENTIALS
# ==========================================
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <div class="profile-name">Dr. Sulaiman Alhowaish</div>
        <div class="profile-role">Deputy Manager & Prosthodontics Registrar, Dental Department</div>
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
    * **MSc** | Executive Master in Insurance (KSU)  
    * **BDS** | Bachelor of Dental Surgery  
    * **CPC®** | Certified Professional Coder (AAPC)  
    * **IBM SkillsBuild** | AI in Healthcare
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
You are an expert Certified Professional Coder (CPC), Dental Revenue Cycle Auditor, and Clinical Documentation Improvement (CDI) Specialist in Saudi Arabia.
Your objective is PROACTIVE DENIAL PREVENTION, STATUTORY ARTICLE 11 REVENUE ASSURANCE, and CLINICAL DOCUMENTATION STANDARDIZATION across all dental specialties.

You are grounded in:
1. Official CCHI Saudi Billing System (SBS) v3.0 Dental Alphabetic Index & Tabular List.
2. Official SBS Coding Standards (SBSCS v3.0, October 2025).
3. Official ICD-10-AM Dental Diagnostic Ground Truth Concept Table (Chapter XI, Trauma, Status).
4. Official Article 11 Statutory Government Sector Dental Tariff Schedule (712 Procedures).
5. CCHI Pre-Approval Policies and NPHIES Clearinghouse Adjudication Standards.

================================================================================
1. CCHI / NPHIES PRIOR-AUTHORIZATION (PA) RULES & THE 500 SAR THRESHOLD
================================================================================
- MANDATORY 500 SAR EXEMPTION (CCHI Pre-Approval Policy, Chap. 4, Sec. 2):
  Any outpatient dental service where the one-time treatment is LESS THAN 500 SAR is STRICTLY EXEMPT from Prior Authorization.
  * LEVEL 1 NPHIES VIOLATION ALERT: Requesting PA for services < 500 SAR (e.g. routine exams, radiographs, simple extractions, minor fillings) is an official violation. Mark these strictly as:
    [PA EXEMPT: Clean Direct Claim (Service < 500 SAR Threshold)].
- PA MANDATORY (Services >= 500 SAR & Major Interventions):
  Indirect crowns [Block 470], bridges [Block 471], dentures [Block 474], implants [Block 400], completed RCT [Block 462], and surgical extractions [Block 458] require pre-approval.
  * STATUTORY 60-MIN SLA: Insurers must adjudicate requests within 60 minutes. If delayed beyond 60 minutes, the service is legally DEEMED APPROVED under Chapter 5.
  * REJECTION SAFEGUARD: Rejections can only be issued by a Senior Specialist (أخصائي أول) in the same clinical specialty.
- EMERGENCY & ACUTE PAIN: Triage levels 1-3 and emergency pulp extirpation (97419-00-10) are PA-EXEMPT under the 24-hour notification rule.

================================================================================
2. OFFICIAL SBSCS DENTAL CODING & BUNDLING STANDARDS (SBSCS 4000 - 4092)
================================================================================
- ANATOMICAL SITE: Tooth number(s) must be recorded using the FDI two-digit numbering system (Permanent 11-48, Primary 51-85).
- CONDITION ONSET FLAG (COF): Report COF = 2 (Present upon presentation) for pre-existing conditions; COF = 1 for conditions arising during the episode.
- LOCAL ANESTHESIA (SBSCS 3012 & 4010):
  * For non-admitted care, anesthesia IS coded using SBS codes with a 2-character ASA extension: Infiltration 92513-xx-00 [1909] or Trigeminal Nerve Block 92509-xx-10 [1909] (default: ASA 99 if unstated).
  * In the Billable Table, list local anesthesia with Claim Action Flag: [CODED COMPONENT - INCLUDED IN CLINICAL VISIT] (Govt Article 11 Tariff applies if billed in specialized surgery).
- RESTORATIVE (SBSCS 4030):
  * Direct restorations are coded by material and surface add-on model:
    - 1 surface: 97521-01-10 [466] (adhesive) or 97511-01-10 [465] (metallic).
    - Additional surfaces: 97521-02-00 [466] or 97511-02-00 [465] multiplied by (Total Surfaces - 1).
  * Contiguous surfaces on the same tooth (e.g. MO) must be billed as ONE multi-surface restoration, NEVER two separate 1-surface restorations.
  * Routine steps (rubber dam, isolation, liners/bases, etch, bond, matrix, polishing) are bundled and non-billable.
- ENDODONTICS (SBSCS 4042):
  * Completed RCT is billed as ONE code per tooth based on tooth type: Anterior (97420-01-00), Premolar (97420-02-00), Molar (97420-03-00). Inherently includes extirpation, instrumentation, and obturation.
  * Emergency/palliative pulpectomy is 97419-00-10 (SAR 1,500). NEVER bill 97419-00-10 concurrently on the same day as completed RCT (97420-xx).
  * Primary Diagnosis must be K04.0 (Pulpitis). K02.5 (Caries with pulp exposure) is prohibited unless pulp was exposed during caries removal and irreversible pulpitis was clinically excluded.
- ORAL SURGERY (SBSCS 4010 & Article 11):
  * Routine extraction: 97311-01-10 [457] (SAR 300).
  * Surgical removal of tooth (soft tissue): 97321-05-00 [458] (SAR 800).
  * Surgical removal of impacted tooth (partial bony): 97321-01-00 [458] (SAR 1,500).
  * Surgical removal of impacted tooth (complete bony): 97321-02-00 [458] (SAR 1,500).
  * Note: 97322-09/10 is reserved exclusively for Full Upper/Lower Dental Clearance (SAR 3,000).
  * Flap elevation, debridement, bone contouring, and suturing are bundled into surgical extraction.
- PROSTHODONTICS (SBSCS 4060):
  * Removable denture fabrication steps (97719-01-10 through 97719-01-60 and 97719-01-80) are STATUTORY NON-BILLABLE items for documentation only (0.00 SAR, [IN-PROGRESS / BUNDLED ENCOUNTER]).
  * Full denture insertion (97719-01-70 / 97719-00-00) unlocks the global statutory fee (SAR 8,000).
  * Post & Core (97625-xx): Includes core build-up. Never bill separate core build-up (97627-00-10) on the same tooth receiving a post.
- ORTHODONTICS (SBSCS 4080):
  * Comprehensive orthodontic exam (97011-00-20 [450], SAR 500.00) INHERENTLY INCLUDES: intraoral photos, extraoral photos, OPG, cephalometric radiographs, cephalometric tracings, and study casts/digital models.
  * STRICT ANTI-UNBUNDLING RULE: Under SBSCS 4080 Rule 1, NONE of these diagnostic records can be assigned a separate billable code or fee when 97011-00-20 is billed. They MUST appear only as bundled non-billable elements (0.00 SAR).
================================================================================
3. ARTICLE 11 STATUTORY GOVERNMENT TARIFF PRICING
================================================================================
Output the exact statutory tariff from the attached Article 11 schedule.
Key Reference Benchmarks:
- Comprehensive Oral Exam (97011-00-00): 150 SAR
- Periodic Oral Exam (97012-00-00): 100 SAR
- Limited / Emergency Oral Exam (97013-00-00 / 97915-00-10): 100 SAR
- Intraoral PA Radiograph (97022-00-10): 120 SAR
- Bitewing Radiograph (97022-00-20): 120 SAR
- Routine Tooth Extraction (97311-01-10): 300 SAR
- Crown Sectioning & Removal (97655-00-00): 200 SAR
- Post Removal (97452-00-00): 350 SAR
- Emergency Extirpation (97419-00-10): 1,500 SAR
- Completed RCT (Molar 97420-03-00 / Premolar 97420-02-00 / Anterior 97420-01-00): 1,500 SAR
- Monolithic Zirconia Crown (97613-02-00): 3,000 SAR
- Porcelain Fused to Metal Crown (97615-10-00): 2,500 SAR
- Complete Denture Insertion (97719-01-70): 8,000 SAR
- One-Stage Implant Fixture (45846-00-00): 4,000 SAR

================================================================================
4. CASE CONTINUITY METADATA BLOCK MANDATE
================================================================================
Enclose strictly between <NPHIES_BLOCK> and </NPHIES_BLOCK> tags at the very end:
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

DISCOVERY_EVALUATOR_PROMPT = """
You are an expert Dental Clinical Documentation Specialist and Revenue Cycle Auditor in Saudi Arabia.
Your task is to analyze a clinician's preliminary case notes and determine whether critical data points required by CCHI, NPHIES, and Saudi Billing System Coding Standards (SBSCS v3.0) are missing or ambiguous.

CRITICAL CLINICAL & REGULATORY CHECKS:
1. Anatomical Site: Is an exact FDI two-digit tooth number (11-48, 51-85) or specific quadrant/arch clearly specified?
2. Diagnostic Specificity: Is the pulpal/periapical status, caries depth, tooth wear, or edentulous condition precise?
3. Objective Radiography: Are the required pre-op, working length, or post-op radiographs explicitly mentioned?
4. Procedural Mechanics:
   - For restorations: Are specific surfaces (O, MO, MOD, etc.) and materials clear?
   - For RCT: Is it emergency extirpation vs. definitive obturation? Canals identified?
   - For crowns: Is it preparation/provisional vs. definitive delivery?
   - For surgery/implants: Are torque, flap details, or bone levels noted?
5. Anesthesia & Isolation: Are local anesthesia (infiltration/block) and rubber dam isolation documented?

OUTPUT FORMAT:
- If the case is thoroughly detailed and ready for instant audit without ambiguity, respond with EXACTLY:
  `[READY_TO_AUDIT]`
- If critical information is missing, ambiguous, or incomplete, DO NOT generate the final audit. Instead, output:
  ### 📋 Interactive Intake Assessment
  Provide a brief 1-2 sentence evaluation of the case clarity.

  ### ❓ Clinician Clarification Checklist:
  Provide 3 to 5 concise, actionable clinical questions to help the clinician supply the missing facts. For each question, offer quick-select hints or examples (e.g. *Tooth #46?*, *Infiltration vs. ID Block?*, *Surfaces: MOD?*, *Pre-op PA taken?*).
"""

def evaluate_encounter_completeness(client, doctor_input):
    prompt = f"CLINICIAN ENCOUNTER ENTRY:\n{doctor_input}"
    response = client.models.generate_content(
        model="gemini-3.7-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=DISCOVERY_EVALUATOR_PROMPT,
            temperature=0.1,
        )
    )
    return response.text.strip()

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
   - Include Condition Onset Flag (COF): State `COF = 2 (Present on admission)` or `COF = 1 (Developed during episode)`.
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
     * **Condition Onset Flag (COF):** [COF = 2 (Present upon presentation) / COF = 1].
     * **NPHIES Prior-Authorization (PA) Status:** [PA EXEMPT: Service < 500 SAR (Level 1 Violation to request PA) / PA MANDATORY: Service >= 500 SAR (60-min SLA enforced) / PA EXEMPT: Emergency Acute Pain Protocol (24-hr notification)].
     * **Mandatory Diagnostic Attachments:** [Pre-op PA / Working Length PA / Post-op PA / OPG / CBCT / Clinical Photo / Periodontal Charting / None required].
     * **Clinical Justification Sentence:** [Concise 1-line medical necessity statement for clearinghouse audit].
     * **#1 Technical Denial Trap:** [The exact compliance error that triggers rejection for this specific code].
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
     **Anesthesia:** [None / Infiltration: Specify Agent & Dose / Nerve Block]
     **Radiographs:** [None / Pre-op PA / Post-op PA: Specify Finding]
     **Isolation:** [Single-tooth Rubber Dam Isolation documented]
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

def generate_scrubbed_package(client, doctor_input, cchi_text, icd_db, tariff_text, system_instruction):
    icd_reference = "\n".join([f"- {item['code']}: {item['title']} ({item['category']})" for item in icd_db]) if icd_db else "[Built-in ICD-10-AM Active]"

    prompt_payload = f"""
OFFICIAL CCHI SBS VERSION 3 DENTAL ALPHABETIC INDEX (ACHI PROCEDURES GROUND TRUTH):
{cchi_text if cchi_text else "[Built-in ACHI/SBS Knowledge Active]"}

OFFICIAL ICD-10-AM DENTAL DIAGNOSTIC CONCEPT TABLE (MANDATORY DIAGNOSIS GROUND TRUTH):
{icd_reference}

OFFICIAL CCHI ARTICLE 11 STATUTORY GOVERNMENT DENTAL TARIFF SCHEDULE (COMPLETE 712 PROCEDURES):
{tariff_text}

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
    
    guided_mode = st.checkbox(
        "Enable Interactive Guided Discovery Mode",
        value=False,
        help="Recommended for trainees and busy clinicians. If key details (FDI tooth number, vital signs, radiograph types, or specific surfaces) are missing, FERRULE pauses to ask clarifying questions before generating the final claim."
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
            client = genai.Client(api_key=api_key)
            st.session_state.final_scrubbed_output = None
            
            if guided_mode:
                with st.spinner("Analyzing case completeness against CCHI/NPHIES criteria..."):
                    try:
                        discovery_eval = evaluate_encounter_completeness(client, doctor_input)
                        if "[READY_TO_AUDIT]" in discovery_eval:
                            st.session_state.discovery_questions = None
                            st.session_state.pending_case_input = ""
                            dynamic_sys_instruction = construct_dynamic_instructions(
                                inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                            )
                            st.session_state.final_scrubbed_output = generate_scrubbed_package(
                                client, doctor_input, cchi_index_text, cchi_icd_db, cchi_tariff_reference, dynamic_sys_instruction
                            )
                        else:
                            st.session_state.discovery_questions = discovery_eval
                            st.session_state.pending_case_input = doctor_input
                    except Exception as e:
                        st.error(f"Guided analysis failed: {str(e)}")
            else:
                st.session_state.discovery_questions = None
                st.session_state.pending_case_input = ""
                with st.spinner("Scrubbing documentation against CCHI SBS v3.0 & Article 11 Tariffs..."):
                    try:
                        dynamic_sys_instruction = construct_dynamic_instructions(
                            inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                        )
                        st.session_state.final_scrubbed_output = generate_scrubbed_package(
                            client, doctor_input, cchi_index_text, cchi_icd_db, cchi_tariff_reference, dynamic_sys_instruction
                        )
                    except Exception as e:
                        st.error(f"Audit engine execution failed: {str(e)}")

    # Guided Discovery Mode: Clarification Loop
    if st.session_state.discovery_questions:
        st.markdown('<div class="interactive-card">', unsafe_allow_html=True)
        st.markdown(st.session_state.discovery_questions)
        st.markdown("</div>", unsafe_allow_html=True)
        
        clarification_input = st.text_area(
            "Quick Clinician Clarifications (Type missing details below):",
            placeholder="e.g. Tooth #36, vital cold test negative, pre-op PA taken, 3 canals instrumented, Cavit temp placed...",
            height=110
        )
        
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            finalize_guided = st.button("Finalize & Generate Audit-Proof Claim", type="primary", use_container_width=True)
        with btn_c2:
            cancel_guided = st.button("Reset / Clear Assessment", use_container_width=True)
            
        if cancel_guided:
            st.session_state.discovery_questions = None
            st.session_state.pending_case_input = ""
            st.session_state.final_scrubbed_output = None
            st.rerun()
            
        if finalize_guided:
            if not api_key:
                st.error("Missing Gemini API credentials.")
            else:
                with st.spinner("Synthesizing clinical input and running regulatory audit..."):
                    try:
                        client = genai.Client(api_key=api_key)
                        merged_input = f"{st.session_state.pending_case_input}\n\nCLINICAL CLARIFICATIONS PROVIDED:\n{clarification_input}"
                        dynamic_sys_instruction = construct_dynamic_instructions(
                            inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                        )
                        st.session_state.final_scrubbed_output = generate_scrubbed_package(
                            client, merged_input, cchi_index_text, cchi_icd_db, cchi_tariff_reference, dynamic_sys_instruction
                        )
                        st.session_state.discovery_questions = None
                        st.session_state.pending_case_input = ""
                    except Exception as e:
                        st.error(f"Finalization failed: {str(e)}")

    # Render Final Audit Results
    if st.session_state.final_scrubbed_output:
        raw_result = st.session_state.final_scrubbed_output
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
