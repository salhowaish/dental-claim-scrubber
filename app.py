import streamlit as st
import json
import os
import re
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="FERRULE AI — Clinical Assistant & Revenue Shield",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

HARDCODED_MODEL = "gemini-3.8-flash"

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #374151; margin-bottom: 1.2rem; }
    .assistant-box { background-color: #EFF6FF; border-left: 5px solid #2563EB; padding: 16px; border-radius: 8px; margin-bottom: 20px; }
    .warning-box { background-color: #FFFBEB; border-left: 5px solid #F59E0B; padding: 16px; border-radius: 8px; margin-bottom: 20px; }
    .success-box { background-color: #ECFDF5; border-left: 5px solid #10B981; padding: 16px; border-radius: 8px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 1. API KEY & DATA LOADERS
# ------------------------------------------------------------------------------

def get_gemini_api_key():
    """Retrieve Gemini API Key from Streamlit Secrets or Sidebar Input."""
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        return st.secrets["GEMINI_API_KEY"]
    return st.sidebar.text_input("Gemini API Key", type="password", help="Enter API Key if not in secrets.toml")

@st.cache_data
def load_codebook_dataframe():
    """Safely load SBS codebook map CSV."""
    candidate_paths = [
        "dental_sbs_achi_map.csv",
        "knowledge/dental_sbs_achi_map.csv",
        "/workspace/knowledge/dental_sbs_achi_map.csv"
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                return pd.read_csv(path)
            except Exception:
                pass
    return None

# ------------------------------------------------------------------------------
# 2. PROMPT BUILDERS FOR CLINICIAN ASSISTANT ENGINE
# ------------------------------------------------------------------------------

DISCOVERY_PROMPT = f"""
You are FERRULE AI — an empathetic, expert Clinical Assistant & Revenue Cycle Partner for Saudi Dental Clinicians.
Your purpose is to ASSIST and GUIDE the clinician, NOT to examine or quiz them.
Analyze the clinician's brief note/narrative and identify ANY missing clinical details, documentation elements, or diagnostic evidence required to guarantee 100% audit-proof claim payment under Saudi regulations (SBS v3.0, Article 11, CCHI MDS, NPHIES, and CBAHI ESR standards).

Analyze the procedure described (e.g. Root Canal, Crown, Filling, Denture, Extraction, Scaling/SRP, Implant, Ortho, etc.) and generate a structured JSON output with missing details to prompt the clinician gently.

Return JSON in this EXACT structure:
{{
  "procedure_detected": "Identified Procedure Name (e.g., Molar Root Canal Therapy / Complete Denture)",
  "missing_critical_details": [
    "Specific missing item 1 (e.g., Tooth number FDI 11-48, or Tooth Surface M/O/D/B/L)",
    "Specific missing item 2 (e.g., Pre-op PA X-ray confirmation or Working length log)",
    "Specific missing item 3 (e.g., Single visit vs Multi-visit stage, Denture try-in step)",
    "Specific missing item 4 (e.g., Anesthesia type/dosage or Rubber Dam isolation)"
  ],
  "medical_necessity_guidance": "Brief explanation of what examination findings or diagnostic criteria must be written in the note to prevent NPHIES claim denials (e.g., N-DC-044, N-DC-045, N-DC-084).",
  "suggested_questions_for_clinician": [
    "Which tooth number (FDI #) or mouth region was treated?",
    "Was this completed in a single visit or is it part of a staged multi-visit treatment?",
    "What anesthesia and isolation methods were used?",
    "Which radiographs (Pre-op PA, Working length, Post-op obturation, OPG, CBCT) were taken?"
  ]
}}
"""

def build_final_audit_prompt(doctor_note, note_style, is_staged, staged_stage, additional_details):
    prompt = f"""
You are FERRULE AI — an expert Clinical Assistant, Revenue Cycle Partner, and CDI Specialist in Saudi Arabia.
Your core mission is to empower the clinician by taking their raw notes and turning them into an AUDIT-PROOF, INSURANCE CLAIM-DENIAL PROOF clinical encounter record that guarantees maximum compliant reimbursement under Saudi regulations.

CLINICIAN'S RAW INPUT:
{doctor_note}

ADDITIONAL CONFIRMED CLINICAL DETAILS:
{additional_details if additional_details else 'None additional provided'}

CLINICIAN'S PREFERENCES:
- Desired Note Style: {note_style}
- Multi-Visit Staged Encounter: {'YES (' + staged_stage + ')' if is_staged else 'NO / Single Visit'}

REGULATORY & COMPLIANCE MANDATES TO ENFORCE:
1. ICD-10-AM DIAGNOSTIC DEPTH: Map the deepest anatomical caries/disease depth (K02.0 Enamel | K02.1 Dentine | K04.0 Irreversible Pulpitis | K05.3 Chronic Periodontitis). Prevent diagnosis mismatches (N-DC-044/N-DC-060).
2. SBS V3.0 TARIFF LOCKS & UNBUNDLING SHIELD: Lock intermediate visits (e.g., RCT dressing 97455 or crown prep 97719) at 0.00 SAR ("part of main service") to eliminate unbundling fraud rejections (N-DC-084 / Error 1675).
3. ARTICLE 11 TARIFF PRICING: Apply statutory government prices for billable definitive services.
4. NPHIES ATTACHMENT MATRIX: Explicitly document required radiographs (Pre-op PA, Working length, Post-op obturation, OPG, CBCT) or Periodontal charts (PPD >= 4-5mm).
5. CBAHI ESR SAFETY STANDARDS: Verify FDI 2-digit site safety (ESR QM.18) and documentation integrity (PC.10).

OUTPUT REQUIREMENTS:
Produce a structured, clean response with these exact sections:

### 1. 🛡️ CLINICIAN'S PRE-FLIGHT COMPLIANCE & MEDICAL NECESSITY CHECKLIST
Provide single-line markdown checkboxes `* [x]` confirming:
- Anatomical site & surfaces verified (FDI tooth # or Arch/Quadrant).
- ICD-10-AM Primary Diagnosis justifies medical necessity.
- Required diagnostic radiographs/attachments archived.
- Unbundling & tariff locks applied (0.00 SAR on intermediate steps).
- NPHIES denial codes prevented (N-DC-044, N-DC-045, N-DC-084, N-DC-043).

### 2. 💰 STATUTORY ARTICLE 11 PAYABLE TARIFF TABLE
Markdown table with columns:
| Service Description | ACHI Code | SBS v3.0 Code | Block | Claim Action | Govt Tariff SAR | Bundled / Locked Status |

### 3. 📋 AUDIT-PROOF CLINICAL NOTE
Generate the ideal clinical note in the requested style ({note_style}):
- If "Concise SmartForm Macro", generate a tight, professional hospital macro.
- If "Detailed SOAP Progress Note", generate a complete Subjective, Objective, Assessment, Plan note.
- Enclose the note strictly between `<CLINICAL_NOTE_START>` and `<CLINICAL_NOTE_END>`.

### 4. 🔒 NPHIES CASE CONTINUITY METADATA
Output structured episode tracking metadata strictly enclosed between `<NPHIES_BLOCK>` and `</NPHIES_BLOCK>`.
"""
    return prompt

# ------------------------------------------------------------------------------
# 3. STREAMLIT USER INTERFACE (FRICTIONLESS ASSISTANT WORKFLOW)
# ------------------------------------------------------------------------------

# Header Banner
st.markdown('<div class="main-header">🦷 FERRULE AI — Clinical Assistant & Revenue Shield</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Your intelligent clinical copilot: write a brief note, get guided discovery, prevent denials, and generate audit-proof claims.</div>', unsafe_allow_html=True)

# Sidebar Controls (Clinician Options)
with st.sidebar:
    st.header("⚙️ Assistant Preferences")
    
    # Toggle 1: Guided Discovery Mode
    guided_mode = st.radio(
        "Guided Discovery Mode:",
        ["ON — Analyze note & ask for missing details", "OFF — Directly generate audit-proof claim & note"],
        index=0,
        help="When ON, AI proactively suggests missing tooth numbers, X-rays, visit stages, and anesthesia details before finalizing."
    )
    is_guided_on = guided_mode.startswith("ON")

    # Toggle 2: Clinical Note Format Choice
    note_style = st.selectbox(
        "Clinical Note Style:",
        [
            "Concise SmartForm Macro (Hospital Standard)",
            "Detailed SOAP Progress Note (Academic / Hospital Standard)",
            "Audit & Tariff Only (Skip Note Generation)"
        ],
        index=0,
        help="Choose your preferred documentation style for your EMR."
    )

    st.divider()
    st.header("🔄 Procedure Staging")
    is_staged = st.checkbox("Is this a Multi-Visit Staged Procedure?", value=False)
    staged_stage = "Single Visit"
    if is_staged:
        staged_stage = st.selectbox(
            "Current Visit Stage:",
            [
                "Visit 1 — Preparation / Extirpation / Primary Impression",
                "Visit 2 — Intermediate Dressing / Try-in / Border Molding",
                "Visit 3 — Final Obturation / Crown Cementation / Denture Delivery",
                "Visit 4+ — Post-Op Re-Evaluation / Adjustment"
            ]
        )

    st.divider()
    st.info(f"🤖 **Active Engine Model:** Hardcoded to `{HARDCODED_MODEL}`")

# Main Interface — Tabs Layout
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 1. Clinical Assistant & Audit", 
    "📖 2. Standalone Codebook Search", 
    "📊 3. Regulatory Cheat Sheet", 
    "🔒 4. EMR Note & NPHIES Metadata"
])

# ------------------------------------------------------------------------------
# TAB 1: CLINICAL ASSISTANT & AUDIT
# ------------------------------------------------------------------------------
with tab1:
    st.markdown('<div class="assistant-box">💡 <b>How it works:</b> Write down a simple note or a few sentences about your patient encounter. FERRULE AI will analyze your note, guide you on missing details to protect your claim, and generate an ideal audit-proof clinical record.</div>', unsafe_allow_html=True)
    
    doctor_note = st.text_area(
        "Enter Clinical Encounter Narrative (a few words or sentences):",
        height=140,
        placeholder="e.g., pt came with severe spontaneous pain lower right 1st molar, deep decay into pulp. Performed pulpectomy, working length 21mm, placed CaOH dressing and Cavit temporary filling. Billed RCT and dressing.",
        help="Write or dictate a brief description of what was done and found during the visit."
    )

    api_key = get_gemini_api_key()
    
    col_a1, col_a2 = st.columns([1, 2])
    with col_a1:
        run_process = st.button("🚀 Analyze Note & Guide Claim", type="primary", use_container_width=True)

    if run_process:
        if not api_key:
            st.error("⚠️ Please enter your Gemini API Key in the sidebar.")
        elif not doctor_note.strip():
            st.error("⚠️ Please enter a brief clinical note before running.")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(HARDCODED_MODEL)

                # Step 1: Run Guided Discovery if Enabled
                if is_guided_on:
                    with st.spinner("AI Assistant Analyzing Note for Missing Evidence & Details..."):
                        disc_prompt = f"{DISCOVERY_PROMPT}\n\nCLINICIAN NOTE:\n{doctor_note}"
                        disc_response = model.generate_content(
                            disc_prompt,
                            generation_config=genai.types.GenerationConfig(temperature=0.1)
                        )
                        raw_disc = disc_response.text
                        
                        # Try parsing JSON
                        try:
                            json_match = re.search(r'\{.*\}', raw_disc, re.DOTALL)
                            if json_match:
                                disc_data = json.loads(json_match.group(0))
                            else:
                                disc_data = {"procedure_detected": "Dental Procedure", "missing_critical_details": [], "medical_necessity_guidance": raw_disc, "suggested_questions_for_clinician": []}
                        except Exception:
                            disc_data = {"procedure_detected": "Dental Procedure", "missing_critical_details": [], "medical_necessity_guidance": raw_disc, "suggested_questions_for_clinician": []}

                        st.session_state["discovery_data"] = disc_data

                # Step 2: Run Full Compliance Audit & Note Generator
                with st.spinner(f"Generating Audit-Proof Claim & {note_style}..."):
                    final_prompt = build_final_audit_prompt(
                        doctor_note, note_style, is_staged, staged_stage, 
                        st.session_state.get("additional_details_text", "")
                    )
                    final_response = model.generate_content(
                        final_prompt,
                        generation_config=genai.types.GenerationConfig(temperature=0.1)
                    )
                    st.session_state["audit_result"] = final_response.text
                    st.success("✅ Audit-Proof Claim & Note Generated Successfully!")

            except Exception as e:
                st.error(f"❌ Execution Error: {str(e)}")

    # Display Guided Discovery Assistant Box if available
    if "discovery_data" in st.session_state and is_guided_on:
        disc = st.session_state["discovery_data"]
        st.divider()
        st.markdown(f"### 💡 AI Guided Discovery: {disc.get('procedure_detected', 'Dental Procedure')}")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 🔍 Missing Details Needed for Audit-Proof Claim:")
            for item in disc.get("missing_critical_details", []):
                st.markdown(f"- ⚠️ **{item}**")
        with col_g2:
            st.markdown("#### 🛡️ Medical Necessity & Denial Protection Guidance:")
            st.info(disc.get("medical_necessity_guidance", "Ensure complete clinical indicators are documented."))

        # Quick Additional Details Input
        with st.expander("✏️ Quick-Fill Missing Details to Complete Your Note (Optional)", expanded=True):
            add_input = st.text_input(
                "Add missing details here (e.g. Tooth #46, Mesial-Occlusal, Rubber dam, 2% Lidocaine, Pre-op & WL X-rays taken):",
                key="add_details_box",
                placeholder="e.g. Tooth 46, Mesial-Occlusal, IAN block 2% Lidocaine, Rubber dam isolation, Pre-op PA and WL X-ray archived."
            )
            if st.button("🔄 Update & Re-Generate Final Note", type="secondary"):
                st.session_state["additional_details_text"] = add_input
                st.rerun()

    # Display Audit Results
    if "audit_result" in st.session_state:
        st.divider()
        st.markdown("### 🔍 Complete Audit & Revenue Shield Results")
        st.markdown(st.session_state["audit_result"])

# ------------------------------------------------------------------------------
# TAB 2: STANDALONE CODEBOOK SEARCH
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("📖 Standalone SBS v3.0 & ACHI Dental Codebook Search")
    st.markdown("Search across all official Saudi Billing System (SBS v3.0) procedure codes and ACHI 10th Edition crosswalks without running an AI audit.")
    
    codebook_df = load_codebook_dataframe()
    if codebook_df is not None:
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            search_query = st.text_input(
                "🔍 Search Code, Keyword, or Description:", 
                placeholder="e.g. 97420, root canal, crown, pulpectomy, examination, restoration...",
            )
        with col_c2:
            if "SBS Block Number" in codebook_df.columns:
                all_blocks = ["All Blocks"] + [str(b) for b in sorted(codebook_df["SBS Block Number"].dropna().unique())]
                selected_block = st.selectbox("Filter by SBS Block:", all_blocks)
            else:
                selected_block = "All Blocks"
                
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

        st.metric("Total Codes Matched", f"{len(filtered_df)} / {len(codebook_df)}")
        display_cols = ["SBS Code hyphenated", "Long Description", "SBS Block Number", "ACHI Code", "ACHI Description"]
        avail_cols = [c for c in display_cols if c in filtered_df.columns]
        st.dataframe(filtered_df[avail_cols], use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Local `dental_sbs_achi_map.csv` not detected in project directory.")

# ------------------------------------------------------------------------------
# TAB 3: REGULATORY CHEAT SHEET
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Saudi Billing System (SBS v3.0) & NPHIES Denial Prevention Shield")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("#### 🚫 Primary NPHIES Denial Codes Prevented")
        st.markdown("""
        - **`N-DC-044`**: Service not clinically indicated based on clinical documentation.
        - **`N-DC-045`**: Service not clinically indicated without supporting diagnostic evidence.
        - **`N-DC-084`**: Unbundling violation (intermediate stage submitted with global procedure).
        - **`N-DC-043`**: Consultation billed within mandatory free follow-up window (14-30 days).
        - **`BE-1-4`**: Prior approval required and not obtained.
        """)
    with col_r2:
        st.markdown("#### 💰 Mandatory Multi-Visit Tariff Locks")
        st.markdown("""
        - **Root Canal Therapy (97420):** Intermediate dressing (`97455`) locked at **`0.00 SAR`**. Global tariff unlocks on obturation.
        - **Indirect Crowns (97613):** Tooth prep (`97719`) & Temp crown (`97631`) locked at **`0.00 SAR`**. Tariff unlocks on crown delivery.
        - **Complete Dentures (97711/21):** Impressions, try-in (`97719-01`) locked at **`0.00 SAR`**. Fee unlocks on final insertion.
        """)

# ------------------------------------------------------------------------------
# TAB 4: EMR NOTE & NPHIES METADATA
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Generated EMR Clinical Note & NPHIES Metadata")
    if "audit_result" in st.session_state:
        res_text = st.session_state["audit_result"]
        
        note_match = re.search(r'<CLINICAL_NOTE_START>(.*?)</CLINICAL_NOTE_START>', res_text, re.DOTALL)
        if note_match:
            st.markdown("#### 📋 Clean EMR Clinical Note (Ready to Copy)")
            st.code(note_match.group(1).strip(), language="text")
            
        nphies_match = re.search(r'<NPHIES_BLOCK>(.*?)</NPHIES_BLOCK>', res_text, re.DOTALL)
        if nphies_match:
            st.markdown("#### 🔒 NPHIES Case Continuity Metadata")
            st.code(nphies_match.group(1).strip(), language="text")
    else:
        st.info("Run an audit in Tab 1 to generate the clean EMR note and NPHIES metadata block.")
