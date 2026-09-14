import os
import re
import json
import time
import sqlite3
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(
    page_title="FERRULE | Dr. Sulaiman Alhowaish",
    page_icon="favicon.svg" if os.path.exists("favicon.svg") else "🦷",
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
# BACKEND: REGULATORY ASSET INGESTION & FTS5 RAG
# ==========================================
@st.cache_data(show_spinner=False)
def load_all_regulatory_assets():
    # 1. Statutory Article 11 Dental Tariffs (712 Procedures)
    tariffs = []
    if os.path.exists("cchi_article11_tariffs.csv"):
        try:
            df = pd.read_csv("cchi_article11_tariffs.csv", skiprows=1, encoding="utf-8", encoding_errors="ignore")
            df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)
            df.columns = df.columns.str.strip()
            for _, r in df.iterrows():
                hyphen = str(r.get("SBS code -Hyphenated", "")).strip()
                block = str(r.get("Block", "")).split(".")[0].strip()
                desc = str(r.get("Short Description", "")).strip()
                price = str(r.get("Price", "")).strip()
                spec = str(r.get("Department/ Specialty", "")).strip()
                if hyphen and hyphen != "nan":
                    tariffs.append(f"{hyphen} [Block {block}] ({spec}) {desc} -> SAR {price}")
        except Exception:
            tariffs = []

    # 2. ICD-10-AM Diagnostic Ground Truth
    icd_list = []
    if os.path.exists("cchi_dental_icd10.json"):
        try:
            with open("cchi_dental_icd10.json", "r", encoding="utf-8") as f:
                icd_list = json.load(f)
        except Exception:
            icd_list = []

    # 3. NPHIES Denial Triggers (86 Rules)
    denials = []
    if os.path.exists("nphies_denial_rules.json"):
        try:
            with open("nphies_denial_rules.json", "r", encoding="utf-8") as f:
                drules = json.load(f)
                denials = [f"- Code {r.get('Code')}: {r.get('Description')}" for r in drules if r.get("Code")]
        except Exception:
            denials = []

    # 4. Official NPHIES FDI Tooth Surface Syntax
    surfaces = []
    if os.path.exists("appendix_fdi_tooth_surface.json"):
        try:
            with open("appendix_fdi_tooth_surface.json", "r", encoding="utf-8") as f:
                srules = json.load(f)
                surfaces = [f"{r.get('Code', r.get('code'))}: {r.get('Display', r.get('display', ''))}" for r in srules]
        except Exception:
            surfaces = ["M: Mesial", "O: Occlusal", "D: Distal", "B: Buccal", "L: Lingual", "P: Palatal", "I: Incisal", "V: Vestibular"]

    return (
        "\n".join(tariffs) if tariffs else "[Article 11 Built-in Tariffs Active]",
        icd_list,
        "\n".join(denials) if denials else "[NPHIES 86 Denial Triggers Active]",
        ", ".join(surfaces)
    )

tariff_reference, icd_db, nphies_denial_context, fdi_surface_reference = load_all_regulatory_assets()

def query_fts5_rag_knowledge(query_narrative, max_chunks=4):
    db_path = "ferrule_knowledge.db"
    if not os.path.exists(db_path):
        return ""
    
    tokens = re.findall(r'[A-Za-z0-9_]{3,}', query_narrative)
    stopwords = {"patient", "tooth", "teeth", "presented", "under", "with", "dental", "treatment", "procedure", "performed"}
    valid_tokens = [t for t in tokens if t.lower() not in stopwords]
    
    if not valid_tokens:
        valid_tokens = ["dental", "periodontal", "restoration", "crown", "canal"]
        
    fts_match_query = " OR ".join(valid_tokens[:8])
    
    snippets = []
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT source_file, page_num, snippet(corpus_fts, 3, '[', ']', '...', 14)
            FROM corpus_fts
            WHERE corpus_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (fts_match_query, max_chunks))
        
        for sf, pn, snip in cur.fetchall():
            clean_snip = snip.replace('\n', ' ').strip()
            snippets.append(f"• [{sf} | Page {pn}]: {clean_snip}")
        conn.close()
    except Exception:
        snippets = []
        
    return "\n".join(snippets) if snippets else ""

