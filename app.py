import streamlit as st
import json
import os
import re
import pandas as pd

# Initialize Streamlit Page Configuration
st.set_page_config(
    page_title="FERRULE AI — Clinical Coding & Compliance Engine",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Clean Professional Interface
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.0rem; color: #4B5563; margin-bottom: 1.5rem; }
    .badge-pass { background-color: #D1FAE5; color: #065F46; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    .badge-warn { background-color: #FEF3C7; color: #92400E; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    .badge-lock { background-color: #E0E7FF; color: #3730A3; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding-top: 8px; padding-bottom: 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# HARDCODED GEMINI MODEL IDENTIFIER
HARDCODED_GEMINI_MODEL = "gemini-3.8-flash"

# ------------------------------------------------------------------------------
# 1. API & ASSET FALLBACK RESILIENCE LAYER
# ------------------------------------------------------------------------------

def get_gemini_api_key():
    """Retrieve Gemini API Key from Streamlit Secrets or Sidebar Input."""
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        return st.secrets["GEMINI_API_KEY"]
    return st.sidebar.text_input("Gemini API Key", type="password", help="Enter API Key if not configured in secrets.toml")

@st.cache_data
def load_codebook_dataframe():
    """Safely load dental SBS to ACHI codebook map CSV with multiple path fallbacks."""
    candidate_paths = [
        "dental_sbs_achi_map.csv",
        "knowledge/dental_sbs_achi_map.csv",
        "/workspace/knowledge/dental_sbs_achi_map.csv"
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                return df
            except Exception:
                pass
    return None

# Embedded Regulatory Fallback Rules (Guarantees zero app crashes)
DEFAULT_DENIAL_RULES = {
    "N-DC-044": "Service not clinically indicated based on clinical documentation.",
    "N-DC-045": "Service not clinically indicated without supporting diagnostic evidence (X-rays/Charts).",
    "N-DC-084": "Unbundling violation — intermediate stage submitted with global procedure.",
    "N-DC-043": "Consultation billed within mandatory free follow-up window (14-30 days).",
    "BE-1-4": "Prior approval required and not obtained prior to service delivery."
}

# ------------------------------------------------------------------------------
# 2. DETERMINISTIC ANATOMICAL & PRE-FLIGHT GUARD LAYER
# ------------------------------------------------------------------------------

def validate_anatomical_site(procedure_category, tooth_num, arch_quad):
    """
    Hard-validates anatomical site selection against FDI (ISO 3950) standards.
    Prevents Site-Incompatibility Error 1676.
    """
    quad_arch_required_categories = ["Periodontics (Per Quadrant)", "Prosthodontics (Per Arch/Jaw)", "Orthodontics", "Fluoride / Full Mouth"]
    
    if procedure_category in quad_arch_required_categories:
        if not arch_quad or arch_quad == "Not Selected":
            return False, "⚠️ **Anatomical Error**: This procedure category mandates an **Arch or Quadrant** selection (e.g., Q1-Q4, Maxilla, or Mandible). Individual tooth numbers are insufficient."
        return True, f"✅ **Arch/Quadrant Validated**: Assigned to {arch_quad}"
    else:
        if not tooth_num or tooth_num == "None / Not Applicable":
            return False, "⚠️ **Anatomical Error**: This procedure mandates a 2-digit **FDI Tooth Number** (11–48 for permanent, 51–85 for primary)."
        return True, f"✅ **FDI Tooth Validated**: FDI #{tooth_num}"

# ------------------------------------------------------------------------------
# 3. MULTI-STAGE COMPLIANCE PROMPT GENERATOR
# ------------------------------------------------------------------------------

def build_compliance_system_prompt(
    patient_age, gender, cof_status, pa_status, specialty, 
    procedure_cat, tooth_num, arch_quad, surfaces, attachments, is_staged, staged_stage
):
    """Builds the comprehensive, 4-layer regulatory audit prompt."""
    
    prompt = f"""
You are FERRULE AI — an expert, ultra-rigorous Clinical Coding & Audit Engine for Saudi Dental Healthcare.
You strictly enforce:
1. Saudi Billing System (SBS v3.0) Coding Standards & Article 11 Government Tariffs.
2. CCHI / CHI Minimum Data Set (MDS) & Minimum Requirements Policy.
3. NPHIES Automated Adjudication Engine Denial Rules (86 Rules).
4. CBAHI 2016 Essential Safety Requirements (ESR QM.18 Site Safety, PC.10 Documentation).
5. ICD-10-AM 11th Edition Diagnostic Hierarchy & Depth Requirements.

PATIENT & ENCOUNTER METADATA:
- Age: {patient_age} | Gender: {gender}
- Condition Onset Flag (COF): {cof_status} (Mandatory COF=2 for pre-existing presentation)
- Prior-Authorization (PA) Status: {pa_status}
- Clinical Specialty: {specialty}
- Procedure Category: {procedure_cat}
- Primary Anatomical Site: Tooth FDI #{tooth_num} | Arch/Quadrant: {arch_quad} | Surfaces: {', '.join(surfaces) if surfaces else 'N/A'}
- Archived Attachments: {', '.join(attachments) if attachments else 'None Logged'}
- Multi-Visit Staged Encounter: {'YES (' + staged_stage + ')' if is_staged else 'NO (Single Visit)'}

CORE REGULATORY AUDIT MANDATES:

1. ICD-10-AM DIAGNOSTIC DEPTH & CROSSWALK RULES:
   - Restorations (Block 465/466): Require deepest caries layer (K02.0 Enamel | K02.1 Dentine | K02.2 Cementum).
   - Pulp Capping (97411): Requires K02.5 (Caries with pulp exposure) for accidental/vital exposure.
   - Root Canal Therapy (97420): MUST be paired with K04.0 (Pulpitis), K04.1 (Pulp Necrosis), or K04.4/K04.5 (Apical Periodontitis). Do NOT assign K02.5 for established RCT unless mechanical exposure without irreversible pulpitis.
   - Periodontics (Block 456): Scaling & Root Planing (97281) or Flap Surgery (97232) REQUIRES K05.3 (Chronic Periodontitis) and documented PPD >= 4-5mm.
   - Prosthetics/Implants (Block 400/470/474): REQUIRES K08.1 (Loss of teeth) or K08.2 (Alveolar ridge atrophy).
   - Preventive Exams (Z01.2): ONLY supports Exam (97011/97012) or Fluoride (97121). Never pair Z01.2 as principal diagnosis for active RCT, Crowns, or Extractions.

2. SBS V3.0 MULTI-VISIT TARIFF LOCKS & UNBUNDLING GUARDS:
   - Root Canal Therapy (97420-01/02/03-00): Intermediate dressing/irrigation (97455-00-10) is LOCKED at 0.00 SAR ("part of main service"). Global tariff (1,500 SAR) unlocks ONLY on final obturation visit.
   - Crowns (97613): Tooth preparation (97719-01-80) and temporary crown (97631-00-10) are LOCKED at 0.00 SAR. Global fee unlocks ONLY on final crown delivery.
   - Dentures (97711/97721): Preliminary steps (impressions, border molding, bite reg, try-in 97719-01-10 to 60) are LOCKED at 0.00 SAR. Tariff unlocks on insertion.
   - Implants (45845/45846): Enforce 3-6 month separation between Stage 1 (45845) and Stage 2 (45847). Enforce 3-code prosthetic sequence: [Prosthesis 97665/666] -> [Abutment 97661] -> [Attachment 97735].
   - Consultation Lock (N-DC-043): Do NOT bill consultations (97011-97014) during intermediate visits for the same condition within 14-30 days.

3. NPHIES ATTACHMENT & EVIDENTIARY MANDATES:
   - RCT (97420): Enforce 3 mandatory radiographs (Pre-op PA + Working Length Log + Post-op Obturation PA).
   - Crowns (97613): Enforce Pre-op PA/Bitewing proving >1.5-2.0mm sound ferrule height.
   - Periodontics (97281/97232): Enforce Full-mouth Periodontal Chart (PPD >= 4-5mm) + Radiographic Bone Loss.
   - Impactions (97321): Enforce Pre-op OPG/PA demonstrating bony impaction.

OUTPUT FORMAT INSTRUCTIONS:
Produce a structured, audit-ready compliance evaluation containing:
1. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (Strictly markdown checkboxes `* [x]` or `* [ ]` with 1 line per rule).
2. COMPLIANCE & AUDIT EVALUATION (Detailed findings, identified risk codes, and corrective actions).
3. STATUTORY ARTICLE 11 TARIFF TABLE (Markdown table with columns: Service Description | ACHI Code | SBS v3.0 Code | Block | Claim Action | Govt Tariff SAR | Bundled Elements).
4. MUTUALLY EXCLUSIVE ALTERNATIVES TABLE (If conflicting codes exist).
5. EMR CLINICAL NOTE (SOAP or SmartForm macro strictly enclosed between `<CLINICAL_NOTE_START>` and `<CLINICAL_NOTE_END>`).
6. NPHIES CASE CONTINUITY METADATA BLOCK (Strictly enclosed between `<NPHIES_BLOCK>` and `</NPHIES_BLOCK>`).
"""
    return prompt

# ------------------------------------------------------------------------------
# 4. STREAMLIT USER INTERFACE & WORKFLOW
# ------------------------------------------------------------------------------

# Header Banner
st.markdown('<div class="main-header">🦷 FERRULE AI — Clinical Coding & Compliance Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Zero-Leak Compliance for CHI, NPHIES Adjudication, SBS v3.0, ICD-10-AM, and CBAHI Standards</div>', unsafe_allow_html=True)

# Sidebar — Patient & Encounter Settings
with st.sidebar:
    st.header("📋 Patient & Encounter Context")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        patient_age = st.number_input("Patient Age", min_value=1, max_value=110, value=35)
    with col_s2:
        gender = st.selectbox("Gender", ["Male", "Female"])
        
    cof_status = st.selectbox("Condition Onset (COF)", ["COF = 2 (Present at presentation)", "COF = 1 (Arising during care)"])
    pa_status = st.selectbox("Prior-Auth Status", [
        "PA-Exempt (< 500 SAR Threshold)",
        "Mandatory PA Reference Obtained",
        "Emergency Encounter (Exempt)",
        "Prescription (Mandatory PA Required)"
    ])
    
    st.divider()
    st.info(f"🤖 **Active Engine Model:** Hardcoded to `{HARDCODED_GEMINI_MODEL}`")

    st.divider()
    st.header("🎯 Specialty & Site")
    specialty = st.selectbox("Clinical Specialty", [
        "Endodontics", "Restorative & Operative", "Periodontics", 
        "Prosthodontics (Fixed/Removable)", "Oral Surgery & Extractions",
        "Pediatric Dentistry", "Orthodontics", "Preventive & Diagnostic"
    ])
    
    procedure_cat = st.selectbox("Procedure Category", [
        "Root Canal Therapy (RCT)", "Direct Restoration (Filling)", 
        "Indirect Crown / Bridge", "Scaling & Root Planing",
        "Periodontics (Per Quadrant)", "Surgical Extraction / Impaction",
        "Dental Implant / Bone Graft", "Prosthodontics (Per Arch/Jaw)",
        "Orthodontics", "Fluoride / Full Mouth"
    ])
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        tooth_num = st.selectbox("FDI Tooth #", ["None / Not Applicable"] + [str(i) for i in list(range(11, 19)) + list(range(21, 29)) + list(range(31, 39)) + list(range(41, 48)) + list(range(51, 56)) + list(range(61, 65)) + list(range(71, 75)) + list(range(81, 85))])
    with col_a2:
        arch_quad = st.selectbox("Arch / Quadrant", ["Not Selected", "Quadrant 1 (Upper Right)", "Quadrant 2 (Upper Left)", "Quadrant 3 (Lower Left)", "Quadrant 4 (Lower Right)", "Maxillary Arch (Upper)", "Mandibular Arch (Lower)", "Both Arches (Full Mouth)"])

    surfaces = st.multiselect("Tooth Surfaces (Restorations Only)", ["M (Mesial)", "O (Occlusal)", "D (Distal)", "B/F (Buccal/Facial)", "L/P (Lingual/Palatal)", "I (Incisal)"])

    st.divider()
    st.header("📷 Archived Attachments")
    attachments = st.multiselect("Clinical Evidence Attached", [
        "Pre-operative Periapical Radiograph",
        "Working Length Radiograph / Apex Locator Log",
        "Post-operative Obturation Radiograph",
        "Bitewing Radiograph Series",
        "Panoramic Radiograph (OPG)",
        "Cone Beam CT (CBCT 3D)",
        "Full-Mouth Periodontal Chart (PPD/CAL)",
        "Clinical Photographs Series",
        "Prior Approval Authorization Letter"
    ])

    st.divider()
    st.header("🔄 Multi-Visit Staging")
    is_staged = st.checkbox("Multi-Visit Staged Procedure?", value=False)
    staged_stage = "Single Visit"
    if is_staged:
        staged_stage = st.selectbox("Current Encounter Stage", [
            "Visit 1 — Preparation / Extirpation / Primary Impression",
            "Visit 2 — Intermediate Dressing / Try-in / Border Molding",
            "Visit 3 — Final Obturation / Crown Cementation / Denture Delivery",
            "Visit 4+ — Post-Op Re-Evaluation / Adjustment"
        ])

# Main Area — Tabs Layout
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 1. Encounter Input & Audit", 
    "🔍 2. Search Codebook", 
    "📊 3. Statutory Tariff & Rules", 
    "🔒 4. EMR Note & NPHIES Metadata"
])

# ------------------------------------------------------------------------------
# TAB 1: ENCOUNTER INPUT & AUDIT
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("Enter Clinical Case Findings")
    
    # Pre-Flight Hard Validation Banner
    is_site_valid, site_msg = validate_anatomical_site(procedure_cat, tooth_num, arch_quad)
    if is_site_valid:
        st.success(site_msg)
    else:
        st.warning(site_msg)

    clinical_input = st.text_area(
        "Clinical Encounter Narrative / Provider Notes:",
        height=180,
        placeholder="e.g., 35-year-old male presented with severe spontaneous throbbing pain in tooth #46 for 3 days. Cold test positive, tender to percussion. Radiograph reveals deep mesial occlusal decay reaching pulp with widened PDL space. Performed access cavity, pulpectomy, working length determination (21mm MB, ML, D), chemomechanical prep, placed Ca(OH)2 dressing and Temporary restoration (Cavit). Planned final obturation next week.",
        help="Paste raw clinical notes, symptoms, treatment steps, and materials used."
    )

    api_key = get_gemini_api_key()
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        run_audit = st.button("🚀 Run Compliance Audit", type="primary", use_container_width=True)

    if run_audit:
        if not api_key:
            st.error("⚠️ Please enter a valid Gemini API Key in the sidebar or configure `GEMINI_API_KEY` in Streamlit secrets.")
        elif not clinical_input.strip():
            st.error("⚠️ Please enter a clinical encounter narrative before running the audit.")
        else:
            with st.spinner(f"Executing 4-Layer Compliance Audit using hardcoded model `{HARDCODED_GEMINI_MODEL}`..."):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    
                    # HARDCODED MODEL INSTANTIATION
                    model = genai.GenerativeModel(HARDCODED_GEMINI_MODEL)
                    
                    sys_prompt = build_compliance_system_prompt(
                        patient_age, gender, cof_status, pa_status, specialty,
                        procedure_cat, tooth_num, arch_quad, surfaces, attachments, is_staged, staged_stage
                    )
                    
                    full_user_prompt = f"{sys_prompt}\n\nRAW CLINICAL ENCOUNTER INPUT:\n{clinical_input}"
                    
                    response = model.generate_content(
                        full_user_prompt,
                        generation_config=genai.types.GenerationConfig(temperature=0.1)
                    )
                    
                    audit_result = response.text
                    st.session_state["audit_result"] = audit_result
                    st.success("✅ Compliance Audit Completed Successfully!")
                    
                except Exception as e:
                    st.error(f"❌ API Execution Error: {str(e)}")

    if "audit_result" in st.session_state:
        st.divider()
        st.markdown("### 🔍 Compliance Audit Results")
        st.markdown(st.session_state["audit_result"])

# ------------------------------------------------------------------------------
# TAB 2: STANDALONE CODEBOOK SEARCH ENGINE
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("📖 Standalone SBS v3.0 & ACHI Dental Codebook Search")
    st.markdown("Search across all official Saudi Billing System (SBS v3.0) procedure codes, ACHI 10th Edition crosswalks, block numbers, and clinical descriptions without triggering an AI audit.")
    
    codebook_df = load_codebook_dataframe()
    
    if codebook_df is not None:
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            search_query = st.text_input(
                "🔍 Search Code, Keyword, or Description:", 
                placeholder="e.g. 97420, root canal, crown, pulpectomy, examination, 97011, restoration...",
                help="Type any 9-digit SBS code, ACHI code, or clinical keyword."
            )
        with col_c2:
            if "SBS Block Number" in codebook_df.columns:
                all_blocks = ["All Blocks"] + [str(b) for b in sorted(codebook_df["SBS Block Number"].dropna().unique())]
                selected_block = st.selectbox("Filter by SBS Block:", all_blocks)
            else:
                selected_block = "All Blocks"
                
        # Filter Logic
        filtered_df = codebook_df.copy()
        
        if selected_block != "All Blocks":
            filtered_df = filtered_df[filtered_df["SBS Block Number"].astype(str) == str(selected_block)]
            
        if search_query.strip():
            q = search_query.strip().lower()
            mask = (
                filtered_df["SBS Code hyphenated"].astype(str).str.lower().str.contains(q, na=False) |
                filtered_df["Long Description"].astype(str).str.lower().str.contains(q, na=False) |
                filtered_df["ACHI Code"].astype(str).str.lower().str.contains(q, na=False) |
                filtered_df["ACHI Description"].astype(str).str.lower().str.contains(q, na=False)
            )
            filtered_df = filtered_df[mask]

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Total Codes Matched", f"{len(filtered_df)} / {len(codebook_df)}")
        with col_m2:
            st.caption("Crosswalk Version: SBS v3.0 to ACHI 10th Edition")

        display_cols = [
            "SBS Code hyphenated", "Long Description", "SBS Block Number", 
            "ACHI Code", "ACHI Description", "Source Code System Version (SBS)"
        ]
        available_cols = [c for c in display_cols if c in filtered_df.columns]

        st.dataframe(
            filtered_df[available_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "SBS Code hyphenated": st.column_config.TextColumn("SBS 9-Digit Code", width="medium"),
                "Long Description": st.column_config.TextColumn("SBS Clinical Description", width="large"),
                "SBS Block Number": st.column_config.TextColumn("Block", width="small"),
                "ACHI Code": st.column_config.TextColumn("ACHI Code", width="medium"),
                "ACHI Description": st.column_config.TextColumn("ACHI Description", width="large")
            }
        )
    else:
        st.warning("⚠️ Local `dental_sbs_achi_map.csv` file not detected in project folder. Quick lookup fallback enabled:")
        
        fallback_codes = [
            {"SBS Code": "97011-00-00", "Description": "Comprehensive oral examination", "Block": "450", "ACHI Code": "97011-00"},
            {"SBS Code": "97011-00-10", "Description": "Oral examination; post operative re-evaluation", "Block": "450", "ACHI Code": "97011-00"},
            {"SBS Code": "97012-00-00", "Description": "Periodic oral examination", "Block": "450", "ACHI Code": "97012-00"},
            {"SBS Code": "97013-00-00", "Description": "Limited oral examination", "Block": "450", "ACHI Code": "97013-00"},
            {"SBS Code": "97014-00-00", "Description": "Dental consultation", "Block": "450", "ACHI Code": "97014-00"},
            {"SBS Code": "97022-00-10", "Description": "Intraoral periapical radiography, per exposure", "Block": "451", "ACHI Code": "97022-00"},
            {"SBS Code": "97022-00-20", "Description": "Intraoral bitewing radiography, per exposure", "Block": "451", "ACHI Code": "97022-00"},
            {"SBS Code": "97114-00-00", "Description": "Removal of calculus, second or subsequent treatment stage", "Block": "452", "ACHI Code": "97114-00"},
            {"SBS Code": "97121-01-00", "Description": "Topical application of remineralising agent", "Block": "453", "ACHI Code": "97121-01"},
            {"SBS Code": "97281-00-10", "Description": "Root planing and subgingival curettage, per tooth", "Block": "456", "ACHI Code": "97281-00"},
            {"SBS Code": "97311-01-00", "Description": "Surgical removal of tooth or tooth fragment", "Block": "458", "ACHI Code": "97311-01"},
            {"SBS Code": "97321-01-00", "Description": "Surgical removal of tooth involving soft tissue and bone", "Block": "458", "ACHI Code": "97321-01"},
            {"SBS Code": "97411-00-10", "Description": "Direct pulp capping", "Block": "461", "ACHI Code": "97411-00"},
            {"SBS Code": "97414-00-00", "Description": "Pulpotomy", "Block": "461", "ACHI Code": "97414-00"},
            {"SBS Code": "97420-01-00", "Description": "Complete root canal treatment, anterior tooth", "Block": "462", "ACHI Code": "97420-01"},
            {"SBS Code": "97420-02-00", "Description": "Complete root canal treatment, premolar tooth", "Block": "462", "ACHI Code": "97420-02"},
            {"SBS Code": "97420-03-00", "Description": "Complete root canal treatment, molar tooth", "Block": "462", "ACHI Code": "97420-03"},
            {"SBS Code": "97455-00-10", "Description": "Irrigation and dressing of root canal system (intermediate stage)", "Block": "462", "ACHI Code": "97455-00"},
            {"SBS Code": "97511-00-00", "Description": "Adhesive restoration, 1 surface, anterior tooth", "Block": "465", "ACHI Code": "97511-00"},
            {"SBS Code": "97521-00-00", "Description": "Adhesive restoration, 1 surface, posterior tooth", "Block": "466", "ACHI Code": "97521-00"},
            {"SBS Code": "97613-01-00", "Description": "Full crown, porcelain/ceramic", "Block": "470", "ACHI Code": "97613-01"},
            {"SBS Code": "97613-02-00", "Description": "Full crown, zirconium", "Block": "470", "ACHI Code": "97613-02"}
        ]
        fb_df = pd.DataFrame(fallback_codes)
        
        s_input = st.text_input("🔍 Quick Search Fallback:", placeholder="e.g., 97420, root canal, crown, filling...")
        if s_input.strip():
            sq = s_input.strip().lower()
            fb_df = fb_df[
                fb_df["SBS Code"].str.lower().str.contains(sq) | 
                fb_df["Description"].str.lower().str.contains(sq) |
                fb_df["ACHI Code"].str.lower().str.contains(sq)
            ]
        st.dataframe(fb_df, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 3: STATUTORY TARIFF & RULES REFERENCE
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Saudi Billing System (SBS v3.0) & Regulatory Reference")
    st.info("💡 FERRULE AI automatically verifies claims against the 86 NPHIES Denial Rules and Article 11 Statutory Tariffs.")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("#### 🚫 Common NPHIES Dental Denial Triggers")
        for code, desc in DEFAULT_DENIAL_RULES.items():
            st.markdown(f"- **`{code}`**: {desc}")
            
    with col_r2:
        st.markdown("#### 💰 Multi-Visit Tariff Lock Rules")
        st.markdown("""
        - **RCT (97420):** Intermediate dressing (97455) locked at **0.00 SAR**. Global 1,500 SAR unlocks on final obturation.
        - **Crowns (97613):** Prep (97719) and Temp Crown (97631) locked at **0.00 SAR**. Crown fee unlocks on delivery.
        - **Dentures (97711/21):** Steps 97719-01 to 60 locked at **0.00 SAR**. Fee unlocks on final insertion.
        - **Consultation Lock (N-DC-043):** Exams (97011-14) during multi-visit care within 14-30 days are non-billable.
        """)

# ------------------------------------------------------------------------------
# TAB 4: EMR NOTE & NPHIES METADATA
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Generated EMR Note & Case Continuity Metadata")
    if "audit_result" in st.session_state:
        res_text = st.session_state["audit_result"]
        
        # Extract EMR Note
        note_match = re.search(r'<CLINICAL_NOTE_START>(.*?)</CLINICAL_NOTE_START>', res_text, re.DOTALL)
        if note_match:
            emr_note = note_match.group(1).strip()
            st.markdown("#### 📋 Clean EMR Clinical Note (Ready to Copy)")
            st.code(emr_note, language="text")
        else:
            st.warning("EMR Note tags `<CLINICAL_NOTE_START>` not detected in current output.")

        # Extract NPHIES Metadata Block
        nphies_match = re.search(r'<NPHIES_BLOCK>(.*?)</NPHIES_BLOCK>', res_text, re.DOTALL)
        if nphies_match:
            nphies_block = nphies_match.group(1).strip()
            st.markdown("#### 🔒 NPHIES Case Continuity Metadata")
            st.code(nphies_block, language="text")
    else:
        st.info("Run an audit in Tab 1 to generate the clean EMR note and NPHIES metadata block.")
