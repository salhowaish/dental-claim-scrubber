import os
import re
import json
import time
import base64
import sqlite3
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# ==========================================
# ASSET ENCODING & PAGE CONFIGURATION
# ==========================================
def get_base64_asset(preferred_names):
    for name in preferred_names:
        if os.path.exists(name):
            try:
                with open(name, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                ext = name.split(".")[-1].lower()
                mime = "image/jpeg" if ext in ["jpg", "jpeg"] else ("image/svg+xml" if ext == "svg" else "image/png")
                return f"data:{mime};base64,{encoded}", name
            except Exception:
                pass
    return None, None

logo_b64, logo_filename = get_base64_asset(["logo.png", "IMG_1007.jpg", "IMG_1007.png", "image.png", "favicon.svg"])

st.set_page_config(
    page_title="FERRULE | Dr. Sulaiman Alhowaish",
    page_icon=logo_filename if logo_filename else "🦷",
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
        align-items: center;
        flex-wrap: wrap;
        gap: 0.85rem;
    }
    .brand-logo-img {
        height: 48px;
        width: 48px;
        border-radius: 8px;
        object-fit: contain;
        box-shadow: 0 2px 10px rgba(56, 189, 248, 0.25);
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
        font-size: 0.90rem;
        font-weight: 500;
        color: #94A3B8 !important;
        line-height: 1.45;
        margin-top: 0.45rem;
    }
    .brand-version {
        font-size: 0.75rem;
        font-weight: 400;
        color: #64748B !important;
        line-height: 1.4;
        margin-top: 0.2rem;
        letter-spacing: 0.01em;
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
    
    .stTextArea textarea, .stTextInput input {
        background-color: #161F30 !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 8px !important;
        font-size: 0.88rem !important;
        line-height: 1.5 !important;
    }
    .stTextArea textarea::placeholder, .stTextInput input::placeholder {
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
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }

    .verification-card {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-top: 1rem;
        margin-bottom: 1.2rem;
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
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "discovery_data" not in st.session_state:
    st.session_state.discovery_data = None
if "pending_case_input" not in st.session_state:
    st.session_state.pending_case_input = ""
if "final_scrubbed_output" not in st.session_state:
    st.session_state.final_scrubbed_output = None

# ==========================================
# BACKEND: REGULATORY ASSET INGESTION & FTS5 RAG
# ==========================================
@st.cache_data(show_spinner=False)
def load_all_regulatory_assets():
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

    icd_list = []
    if os.path.exists("cchi_dental_icd10.json"):
        try:
            with open("cchi_dental_icd10.json", "r", encoding="utf-8") as f:
                icd_list = json.load(f)
        except Exception:
            icd_list = []

    denials = []
    if os.path.exists("nphies_denial_rules.json"):
        try:
            with open("nphies_denial_rules.json", "r", encoding="utf-8") as f:
                drules = json.load(f)
                denials = [f"- Code {r.get('Code')}: {r.get('Description')}" for r in drules if r.get("Code")]
        except Exception:
            denials = []

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
# MAIN INTERFACE HEADER (UPDATED SEPTEMBER 2026)
# ==========================================
logo_element = f'<img src="{logo_b64}" class="brand-logo-img">' if logo_b64 else ""
st.markdown(f"""
<div class="brand-header">
    <div class="brand-top-row">
        <div class="brand-title-group">
            {logo_element}
            <div>
                <h1 class="brand-title" style="display:inline-block;">FERRULE</h1>
                <span class="brand-author" style="margin-left:0.5rem;">by Dr. Sulaiman Alhowaish</span>
            </div>
        </div>
    </div>
    <div class="brand-subtitle">
        NPHIES compliant clinical documentation system and revenue assurance engine
    </div>
    <div class="brand-version">
        Updated September 2026
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

1. DUAL TAXONOMY & ENCOUNTER ROUTING MANDATE (NPHIES COMPLIANCE)
- OUTPATIENT DENTAL CARE: Billed using the Australian Schedule of Dental Services and Glossary (ADA item numbers mapped to SBS v3.0 `97xxx-xx-xx` format).
- INPATIENT / OPERATING ROOM / MAXILLOFACIAL CARE: Billed using ICD-10-AM Diagnosis + 7-digit ACHI 10th Edition procedure codes.
- TOOTH NOTATION: Strictly mandatory FDI two-digit numbering (Permanent 11-48, Deciduous 51-85).
- TOOTH SURFACES: Strictly validate against NPHIES Codeable Concepts: {fdi_surface_reference}. Multi-surface restorations MUST be billed as ONE multi-surface code, never separated.

2. CCHI / NPHIES PRIOR-AUTHORIZATION (PA) RULES & THE 500 SAR THRESHOLD
- MANDATORY 500 SAR EXEMPTION: Any outpatient dental service where the one-time treatment is LESS THAN 500 SAR is STRICTLY EXEMPT from Prior Authorization. Requesting PA for services < 500 SAR is an official Level 1 Violation. Mark as [PA EXEMPT: Clean Direct Claim (Service < 500 SAR Threshold)].
- PA MANDATORY (Services >= 500 SAR & Major Interventions): Crowns [470], bridges [471], dentures [474], implants [400], completed RCT [462], surgical extractions [458], periodontal surgery [456]. Statutory 60-min SLA enforced.
- TIMELY FILING DEADLINES: Private: 30 days. Government/Clusters: 45 days. Re-submissions: 15 days.

3. OFFICIAL SBSCS DENTAL CODING & BUNDLING STANDARDS
- Crown Lengthening (97238-00-00 [456]): Strictly EXCLUDES routine periodontal flap surgery (97232-xx) (Tabular List Page 167).
- Endodontics (SBSCS 4042): Completed RCT billed as ONE code per tooth based on type (Molar 97420-03-00, Premolar 97420-02-00, Anterior 97420-01-00). Inherently bundles extirpation, shaping, obturation. NEVER bill emergency pulpectomy (97419-00-10) concurrently on same day. Requires pre-op radiograph.
- Prosthodontics (SBSCS 4060): Denture fabrication stages are non-billable (0.00 SAR). Full insertion (97719-01-70) unlocks global fee (SAR 8,000). Post & core includes core build-up.
- Orthodontics (SBSCS 4080): Comprehensive exam (97011-00-20, SAR 500) inherently bundles photos, OPG, ceph, tracings, and study models. Separate billing prohibited.
- Periodontal Surgery (SBSCS 4021): Flap entry/closure coded separately from tissue regeneration. Probing depth >= 4mm and BOP required.

4. NPHIES CLEARINGHOUSE DENIAL PROTECTION RULES
Proactively guard the claim against these active NPHIES denial triggers:
{nphies_denial_context}
"""

DISCOVERY_EVALUATOR_PROMPT = """
You are an expert Dental Clinical Documentation Specialist and Revenue Cycle Auditor in Saudi Arabia.
Analyze the clinician's case note and determine whether critical data points required by CCHI, NPHIES, and SBSCS v3.0 are missing or ambiguous.

RESPOND STRICTLY IN JSON FORMAT ONLY:
{
  "status": "READY_TO_AUDIT" or "NEED_CLARIFICATION",
  "assessment": "Concise 1-sentence evaluation of what is missing or ambiguous.",
  "clarifications": [
    {
      "label": "Name of Parameter (e.g. FDI Tooth, Diagnostic Etiology, Surfaces, Radiographs, Staging)",
      "options": ["Specific option 1", "Specific option 2", "Specific option 3", "Other / Stated in Note"]
    }
  ]
}
Generate 3 to 5 realistic, clinically accurate dropdown parameters with options tailored directly to the patient's case. Return JSON ONLY.
"""

SUPPORTED_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash"]

def call_gemini_resilient(client, prompt, system_instruction, temperature, force_json=False):
    last_err = None
    for model_id in SUPPORTED_MODELS:
        for attempt in range(2):
            try:
                config_args = {
                    "system_instruction": system_instruction,
                    "temperature": temperature,
                }
                if force_json:
                    config_args["response_mime_type"] = "application/json"
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
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
    raw = call_gemini_resilient(
        client=client,
        prompt=prompt,
        system_instruction=DISCOVERY_EVALUATOR_PROMPT,
        temperature=0.1,
        force_json=True
    )
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except Exception: pass
        return {"status": "READY_TO_AUDIT"}

def construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway):
    instructions = [BASE_PRINCIPLES]
    
    if is_staged:
        if staged_pathway != "Auto-detect from case input":
            instructions.append(f"\nACTIVE WORKFLOW PRE-SET: Clinician selected pathway: {staged_pathway}. Align stage numbering and tariff locks strictly with this clinical pathway.\n")
        
        instructions.append("""
================================================================================
NPHIES CASE CONTINUITY METADATA BLOCK MANDATE
================================================================================
Because this is an active multi-visit staged episode, enclose strictly between <NPHIES_BLOCK> and </NPHIES_BLOCK> tags at the very end:
<NPHIES_BLOCK>
[EPISODE_ID]: [Specialty]-[Procedure]-[FDI Tooth/Arch]
[PRIMARY_ICD10]: [Code] — [Accurate Description]
[PRIMARY_SBS_CODE]: [SBS 9-digit Code] [Block]
[CURRENT_STAGE]: Visit [X] of [Total Visits] — [Description of Today's Step]
[BILLING_STATUS]: [IN_PROGRESS - CLAIM LOCKED (0.00 SAR) / BILLABLE ENCOUNTER (Tariff SAR) / GLOBAL CLAIM DELIVERED (Tariff SAR)]
[NEXT_VISIT_EXPECTED]: Visit [X+1] — [Description of Next Step]
[ANTI-UNBUNDLING_LOCK]: [LOCKED / EPISODE_ACTIVE / EPISODE_CLOSED]
</NPHIES_BLOCK>
""")
    else:
        instructions.append("\nSINGLE-VISIT ENCOUNTER: Do NOT output any <NPHIES_BLOCK> or Case Continuity Tokens.\n")

    instructions.append("\nREQUIRED OUTPUT SECTIONS (Generate ONLY the sections explicitly requested below):\n")
    sec_num = 1
    
    if inc_icd:
        instructions.append(f"""
{sec_num}. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM)
   - Specific, valid ICD-10-AM code from the ground truth table. State `COF = 2 (Present on admission)` or `COF = 1`.
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
   - ULTRA-CONCISE & TELEGRAPHIC (Strictly 1 single line per item with markdown checkbox `* [x]`):
     * [x] **Anatomical Site:** [FDI 2-digit tooth number & surfaces verified]
     * [x] **Condition Onset:** [COF = 2 (Present upon presentation) confirmed]
     * [x] **Prior-Auth Status:** [PA-Exempt (< 500 SAR threshold) OR Mandatory PA Reference verified]
     * [x] **Diagnostic Attachments:** [Pre-op PA / Working Length PA / Post-op PA / OPG / CBCT / Periodontal Chart archived]
     * [x] **Anti-Denial Protection:** [Primary technical trap avoided with exact standard citation]
""")
        sec_num += 1

    if note_style == "Concise SmartForm Macro (Hospital Standard)":
        instructions.append(f"""
<CLINICAL_NOTE_START>
{sec_num}. AUDIT-PROOF EMR CLINICAL NOTE (CONCISE SMARTFORM MACRO)
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
<CLINICAL_NOTE_END>
""")
    elif note_style == "Detailed SOAP Clinical Note (Hospital / Academic)":
        instructions.append(f"""
<CLINICAL_NOTE_START>
{sec_num}. AUDIT-PROOF EMR SOAP CLINICAL PROGRESS NOTE (NARRATIVE)
Comprehensive narrative medical record: Subjective, Objective, Assessment, Plan & Procedure, Post-Operative Instructions.
<CLINICAL_NOTE_END>
""")

    return "".join(instructions)

def generate_scrubbed_package(client, doctor_input, icd_db, tariff_text, system_instruction):
    icd_reference = "\n".join([f"- {item['code']}: {item['title']} ({item['category']})" for item in icd_db]) if icd_db else "[Built-in ICD-10-AM Active]"
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
        help="Evaluates documentation against NPHIES rules and provides convenient dropdown selection lists."
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
        value=False, 
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
                        discovery_result = evaluate_encounter_completeness(client, doctor_input)
                        if discovery_result.get("status") == "READY_TO_AUDIT":
                            st.session_state.discovery_data = None
                            st.session_state.pending_case_input = ""
                            dynamic_sys_instruction = construct_dynamic_instructions(
                                inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                            )
                            st.session_state.final_scrubbed_output = generate_scrubbed_package(
                                client, doctor_input, icd_db, tariff_reference, dynamic_sys_instruction
                            )
                        else:
                            st.session_state.discovery_data = discovery_result
                            st.session_state.pending_case_input = doctor_input
                    except Exception as e:
                        st.error(f"Guided analysis failed: {str(e)}")
            else:
                st.session_state.discovery_data = None
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

    # ==========================================
    # GUIDED DISCOVERY: DROPDOWN & DYNAMIC OTHER WORKFLOW
    # ==========================================
    if st.session_state.discovery_data:
        d_data = st.session_state.discovery_data
        st.markdown('<div class="interactive-card">', unsafe_allow_html=True)
        st.markdown("### 📋 Interactive Intake Assessment")
        st.write(d_data.get("assessment", "Encounter requires specific clinical parameters to satisfy NPHIES clearinghouse rules."))
        st.markdown("### ❓ Clinician Clarification Checklist")
        st.caption("Select the appropriate clinical parameters below from each dropdown list:")
        
        clarifications = d_data.get("clarifications", [])
        chosen_values = {}
        for idx, item in enumerate(clarifications):
            lbl = item.get("label", f"Parameter {idx+1}")
            opts = item.get("options", ["Confirmed / Applicable", "Not Applicable"])
            selected_val = st.selectbox(lbl, opts, key=f"guide_sel_{idx}")
            
            # Immediately show a text box if "Other" or "Stated in Note" is chosen
            if "other" in str(selected_val).lower():
                custom_spec = st.text_input(
                    f"Specify details for {lbl}:",
                    placeholder="Enter custom clinical detail, tooth #, finding, or surface...",
                    key=f"guide_other_{idx}"
                )
                if custom_spec.strip():
                    chosen_values[lbl] = f"Other ({custom_spec.strip()})"
                else:
                    chosen_values[lbl] = selected_val
            else:
                chosen_values[lbl] = selected_val
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            finalize_guided = st.button("Finalize & Generate Audit-Proof Claim", type="primary", use_container_width=True)
        with btn_c2:
            cancel_guided = st.button("Reset / Clear Assessment", use_container_width=True)
            
        if cancel_guided:
            st.session_state.discovery_data = None
            st.session_state.pending_case_input = ""
            st.session_state.final_scrubbed_output = None
            st.rerun()
            
        if finalize_guided and api_key:
            with st.spinner("Synthesizing selected criteria & generating regulatory audit..."):
                try:
                    client = genai.Client(api_key=api_key)
                    clarification_summary = "\n".join([f"- {k}: {v}" for k, v in chosen_values.items()])
                    merged_input = f"{st.session_state.pending_case_input}\n\nCLINICIAN PARAMETERS SPECIFIED:\n{clarification_summary}"
                    
                    dynamic_sys_instruction = construct_dynamic_instructions(
                        inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway
                    )
                    st.session_state.final_scrubbed_output = generate_scrubbed_package(
                        client, merged_input, icd_db, tariff_reference, dynamic_sys_instruction
                    )
                    st.session_state.discovery_data = None
                    st.session_state.pending_case_input = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"Finalization failed: {str(e)}")

    # ==========================================
    # RENDER FINAL AUDIT RESULTS & NOTE SYNC
    # ==========================================
    if st.session_state.final_scrubbed_output:
        raw_result = st.session_state.final_scrubbed_output
        
        nphies_match = re.search(r"<NPHIES_BLOCK>(.*?)</NPHIES_BLOCK>", raw_result, re.DOTALL)
        if nphies_match:
            block_content = nphies_match.group(1).strip()
            clean_result = re.sub(r"<NPHIES_BLOCK>.*?</NPHIES_BLOCK>", "", raw_result, flags=re.DOTALL).strip()
        else:
            fallback_match = re.search(r"(\[EPISODE_ID\].*?\[ANTI-UNBUNDLING_LOCK\].*?$)", raw_result, re.DOTALL)
            if fallback_match:
                block_content = fallback_match.group(1).strip()
                clean_result = raw_result[:fallback_match.start()].strip()
                clean_result = re.sub(r"(?:🔄\s*)?(?:NPHIES Case Continuity Token.*?$|NPHIES CASE CONTINUITY BLOCK.*?$)", "", clean_result, flags=re.MULTILINE).strip()
            else:
                block_content = None
                clean_result = raw_result.strip()
            
        note_match = re.search(r"<CLINICAL_NOTE_START>(.*?)<CLINICAL_NOTE_END>", clean_result, re.DOTALL)
        if note_match:
            regulatory_sections = clean_result[:note_match.start()].strip()
            base_clinical_note = note_match.group(1).strip()
        else:
            regulatory_sections = clean_result
            base_clinical_note = ""

        st.markdown(regulatory_sections)
        
        st.markdown('<div class="verification-card">', unsafe_allow_html=True)
        st.markdown("#### ✅ Clinician Pre-Flight Verification Sign-Off")
        st.caption("Active checkmarks automatically stamp into the clinical note below:")
        
        pv1, pv2, pv3, pv4 = st.columns(4)
        with pv1:
            chk_fdi = st.checkbox("FDI Site Confirmed", value=True, key="pv_fdi")
            chk_rad = st.checkbox("Radiographs Archived", value=True, key="pv_rad")
        with pv2:
            chk_dam = st.checkbox("Rubber Dam Documented", value=True, key="pv_dam")
            chk_pa = st.checkbox("PA Status Cleared", value=True, key="pv_pa")
        with pv3:
            chk_cof = st.checkbox("COF = 2 Flag Confirmed", value=True, key="pv_cof")
            chk_surf = st.checkbox("Surfaces Validated", value=True, key="pv_surf")
        with pv4:
            chk_consent = st.checkbox("Informed Consent On File", value=True, key="pv_consent")
            chk_anti = st.checkbox("Anti-Unbundling Active", value=True, key="pv_anti")
        st.markdown('</div>', unsafe_allow_html=True)

        if base_clinical_note:
            stamped_items = []
            if chk_fdi: stamped_items.append("FDI Site Confirmed")
            if chk_rad: stamped_items.append("Diagnostic Radiographs Archived")
            if chk_dam: stamped_items.append("Rubber Dam Isolation Documented")
            if chk_pa: stamped_items.append("Prior-Authorization Status Cleared")
            if chk_cof: stamped_items.append("COF=2 Pre-existing Condition Flag")
            if chk_surf: stamped_items.append("FDI Tooth Surfaces Verified")
            if chk_consent: stamped_items.append("Informed Consent Documented")
            if chk_anti: stamped_items.append("Anti-Unbundling Multi-Stage Locked")

            audit_stamp = "\n".join([f"  [✓] {item}" for item in stamped_items]) if stamped_items else "  [!] No verification flags confirmed by clinician."
            
            complete_clinical_note = f"{base_clinical_note}\n\n**CLINICAL COMPLIANCE & VERIFICATION AUDIT:**\n{audit_stamp}"
            st.markdown(complete_clinical_note)

        if is_staged and block_content:
            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
            st.caption("NPHIES Episode Continuity Token (Persist across multi-visit encounters):")
            st.code(block_content, language="text")
