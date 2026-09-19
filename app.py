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
    .question-box { background-color: #F3F4F6; border: 1px solid #D1D5DB; padding: 16px; border-radius: 8px; margin-bottom: 12px; }
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
# 2. DYNAMIC AI DISCOVERY PROMPT WITH AI DROPDOWN GENERATION
# ------------------------------------------------------------------------------

DYNAMIC_DISCOVERY_PROMPT = """
You are FERRULE AI — an expert Clinical Assistant and CDI Specialist for Saudi Dental Healthcare.
Analyze the clinician's brief note and identify ANY missing clinical details required for an audit-proof, insurance claim-denial proof record under Saudi rules (SBS v3.0, Article 11, CCHI MDS, NPHIES, CBAHI ESR).

NOTE ON SBS V3.0 CODE FORMATTING: All SBS v3.0 codes MUST be strictly 9 digits in the 'XXXXX-XX-XX' hyphenated format (e.g., 97420-03-00 for Molar RCT, 97455-00-10 for RCT dressing, 97613-02-00 for zirconium crown).

Generate a set of 3 to 5 DYNAMIC, HIGHLY SPECIFIC QUESTIONS WITH PRE-POPULATED DROPDOWN OPTIONS (selection choices) based directly on the procedure detected in the note!

Examples of procedures & required dropdowns:
- If RCT/Pulpectomy: Ask for FDI tooth # (dropdown), Radiographs archived (multiselect options: Pre-op PA, WL log, Post-op obturation PA), Visit stage (dropdown), Anesthesia/Isolation (dropdown).
- If Crown/Bridge: Ask for FDI tooth # (dropdown), Sound ferrule verification (>1.5mm PA) (dropdown), Core buildup material (dropdown), Impression type (dropdown), Visit stage (dropdown).
- If Restoration/Filling: Ask for FDI tooth # (dropdown), Tooth surfaces involved (multiselect: M, O, D, B, L, I), Caries depth (dropdown: Enamel K02.0, Dentine K02.1, Pulp exposure K02.5), Material used (dropdown).
- If Denture: Ask for Arch/Jaw (dropdown: Upper Maxilla, Lower Mandible, Both Arches), Denture stage completed (dropdown: Primary Impression, Border Molding/Final Impression, Jaw Relation/Bite Reg, Wax Try-in, Final Insertion), Resin material (dropdown).
- If Extraction/Impaction: Ask for FDI tooth # (dropdown), Extraction type (Simple 97311-01-00 vs Surgical 97321-01-00), Radiograph (Pre-op OPG/PA), Anesthesia type (dropdown).

Return JSON strictly in this EXACT structure:
{
  "procedure_detected": "Identified Procedure Name (e.g., Molar Root Canal Therapy [SBS 97420-03-00] / Zirconium Crown Prep [SBS 97613-02-00])",
  "medical_necessity_guidance": "Brief 1-2 sentence guidance on medical necessity to avoid NPHIES denials (N-DC-044/045/084).",
  "questions": [
    {
      "id": "q1",
      "question": "Which tooth (FDI #) or region was treated?",
      "type": "selectbox",
      "options": ["Tooth #16 (Upper Right 1st Molar)", "Tooth #11", "Tooth #26", "Tooth #36", "Tooth #46", "Quadrant 1", "Quadrant 2", "Quadrant 3", "Quadrant 4", "Maxillary Arch", "Mandibular Arch"]
    },
    {
      "id": "q2",
      "question": "Which supporting radiographs / evidence are archived?",
      "type": "multiselect",
      "options": ["Pre-operative PA Radiograph", "Working Length Log / Apex Locator PA", "Post-operative Obturation PA", "Bitewing Radiograph Series", "Panoramic Radiograph (OPG)", "Full-Mouth Periodontal Chart (PPD >= 4-5mm)"]
    },
    {
      "id": "q3",
      "question": "What visit stage was completed today?",
      "type": "selectbox",
      "options": ["Single Visit (Completed today)", "Visit 1: Prep / Extirpation / Primary Impression", "Visit 2: Intermediate Dressing / Try-in / Border Molding", "Visit 3: Final Obturation / Crown Cementation / Insertion"]
    },
    {
      "id": "q4",
      "question": "What anesthesia and isolation method were used?",
      "type": "selectbox",
      "options": ["Local Infiltration (2% Lidocaine 1:100k) + Cotton Roll Isolation", "Infiltration / Block + Rubber Dam Isolation", "Nerve Block + Cotton Roll Isolation", "No Local Anesthesia Used"]
    }
  ]
}
"""

def build_final_audit_prompt(doctor_note, note_style, is_staged, staged_stage, additional_details_formatted):
    prompt = f"""
You are FERRULE AI — an expert Clinical Assistant, Revenue Cycle Partner, and CDI Specialist in Saudi Arabia.
Your core mission is to empower the clinician by taking their raw notes and selected dropdown details, turning them into an AUDIT-PROOF, INSURANCE CLAIM-DENIAL PROOF clinical encounter record that guarantees maximum compliant reimbursement under Saudi regulations.

CLINICIAN'S RAW INPUT NOTE:
{doctor_note}

CLINICIAN'S DROPDOWN-SELECTED DETAILS:
{additional_details_formatted if additional_details_formatted else 'All details inferred from primary note.'}

CLINICIAN'S PREFERENCES:
- Desired Note Style: {note_style}
- Multi-Visit Staged Encounter: {'YES (' + staged_stage + ')' if is_staged else 'NO / Single Visit'}

STRICT REGULATORY & COMPLIANCE MANDATES TO ENFORCE:
1. CRITICAL SBS V3.0 CODE FORMAT: ALL Saudi Billing System (SBS v3.0) procedure codes MUST be formatted strictly as 9 digits in the 'XXXXX-XX-XX' hyphenated format (e.g., 97420-03-00 for Molar RCT, 97455-00-10 for RCT dressing, 97613-02-00 for Zirconium crown, 97719-01-80 for Tooth prep, 97521-00-00 for Posterior restoration). NEVER write 5-digit or unhyphenated codes in the SBS v3.0 column.
2. ICD-10-AM DIAGNOSTIC DEPTH: Map the deepest anatomical caries/disease depth (K02.0 Enamel | K02.1 Dentine | K04.0 Irreversible Pulpitis | K05.3 Chronic Periodontitis). Prevent diagnosis mismatches (N-DC-044/N-DC-060).
3. SBS V3.0 TARIFF LOCKS & UNBUNDLING SHIELD: Lock intermediate visits (e.g., RCT dressing 97455-00-10 or crown prep 97719-01-80) at 0.00 SAR ("part of main service") to eliminate unbundling fraud rejections (N-DC-084 / Error 1675). Global fees unlock ONLY on final completion visits.
4. ARTICLE 11 TARIFF PRICING: Apply statutory government prices for billable definitive services.
5. NPHIES ATTACHMENT MATRIX: Explicitly document required radiographs (Pre-op PA, Working length, Post-op obturation, OPG, CBCT) or Periodontal charts (PPD >= 4-5mm).
6. CBAHI ESR SAFETY STANDARDS: Verify FDI 2-digit site safety (ESR QM.18) and documentation integrity (PC.10).

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
Markdown table with columns (SBS Code MUST be 9 digits XXXXX-XX-XX):
| Service Description | ACHI Code (5 digits) | SBS v3.0 Code (9 digits XXXXX-XX-XX) | Block | Claim Action | Govt Tariff SAR | Bundled / Locked Status |

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
# 3. STREAMLIT USER INTERFACE (AI DROPDOWN DISCOVERY WORKFLOW)
# ------------------------------------------------------------------------------

# Header Banner
st.markdown('<div class="main-header">🦷 FERRULE AI — Clinical Assistant & Revenue Shield</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Write a brief note, let AI generate targeted dropdowns for missing details, prevent denials, and build audit-proof claims.</div>', unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Assistant Preferences")
    
    guided_mode = st.radio(
        "Guided Discovery Mode:",
        ["ON — AI asks missing details via Dropdowns", "OFF — Directly generate audit-proof claim"],
        index=0,
        help="When ON, AI analyzes your note and generates instant dropdown choices for missing clinical variables."
    )
    is_guided_on = guided_mode.startswith("ON")

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

# Main Interface Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 1. Clinical Assistant & Audit", 
    "📖 2. Standalone Codebook Search", 
    "📊 3. Regulatory Cheat Sheet", 
    "🔒 4. EMR Note & NPHIES Metadata"
])

# ------------------------------------------------------------------------------
# TAB 1: CLINICAL ASSISTANT & AUDIT WITH AI DROPDOWNS
# ------------------------------------------------------------------------------
with tab1:
    st.markdown('<div class="assistant-box">💡 <b>Zero-Typing Assistant:</b> Write a brief 1-2 sentence note. FERRULE AI will generate custom <b>dropdown choices</b> for any missing details so you can complete your claim with just a few clicks!</div>', unsafe_allow_html=True)
    
    doctor_note = st.text_area(
        "Enter Clinical Encounter Narrative (a few words or sentences):",
        height=120,
        placeholder="e.g. prep tooth 16 for zirconium crown placed core buildup and temp crown",
        help="Write or dictate a brief description of what was done during the visit."
    )

    api_key = get_gemini_api_key()
    
    col_a1, col_a2 = st.columns([1, 2])
    with col_a1:
        run_process = st.button("🚀 Step 1: Analyze Note & Build Dropdowns", type="primary", use_container_width=True)

    # STEP 1: RUN DISCOVERY & BUILD AI DROPDOWNS
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

                if is_guided_on:
                    with st.spinner("AI Assistant Analyzing Note & Generating Targeted Dropdowns..."):
                        disc_prompt = f"{DYNAMIC_DISCOVERY_PROMPT}\n\nCLINICIAN NOTE:\n{doctor_note}"
                        disc_response = model.generate_content(
                            disc_prompt,
                            generation_config=genai.types.GenerationConfig(temperature=0.1)
                        )
                        raw_disc = disc_response.text
                        
                        try:
                            json_match = re.search(r'\{.*\}', raw_disc, re.DOTALL)
                            if json_match:
                                disc_data = json.loads(json_match.group(0))
                            else:
                                disc_data = {"procedure_detected": "Dental Procedure", "medical_necessity_guidance": "Complete required clinical indicators.", "questions": []}
                        except Exception:
                            disc_data = {"procedure_detected": "Dental Procedure", "medical_necessity_guidance": "Complete required clinical indicators.", "questions": []}

                        st.session_state["discovery_data"] = disc_data
                        st.session_state["doctor_note_saved"] = doctor_note
                        st.session_state["step1_done"] = True
                else:
                    # Directly run Step 2 if Guided Mode is OFF
                    with st.spinner(f"Generating Audit-Proof Claim & {note_style}..."):
                        final_prompt = build_final_audit_prompt(doctor_note, note_style, is_staged, staged_stage, "")
                        final_response = model.generate_content(
                            final_prompt,
                            generation_config=genai.types.GenerationConfig(temperature=0.1)
                        )
                        st.session_state["audit_result"] = final_response.text
                        st.success("✅ Audit-Proof Claim & Note Generated Successfully!")

            except Exception as e:
                st.error(f"❌ Execution Error: {str(e)}")

    # DISPLAY STEP 2: AI-GENERATED DROPDOWNS
    if "discovery_data" in st.session_state and is_guided_on:
        disc = st.session_state["discovery_data"]
        st.divider()
        st.markdown(f"### 🎯 Step 2: Confirm Missing Details for {disc.get('procedure_detected', 'Dental Procedure')}")
        st.info(f"💡 **Medical Necessity Tip:** {disc.get('medical_necessity_guidance', 'Select options below to ensure claim approval.')}")

        questions = disc.get("questions", [])
        user_responses = {}

        if questions:
            st.markdown("#### 📋 Select From AI-Generated Dropdowns (Zero Writing Required):")
            
            with st.form("dropdown_discovery_form"):
                for q in questions:
                    q_id = q.get("id", "q")
                    q_text = q.get("question", "Question")
                    q_type = q.get("type", "selectbox")
                    q_options = q.get("options", ["Not Applicable / None"])

                    if q_type == "multiselect":
                        user_responses[q_text] = st.multiselect(q_text, options=q_options, key=f"form_{q_id}")
                    else:
                        user_responses[q_text] = st.selectbox(q_text, options=q_options, key=f"form_{q_id}")

                submit_final = st.form_submit_button("🚀 Step 3: Generate Audit-Proof Record", type="primary", use_container_width=True)

            if submit_final:
                formatted_choices = []
                for q_k, q_v in user_responses.items():
                    if isinstance(q_v, list):
                        formatted_choices.append(f"- **{q_k}**: {', '.join(q_v) if q_v else 'None selected'}")
                    else:
                        formatted_choices.append(f"- **{q_k}**: {q_v}")
                
                additional_details_formatted = "\n".join(formatted_choices)
                
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(HARDCODED_MODEL)

                    saved_note = st.session_state.get("doctor_note_saved", doctor_note)
                    with st.spinner("Finalizing Audit-Proof Claim, Tariff Table & Clinical Note..."):
                        final_prompt = build_final_audit_prompt(
                            saved_note, note_style, is_staged, staged_stage, additional_details_formatted
                        )
                        final_response = model.generate_content(
                            final_prompt,
                            generation_config=genai.types.GenerationConfig(temperature=0.1)
                        )
                        st.session_state["audit_result"] = final_response.text
                        st.success("✅ Audit-Proof Claim & Ideal Note Generated Successfully!")

                except Exception as e:
                    st.error(f"❌ Final Audit Error: {str(e)}")

    # DISPLAY AUDIT RESULTS
    if "audit_result" in st.session_state:
        st.divider()
        st.markdown("### 🔍 Final Audit & Revenue Shield Results")
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
                placeholder="e.g. 97420-03-00, root canal, crown, pulpectomy, examination, restoration...",
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
        st.markdown("#### 💰 Mandatory Multi-Visit Tariff Locks (9-Digit SBS v3.0 Codes)")
        st.markdown("""
        - **Root Canal Therapy (`97420-03-00`):** Intermediate dressing (`97455-00-10`) locked at **`0.00 SAR`**. Global tariff unlocks on obturation.
        - **Indirect Crowns (`97613-02-00`):** Tooth prep (`97719-01-80`) & Temp crown (`97631-00-10`) locked at **`0.00 SAR`**. Tariff unlocks on crown delivery.
        - **Complete Dentures (`97711-00-00` / `97721-00-00`):** Impressions, try-in (`97719-01-10` to `60`) locked at **`0.00 SAR`**. Fee unlocks on final insertion.
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