# ==========================================
# SIDEBAR: EXECUTIVE PROFILE
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
BASE_PRINCIPLES = f"""
You are an expert Certified Professional Coder (CPC), Dental Revenue Cycle Auditor, and Clinical Documentation Improvement (CDI) Specialist in Saudi Arabia.
Your objective is PROACTIVE DENIAL PREVENTION, STATUTORY ARTICLE 11 REVENUE ASSURANCE, and CLINICAL DOCUMENTATION STANDARDIZATION across all dental specialties.

You are grounded in:
1. Official CCHI Saudi Billing System (SBS) v3.0 Dental Alphabetic Index & Tabular List.
2. Official SBS Coding Standards (SBSCS v3.0, October 2025).
3. Official ICD-10-AM Dental Diagnostic Ground Truth Concept Table (Chapter XI, Trauma, Status).
4. Official Article 11 Statutory Government Sector Dental Tariff Schedule (712 Procedures).
5. CCHI Pre-Approval Policies, CHI Implementing Regulations, and NPHIES Adjudication Standards.

================================================================================
1. DUAL TAXONOMY & ENCOUNTER ROUTING MANDATE (NPHIES COMPLIANCE)
================================================================================
- OUTPATIENT DENTAL CARE: Billed using the Australian Schedule of Dental Services and Glossary (ADA item numbers mapped to SBS v3.0 `97xxx-xx-xx` format).
- INPATIENT / OPERATING ROOM / MAXILLOFACIAL CARE: Billed using ICD-10-AM Diagnosis + 7-digit ACHI 10th Edition procedure codes.
- TOOTH NOTATION: Strictly mandatory FDI two-digit numbering (Permanent 11-48, Deciduous 51-85).
- TOOTH SURFACES: Strictly validate against NPHIES Codeable Concepts: {fdi_surface_reference}. Multi-surface restorations MUST be billed as ONE multi-surface code, never separated.

================================================================================
2. CCHI / NPHIES PRIOR-AUTHORIZATION (PA) RULES & THE 500 SAR THRESHOLD
================================================================================
- MANDATORY 500 SAR EXEMPTION (CCHI Pre-Approval Policy, Chap. 4, Sec. 2):
  Any outpatient dental service where the one-time treatment is LESS THAN 500 SAR is STRICTLY EXEMPT from Prior Authorization.
  * LEVEL 1 NPHIES VIOLATION ALERT: Requesting PA for services < 500 SAR is an official violation. Mark these strictly as:
    [PA EXEMPT: Clean Direct Claim (Service < 500 SAR Threshold)].
- PA MANDATORY (Services >= 500 SAR & Major Interventions):
  Indirect crowns [Block 470], bridges [Block 471], dentures [Block 474], implants [Block 400], completed RCT [Block 462], surgical extractions [Block 458], and periodontal surgery [Block 456] require pre-approval.
  * STATUTORY 60-MIN SLA: Insurers must adjudicate requests within 60 minutes. If delayed beyond 60 minutes, the service is legally DEEMED APPROVED under Chapter 5.
  * REJECTION SAFEGUARD: Rejections can only be issued by a Senior Specialist (أخصائي أول) in the same clinical specialty.
- TIMELY FILING DEADLINES (CHI Implementing Regulations, Article 90):
  * Private sector claims: must be submitted within 30 days of service.
  * Government sector / Health Clusters: must be submitted within 45 days of service.
  * Insurer settlement deadline: 30 days from receipt.
  * Re-submission turnaround for rejected claims: strictly 15 days.

================================================================================
3. OFFICIAL SBSCS DENTAL CODING & BUNDLING STANDARDS (SBSCS 4000 - 4092)
================================================================================
- Crown Lengthening (97238-00-00 [456]): Strictly EXCLUDES and CANNOT be billed concurrently with routine periodontal flap surgery (97232-xx). Cite Tabular List Page 167 exclusion.
- Endodontics (SBSCS 4042): Completed RCT is billed as ONE code per tooth based on type (Molar 97420-03-00, Premolar 97420-02-00, Anterior 97420-01-00). Inherently bundles extirpation, instrumentation, and obturation. NEVER bill emergency pulpectomy (97419-00-10) concurrently on the same day. Requires pre-op radiograph.
- Prosthodontics (SBSCS 4060): Denture fabrication stages (97719-01-10 through 97719-01-60) are non-billable (0.00 SAR). Full denture insertion (97719-01-70 / 97719-00-00) unlocks the global statutory fee (SAR 8,000). Post & core (97625-xx) includes core build-up; do not bill separate core build-up.
- Orthodontics (SBSCS 4080): Comprehensive exam (97011-00-20, SAR 500) inherently includes intra/extraoral photos, OPG, ceph, tracings, and study models. Separate billing is strictly prohibited.
- Periodontal Surgery (SBSCS 4021): Flap entry and closure are coded separately from tissue regeneration. Bone graft (97244-00-00, SAR 2,000); GTR membrane (97236-00-00, SAR 1,500). Medical necessity requires documented probing depth >= 4mm and BOP.

================================================================================
4. NPHIES CLEARINGHOUSE DENIAL PROTECTION RULES
================================================================================
Proactively guard the claim against these active NPHIES denial triggers:
{nphies_denial_context}

================================================================================
5. CASE CONTINUITY METADATA BLOCK MANDATE
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
Analyze the clinician's case note and determine whether critical data points required by CCHI, NPHIES, and SBSCS v3.0 are missing or ambiguous.

CRITICAL CHECKS:
1. Anatomical Site: Exact FDI tooth number (11-48, 51-85) or quadrant/arch specified?
2. Diagnostic Specificity: Pulpal/periapical status, caries depth, tooth wear, or edentulous condition?
3. Radiographs: Pre-op, working length, or post-op radiograph attachments documented?
4. Mechanics: Specific surfaces for fillings (M, O, D, B, L/P), crown prep vs delivery, implant torque/bone level?
5. Anesthesia & Isolation: Documented?

OUTPUT FORMAT:
- If ready: Respond with EXACTLY `[READY_TO_AUDIT]`.
- If incomplete:
  ### 📋 Interactive Intake Assessment
  (1-2 sentence evaluation)
  ### ❓ Clinician Clarification Checklist:
  (3-5 concise, actionable questions with quick examples)
"""

