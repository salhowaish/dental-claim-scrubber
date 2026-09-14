import os
import re
import json
import time
import sqlite3
import pandas as pd
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

# ==========================================
# PAGE CONFIGURATION & ENTERPRISE THEME
# ==========================================
st.set_page_config(
    page_title="FERRULE | Dr. Sulaiman Alhowaish",
    page_icon="favicon.svg" if os.path.exists("favicon.svg") else "🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

    .tier-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-right: 0.5rem;
    }
    .badge-reject { background-color: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
    .badge-warning { background-color: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
    .badge-tier { background-color: #e0e7ff; color: #3730a3; }
    .evidence-box {
        background-color: #0f172a;
        color: #e2e8f0;
        border-left: 3px solid #38bdf8;
        padding: 0.8rem 1rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DETERMINISTIC FERRULE ENGINE CORE
# ==========================================
class FerruleEngine:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_dir, "ferrule_knowledge.db")
        self._load_reference_tables()

    def _load_reference_tables(self):
        surf_path = os.path.join(self.base_dir, "appendix_fdi_tooth_surface.json")
        self.valid_surfaces = set()
        if os.path.exists(surf_path):
            with open(surf_path, "r", encoding="utf-8") as f:
                for r in json.load(f):
                    c = r.get("Code", r.get("code", "")).strip().upper()
                    if c: self.valid_surfaces.add(c)
        if not self.valid_surfaces:
            self.valid_surfaces = {"M", "O", "D", "B", "L", "V", "P", "I"}

        denial_path = os.path.join(self.base_dir, "nphies_denial_rules.json")
        self.denials = {}
        if os.path.exists(denial_path):
            with open(denial_path, "r", encoding="utf-8") as f:
                for r in json.load(f):
                    self.denials[r.get("Code", "").strip()] = r.get("Description", "")

    def get_connection(self):
        if not os.path.exists(self.db_path):
            return None
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def normalize_code(self, raw_code):
        conn = self.get_connection()
        if not conn: return None
        clean = re.sub(r'[^0-9]', '', str(raw_code).strip())
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM procedures WHERE replace(sbs_code, '-', '') = ? OR sbs_code = ?", (clean, raw_code))
        row = cur.fetchone()
        if row: 
            conn.close()
            return dict(row)

        if len(clean) == 3:
            cur.execute("SELECT * FROM procedures WHERE ada_item = ? LIMIT 1", (clean,))
            row = cur.fetchone()
            if row:
                conn.close()
                return dict(row)

        if len(clean) >= 5 and clean.startswith("97"):
            prefix = clean[:5]
            cur.execute("SELECT * FROM procedures WHERE sbs_code LIKE ? LIMIT 1", (f"{prefix}%",))
            row = cur.fetchone()
            if row:
                conn.close()
                return dict(row)

        conn.close()
        return None

    def query_rag_evidence(self, search_terms, max_results=2):
        conn = self.get_connection()
        if not conn: return []
        cur = conn.cursor()
        sanitized = search_terms.replace("'", '"')
        try:
            cur.execute("""
                SELECT doc_type, source_file, page_num, snippet(corpus_fts, 3, '[', ']', '...', 12) as snip
                FROM corpus_fts
                WHERE corpus_fts MATCH ?
                ORDER BY rank LIMIT ?
            """, (sanitized, max_results))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows
        except sqlite3.OperationalError:
            tokens = re.findall(r'\w+', search_terms)
            if not tokens:
                conn.close()
                return []
            fallback = " OR ".join(tokens)
            try:
                cur.execute("""
                    SELECT doc_type, source_file, page_num, snippet(corpus_fts, 3, '[', ']', '...', 12) as snip
                    FROM corpus_fts
                    WHERE corpus_fts MATCH ?
                    ORDER BY rank LIMIT ?
                """, (fallback, max_results))
                rows = [dict(r) for r in cur.fetchall()]
                conn.close()
                return rows
            except Exception:
                conn.close()
                return []

    def validate_fdi_tooth(self, tooth_num):
        if not tooth_num: return True, None
        t = str(tooth_num).strip()
        perm_quads = {'1', '2', '3', '4'}
        decid_quads = {'5', '6', '7', '8'}
        if len(t) == 2 and t[0] in perm_quads and t[1] in [str(i) for i in range(1, 9)]:
            return True, "Permanent"
        if len(t) == 2 and t[0] in decid_quads and t[1] in [str(i) for i in range(1, 6)]:
            return True, "Deciduous"
        return False, None

    def validate_surfaces(self, surface_str):
        if not surface_str: return True
        surfaces = [s.strip().upper() for s in re.split(r'[,/ ]+', surface_str) if s.strip()]
        return all(s in self.valid_surfaces for s in surfaces)

    def scrub_claim(self, claim):
        findings = []
        status = "PASSED"

        # Tier 1: Diagnosis & Timing
        dx = claim.get("diagnosis_codes", [])
        if not dx:
            findings.append({
                "tier": 1,
                "severity": "REJECT",
                "code": "NC-001",
                "message": "Mandatory primary diagnosis missing. Provide valid ICD-10-AM diagnosis code.",
                "citations": []
            })
            status = "FAILED"

        days = claim.get("days_since_discharge", 0)
        max_days = 45 if claim.get("sector") == "Government" else 30
        if days > max_days:
            citations = self.query_rag_evidence('naphies AND "30" AND "45"')
            findings.append({
                "tier": 4,
                "severity": "REJECT",
                "code": "TIMELY-FILING-EXCEEDED",
                "message": f"Filing delay ({days} days) exceeds statutory {max_days}-day limit under Article 90 of CHI Regulations.",
                "citations": citations
            })
            status = "FAILED"

        # Tier 2 & 3: Line Items
        lines = claim.get("lines", [])
        resolved_lines = []

        for idx, line in enumerate(lines, 1):
            raw_c = line.get("procedure_code", "").strip()
            proc = self.normalize_code(raw_c)
            tooth = line.get("tooth")
            surfaces = line.get("surfaces")
            amount = float(line.get("claimed_amount", 0.0) or 0.0)

            if not proc:
                findings.append({
                    "tier": 2,
                    "line": idx,
                    "severity": "REJECT",
                    "code": "CODE-NOT-FOUND",
                    "message": f"Procedure '{raw_c}' cannot be mapped to SBS v3.0 Dental or Article 11 schedules.",
                    "citations": []
                })
                status = "FAILED"
                continue

            resolved_lines.append((line, proc))

            if tooth:
                v_tooth, _ = self.validate_fdi_tooth(tooth)
                if not v_tooth:
                    findings.append({
                        "tier": 1,
                        "line": idx,
                        "severity": "REJECT",
                        "code": "DENIAL-E045",
                        "message": f"Invalid FDI tooth '{tooth}'. Must be 11-48 or 51-85.",
                        "citations": []
                    })
                    status = "FAILED"

            if "restoration" in proc["long_desc"].lower():
                if not surfaces or not self.validate_surfaces(surfaces):
                    citations = self.query_rag_evidence('restoration AND tooth AND surface')
                    findings.append({
                        "tier": 1,
                        "line": idx,
                        "severity": "REJECT",
                        "code": "DENIAL-E082",
                        "message": f"Restoration {proc['sbs_code']} requires valid tooth surfaces (M, O, D, B, L/P).",
                        "citations": citations
                    })
                    status = "FAILED"

            if amount > 500 and not claim.get("pre_auth_ref"):
                findings.append({
                    "tier": 3,
                    "line": idx,
                    "severity": "REJECT",
                    "code": "NPHIES-PA-01",
                    "message": f"Line amount {amount:.2f} SAR exceeds 500 SAR limit without Pre-Authorization.",
                    "citations": [{"doc_type": "Compliance", "source_file": "naphies.md", "page_num": "50", "snip": "رﻓﻊ ﻃﻠﺒﺎت اﻟﻤﻮاﻓﻘﺔ اﻟﻤﺴﺒﻘﺔ ﻟﻠﺨﺪﻣﺎت اﻟﺘﻲ ﺗﻘﻞ ﻗﻴﻤﺘﻬﺎ ﻋﻦ 500 رﻳﺎل"}]
                })
                status = "FAILED"

            if any(k in proc["long_desc"].lower() for k in ["root canal", "implant", "fixture"]):
                if not claim.get("has_radiograph"):
                    citations = self.query_rag_evidence('radiograph OR periapical OR OPG')
                    findings.append({
                        "tier": 3,
                        "line": idx,
                        "severity": "REJECT",
                        "code": "DENIAL-E104",
                        "message": f"Procedure {proc['sbs_code']} requires verified radiographic attachment.",
                        "citations": citations
                    })
                    status = "FAILED"

        # Tier 3: Bundling & Exclusions
        all_sbs = [p["sbs_code"] for _, p in resolved_lines]
        for line, proc in resolved_lines:
            sbs = proc["sbs_code"]
            if "97238" in sbs:
                for other in all_sbs:
                    if "97232" in other or "97231" in other:
                        citations = self.query_rag_evidence('97238 OR "crown lengthening"')
                        findings.append({
                            "tier": 3,
                            "severity": "REJECT",
                            "code": "SBSCS-UNBUNDLE-01",
                            "message": f"Unbundling Detected: Crown lengthening ({sbs}) billed with routine periodontal flap ({other}).",
                            "citations": citations
                        })
                        status = "FAILED"

        return {
            "status": status,
            "claim_id": claim.get("claim_id"),
            "findings_count": len(findings),
            "findings": findings,
            "resolved_lines": resolved_lines
        }

engine = FerruleEngine()

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

    icd_list = []
    json_filename = "cchi_dental_icd10.json"
    if os.path.exists(json_filename):
        try:
            with open(json_filename, "r", encoding="utf-8") as f:
                icd_list = json.load(f)
        except Exception:
            icd_list = []

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

# Tabs separating Clinical Note Assistant from Direct Line-Item Scrubber
tab_clinical, tab_scrubber = st.tabs([
    "📝 Clinical Note & Intelligent Audit", 
    "🛡️ Deterministic Line-Item Scrubber"
])

# ==========================================
# TAB 1: CLINICAL NOTE & INTELLIGENT AUDIT (ORIGINAL PIPELINE)
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

1. CCHI / NPHIES PRIOR-AUTHORIZATION (PA) RULES & THE 500 SAR THRESHOLD:
- MANDATORY 500 SAR EXEMPTION: Any outpatient dental service where the one-time treatment is LESS THAN 500 SAR is STRICTLY EXEMPT from Prior Authorization.
- Requesting PA for services < 500 SAR is an official violation. Mark as [PA EXEMPT: Clean Direct Claim (Service < 500 SAR Threshold)].
- PA MANDATORY: Services >= 500 SAR (Indirect crowns [470], bridges [471], dentures [474], implants [400], completed RCT [462], surgical extractions [458], periodontal surgery [456]). Statutory 60-min SLA enforced.
- Emergency & acute pain (Triage 1-3, emergency pulp extirpation 97419-00-10) are PA-exempt under 24-hr notification rule.

2. OFFICIAL SBSCS BUNDLING STANDARDS:
- Anatomical site: FDI two-digit numbering (Permanent 11-48, Primary 51-85).
- Contiguous restorative surfaces on same tooth (e.g. MO) billed as ONE multi-surface code, NEVER two 1-surface codes.
- Crown lengthening (97238-00-00) excludes routine periodontal flap (97232-xx).
- Completed RCT billed as ONE code per tooth based on type (Anterior 97420-01-00, Premolar 97420-02-00, Molar 97420-03-00). NEVER bill emergency extirpation (97419-00-10) concurrently with completed RCT.
- Removable denture in-progress steps are non-billable (0.00 SAR). Global tariff released on insertion (8,000 SAR).
- Orthodontic comprehensive exam (97011-00-20) inherently bundles photographs, OPG, ceph, tracing, and study models. Separate billing prohibited.

3. ARTICLE 11 STATUTORY GOVERNMENT TARIFF PRICING:
Output exact statutory tariffs from Article 11 schedule.

4. CASE CONTINUITY METADATA BLOCK:
Enclose strictly between <NPHIES_BLOCK> and </NPHIES_BLOCK> tags at the very end.
"""

DISCOVERY_EVALUATOR_PROMPT = """
You are an expert Dental Clinical Documentation Specialist and Revenue Cycle Auditor in Saudi Arabia.
Analyze the clinician's notes and determine if critical data points required by CCHI, NPHIES, and SBSCS v3.0 are missing or ambiguous.
Output EXACTLY `[READY_TO_AUDIT]` if complete, or provide a concise Intake Assessment and Clarification Checklist if incomplete.
"""

def evaluate_encounter_completeness(client, doctor_input):
    prompt = f"CLINICIAN ENCOUNTER ENTRY:\n{doctor_input}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
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
        instructions.append(f"\nACTIVE WORKFLOW PRE-SET: Clinician selected pathway: {staged_pathway}.\n")
    instructions.append("\nREQUIRED OUTPUT SECTIONS:\n")
    sec_num = 1
    if inc_icd:
        instructions.append(f"{sec_num}. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM)\n")
        sec_num += 1
    if inc_billing:
        instructions.append(f"{sec_num}. BILLABLE CODING TABLE (SBS v3.0 & ACHI 10th Ed)\n")
        sec_num += 1
    if inc_checklist:
        instructions.append(f"{sec_num}. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES)\n")
        sec_num += 1
    if note_style == "Concise SmartForm Macro (Hospital Standard)":
        instructions.append(f"{sec_num}. AUDIT-PROOF EMR CLINICAL NOTE (CONCISE SMARTFORM MACRO)\n")
    elif note_style == "Detailed SOAP Clinical Note (Hospital / Academic)":
        instructions.append(f"{sec_num}. AUDIT-PROOF EMR SOAP CLINICAL PROGRESS NOTE (NARRATIVE)\n")
    return "".join(instructions)

def generate_scrubbed_package(client, doctor_input, cchi_text, icd_db, tariff_text, system_instruction):
    icd_reference = "\n".join([f"- {item['code']}: {item['title']} ({item['category']})" for item in icd_db]) if icd_db else "[Built-in ICD-10-AM Active]"
    prompt_payload = f"""
OFFICIAL CCHI SBS VERSION 3 DENTAL ALPHABETIC INDEX:
{cchi_text if cchi_text else "[Built-in ACHI/SBS Knowledge Active]"}

OFFICIAL ICD-10-AM DENTAL DIAGNOSTIC CONCEPT TABLE:
{icd_reference}

OFFICIAL CCHI ARTICLE 11 STATUTORY GOVERNMENT DENTAL TARIFF SCHEDULE:
{tariff_text}

CLINICIAN ENCOUNTER CASE SUMMARY:
{doctor_input}
"""
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
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

with tab_clinical:
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
            help="Pauses to ask clarifying questions if key details (tooth #, vital signs, radiograph types) are missing."
        )
        
        st.markdown('<div class="sub-section-title">Audit Package Configuration</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: inc_icd = st.checkbox("ICD-10-AM Diagnosis", value=True)
        with c2: inc_billing = st.checkbox("SBS v3.0 / ACHI Table", value=True)
        with c3: inc_checklist = st.checkbox("NPHIES Checklist", value=True)
            
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
        is_staged = st.checkbox("Enable Multi-Visit Episode Continuity Guard", value=True)
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
                                dynamic_sys = construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway)
                                st.session_state.final_scrubbed_output = generate_scrubbed_package(client, doctor_input, cchi_index_text, cchi_icd_db, cchi_tariff_reference, dynamic_sys)
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
                            dynamic_sys = construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway)
                            st.session_state.final_scrubbed_output = generate_scrubbed_package(client, doctor_input, cchi_index_text, cchi_icd_db, cchi_tariff_reference, dynamic_sys)
                        except Exception as e:
                            st.error(f"Audit execution failed: {str(e)}")

        if st.session_state.discovery_questions:
            st.markdown('<div class="interactive-card">', unsafe_allow_html=True)
            st.markdown(st.session_state.discovery_questions)
            st.markdown("</div>", unsafe_allow_html=True)
            
            clarification_input = st.text_area("Quick Clinician Clarifications:", height=100)
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1: finalize_guided = st.button("Finalize Claim Package", type="primary", use_container_width=True)
            with btn_c2: cancel_guided = st.button("Reset Assessment", use_container_width=True)
                
            if cancel_guided:
                st.session_state.discovery_questions = None
                st.session_state.pending_case_input = ""
                st.session_state.final_scrubbed_output = None
                st.rerun()
                
            if finalize_guided and api_key:
                with st.spinner("Synthesizing input & generating regulatory audit..."):
                    client = genai.Client(api_key=api_key)
                    merged = f"{st.session_state.pending_case_input}\n\nCLARIFICATIONS:\n{clarification_input}"
                    dynamic_sys = construct_dynamic_instructions(inc_icd, inc_billing, inc_checklist, note_style, is_staged, staged_pathway)
                    st.session_state.final_scrubbed_output = generate_scrubbed_package(client, merged, cchi_index_text, cchi_icd_db, cchi_tariff_reference, dynamic_sys)
                    st.session_state.discovery_questions = None
                    st.session_state.pending_case_input = ""

        if st.session_state.final_scrubbed_output:
            raw_result = st.session_state.final_scrubbed_output
            nphies_match = re.search(r"<NPHIES_BLOCK>(.*?)</NPHIES_BLOCK>", raw_result, re.DOTALL)
            if nphies_match:
                block_content = nphies_match.group(1).strip()
                clean_markdown = re.sub(r"<NPHIES_BLOCK>.*?</NPHIES_BLOCK>", "", raw_result, flags=re.DOTALL).strip()
            else:
                block_content = None
                clean_markdown = raw_result.strip()
            
            st.markdown(clean_markdown)
            if block_content:
                st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
                st.caption("NPHIES Episode Continuity Token (Persist across multi-visit encounters):")
                st.code(block_content, language="text")

# ==========================================
# TAB 2: DETERMINISTIC LINE-ITEM SCRUBBER
# ==========================================
with tab_scrubber:
    st.markdown("### 4-Tier Deterministic Claim Scrubber")
    st.caption("Directly validates procedure line items against SBS v3.0, Article 11 tariffs, FDI specs, and FTS5 RAG evidence citations.")

    scrub_col1, scrub_col2 = st.columns([1, 2])
    with scrub_col1:
        s_sector = st.selectbox("Sector", ["Government", "Private"], key="scrub_sector")
        s_days = st.number_input("Days Since Discharge", min_value=0, max_value=120, value=14, key="scrub_days")
        s_preauth = st.text_input("Pre-Authorization Ref (NPHIES)", value="", key="scrub_pa")
        s_radio = st.checkbox("Radiographic Attachment Verified", value=False, key="scrub_xray")
    with scrub_col2:
        s_claim_id = st.text_input("Claim Identifier", value="CLM-2026-9041", key="scrub_cid")
        s_dx = st.text_input("Primary ICD-10-AM Diagnosis Code", value="K05.30", key="scrub_dx")
        s_preset = st.selectbox(
            "Load Validation Test Case",
            ["Custom Lines", "Unbundling: Crown Lengthening + Flap", "Invalid Restorative Surface", "Over 500 SAR Missing PA"]
        )

    preset_lines = [
        {"procedure_code": "238", "tooth": "14", "surfaces": "", "claimed_amount": 950.0},
        {"procedure_code": "97232-00-10", "tooth": "14", "surfaces": "", "claimed_amount": 400.0}
    ]
    if s_preset == "Unbundling: Crown Lengthening + Flap":
        preset_lines = [
            {"procedure_code": "238", "tooth": "14", "surfaces": "", "claimed_amount": 950.0},
            {"procedure_code": "97232-00-10", "tooth": "14", "surfaces": "", "claimed_amount": 400.0}
        ]
    elif s_preset == "Invalid Restorative Surface":
        preset_lines = [
            {"procedure_code": "97521", "tooth": "16", "surfaces": "XYZ", "claimed_amount": 350.0}
        ]
    elif s_preset == "Over 500 SAR Missing PA":
        preset_lines = [
            {"procedure_code": "97420-03-00", "tooth": "46", "surfaces": "", "claimed_amount": 1500.0}
        ]

    st.markdown("#### Procedure Lines")
    scrubber_table = st.data_editor(
        pd.DataFrame(preset_lines),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "procedure_code": st.column_config.TextColumn("Procedure / ADA / SBS", required=True),
            "tooth": st.column_config.TextColumn("FDI Tooth (e.g. 14, 46)"),
            "surfaces": st.column_config.TextColumn("Surfaces (e.g. MO, MOD)"),
            "claimed_amount": st.column_config.NumberColumn("Amount (SAR)", min_value=0.0, format="%.2f SAR")
        },
        key="scrubber_editor"
    )

    if st.button("Execute Deterministic Audit & FTS5 Retrieval", type="primary"):
        payload = {
            "claim_id": s_claim_id,
            "sector": s_sector,
            "days_since_discharge": s_days,
            "pre_auth_ref": s_preauth.strip() if s_preauth.strip() else None,
            "has_radiograph": s_radio,
            "diagnosis_codes": [s_dx.strip()] if s_dx.strip() else [],
            "lines": scrubber_table.to_dict(orient="records")
        }

        audit_res = engine.scrub_claim(payload)

        st.markdown("---")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            if audit_res["status"] == "PASSED":
                st.success("### STATUS: CLEAN CLAIM")
            else:
                st.error("### STATUS: REJECT RISK")
        with rc2:
            st.metric("Total Lines Analyzed", len(audit_res["resolved_lines"]))
        with rc3:
            st.metric("Audit Flags Raised", audit_res["findings_count"])

        st.markdown("#### Normalized Procedures & Tariffs")
        if audit_res["resolved_lines"]:
            n_rows = []
            for orig, mapped in audit_res["resolved_lines"]:
                n_rows.append({
                    "Input": orig.get("procedure_code"),
                    "Mapped SBS Code": mapped["sbs_code"],
                    "Block": mapped["block"],
                    "Description": mapped["long_desc"],
                    "Setting": mapped["setting"]
                })
            st.dataframe(pd.DataFrame(n_rows), use_container_width=True)

        st.markdown("#### Regulatory Findings & Exact Evidence Citations")
        if not audit_res["findings"]:
            st.success("No compliance or bundling infractions detected. Claim satisfies NPHIES specifications.")
        else:
            for f in audit_res["findings"]:
                b_class = "badge-reject" if f["severity"] == "REJECT" else "badge-warning"
                st.markdown(f"""
                <div>
                    <span class="tier-badge badge-tier">Tier {f['tier']}</span>
                    <span class="tier-badge {b_class}">{f['severity']}</span>
                    <strong>[{f['code']}]</strong> {f['message']}
                </div>
                """, unsafe_allow_html=True)

                if f.get("citations"):
                    for c in f["citations"]:
                        st.markdown(f"""
                        <div class="evidence-box">
                            📖 <strong>Regulatory / Clinical Evidence:</strong> [{c['source_file']} | Page {c['page_num']}]<br>
                            {c['snip']}
                        </div>
                        """, unsafe_allow_html=True)
                st.write("")