SUPPORTED_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash"]

def call_gemini_resilient(client, prompt, system_instruction, temperature):
    last_err = None
    for model_id in SUPPORTED_MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                    )
                )
                return response.text.strip()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "404" in err_str or "not_found" in err_str or "not supported" in err_str:
                    break
                time.sleep(1)
    raise last_err

def evaluate_encounter_completeness(client, doctor_input):
    prompt = f"CLINICIAN ENCOUNTER ENTRY:\n{doctor_input}"
    return call_gemini_resilient(
        client=client,
        prompt=prompt,
        system_instruction=DISCOVERY_EVALUATOR_PROMPT,
        temperature=0.1
    )

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
     * **#1 Technical Denial Trap & Regulatory Citation:** [Cite exact SBSCS standard, Article 11 tariff rule, or Tabular List page number that protects against rejection].
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

def generate_scrubbed_package(client, doctor_input, icd_db, tariff_text, system_instruction):
    icd_reference = "\n".join([f"- {item['code']}: {item['title']} ({item['category']})" for item in icd_db]) if icd_db else "[Built-in ICD-10-AM Active]"
    
    # Real-time FTS5 RAG retrieval from ferrule_knowledge.db
    rag_context = query_fts5_rag_knowledge(doctor_input, max_chunks=4)

    prompt_payload = f"""
OFFICIAL ICD-10-AM DENTAL DIAGNOSTIC GROUND TRUTH:
{icd_reference}

OFFICIAL CCHI ARTICLE 11 STATUTORY GOVERNMENT DENTAL TARIFF SCHEDULE:
{tariff_text}

VERIFIED TEXTBOOK & REGULATORY EXCLUSION EXCERPTS (FTS5 RAG RETRIEVAL):
{rag_context if rag_context else "[Standard SBS v3.0 / NPHIES Ground Truth Active]"}

CLINICIAN ENCOUNTER CASE SUMMARY:
{doctor_input}
"""
    return call_gemini_resilient(
        client=client,
        prompt=prompt_payload,
        system_instruction=system_instruction,
        temperature=0.05
    )

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
                                client, doctor_input, icd_db, tariff_reference, dynamic_sys_instruction
                            )
                        else:
                            st.session_state.discovery_questions = discovery_eval
                            st.session_state.pending_case_input = doctor_input
                    except Exception as e:
                        st.error(f"Guided analysis failed: {str(e)}")
            else:
                st.session_state.discovery_questions = None
                st.session_state.pending_case_input = ""
                with st.spinner("Scrubbing documentation against SBS v3.0, Article 11 Tariffs & NPHIES..."):
                    try:
                        dynamic_sys_instruction = construct_dynamic_instructions(
                            inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                        )
                        st.session_state.final_scrubbed_output = generate_scrubbed_package(
                            client, doctor_input, icd_db, tariff_reference, dynamic_sys_instruction
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
            placeholder="e.g. Tooth #46, vital cold test negative, pre-op PA taken, 3 canals instrumented, Cavit temp placed...",
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
                            client, merged_input, icd_db, tariff_reference, dynamic_sys_instruction
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
