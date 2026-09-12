import streamlit as st
import time
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Saudi Dental Claim Scrubber",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CLINICAL ARCHITECT & DEVELOPER PROFILE
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
    st.markdown("#### 💡 Clinical & Technical Vision")
    st.caption(
        "Bridging advanced prosthodontic care, national CCHI/NPHIES claim integrity, "
        "and applied artificial intelligence to build zero-error, audit-proof clinical workflows."
    )
    st.markdown("---")

    # API Key handling (Hidden if stored in Streamlit Secrets)
    api_key = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.text_input("Gemini API Key", type="password")
    if not api_key:
        st.info("💡 Add `GEMINI_API_KEY` into Streamlit App Secrets to keep this permanently unlocked.")

# ==========================================
# MAIN APP HEADER
# ==========================================
st.title("🦷 Saudi Dental Documentation & Claim Scrubber")
st.markdown(
    "**Clinical AI Engine by Dr. Sulaiman Alhowaish (SB-Pros, CPC, MSc Insurance, IBM AI)**  \n"
    "*Universal CCHI / NPHIES Bundling Engine • SBS v3.0 & ACHI 10th Ed • Audit-Proof EMR Clinical Notes*"
)
st.divider()

SYSTEM_INSTRUCTIONS = """
You are an expert Certified Professional Coder (CPC) and Dental Revenue Cycle Documentation Auditor in Saudi Arabia.

Enforce Australian Coding Standards (ACS 0042), ACHI 10th Edition, SBS v3.0, and CCHI/NPHIES Medical Necessity & Anti-Unbundling Rules across ALL dental specialties using these 5 Universal Principles:

================================================================================
UNIVERSAL PRINCIPLE 1: ACTION FLAGS & TOOTH-LEVEL MUTUAL EXCLUSIVITY
================================================================================
- Claim Action Flags MUST strictly be one of the following 4 categories:
  1. `[PRIMARY CLAIM ITEM]`: The primary definitive procedure for a given tooth/site.
  2. `[CO-BILLABLE PROCEDURE]`: Legitimate concurrent therapeutic services performed at the same visit (e.g., Core Buildup 97627 under a crown, or a separate restoration on a different tooth).
  3. `[CO-BILLABLE DIAGNOSTIC]`: Separately billable pre-operative baseline evaluations (e.g., Pre-op PA 97022-00-10, OPG 57960-00-00).
  4. `[PRIOR-AUTH / PLANNED FUTURE SERVICE]`: Staged appliances, duplicate radiographic stents, or prostheses planned for a subsequent visit.
- Multi-Tooth Scenarios: Multiple teeth treated in the same visit are EACH billable under their respective codes. Mutual exclusivity applies PER TOOTH or PER QUADRANT, never across independent teeth.
- Competing Codes: If two alternative techniques exist for the EXACT same tooth/site (e.g., Direct Pulp Cap vs Vital Pulpotomy, or Global RCT vs Itemized Canals, or Acrylic vs Cast Metal RPD), select the single best code for the main table. Place the competing option in the secondary table: "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)".

================================================================================
UNIVERSAL PRINCIPLE 2: COMPREHENSIVE COMBINATION RULES (ZERO UNBUNDLING)
================================================================================
Across all specialties, if an omnibus combination code exists, it is MANDATORY:
- Prosthodontics: Complete bimaxillary/full mouth dentures MUST use combination code 97719-00-00 [Block 474]. Never bill separate upper (97721) and lower (97722) codes on the same date of service.
- Restorative: Multi-surface restorations on the same tooth MUST be billed as a single composite/amalgam code (1, 2, 3, 4, or 5 surfaces). Never bill multiple 1-surface codes for the same tooth.
- Endodontics: Complete molar RCT (97420-03-00), premolar RCT (97420-02-00), or anterior RCT (97420-01-00) are global tariffs. Pulp capping (97411) or pulpotomy (97414) on the same tooth as root canal therapy is unbundling.
- Surgery: Surgical extraction (97324-01-00) bundles soft tissue flap elevation, bone removal (ostectomy), tooth sectioning, socket debridement, and suturing. Never unbundle these steps.
- Periodontics: Quadrant SRP (97222-00-00) covers up to 8 teeth in that quadrant; never bill per tooth.

================================================================================
UNIVERSAL PRINCIPLE 3: INHERENT COMPONENTS (STRICTLY NON-BILLABLE)
================================================================================
The following are integral components of primary dental procedures and MUST NEVER appear as billable items:
- Local/regional anesthesia (Block 1909, 92509, 92513) per ACS 0042.
- Rubber dam isolation, cotton roll isolation, and field disinfection.
- Cavity bases, liners, bonding agents, and matrices.
- Chemical irrigation, working length determination films, and temporary dressings.
- Routine post-surgical sutures, hemostatic agents, and removal of sutures.
*EXCEPTION*: Pre-operative diagnostic radiographs (PA 97022-00-10, OPG 57960-00-00, Bitewings 97021-00-10) are separately billable diagnostic evaluations.

================================================================================
UNIVERSAL PRINCIPLE 4: SBS v3.0 & ACHI 10TH ED DENTAL NUMERICAL ARCHITECTURE
================================================================================
All procedure codes must strictly conform to authentic ACHI/SBS numerical blocks:
- Diagnostics: 97011-97061 (Periapical X-Ray: ACHI 97022-00 / SBS 97022-00-10; Pulp Vitality: 97061-00-00; OPG: 57960-00 / 57960-00-00)
- Periodontics: 97211-97282 (Root Planing: 97222-00-00)
- Oral Surgery: 97311-97399 (Simple extraction: 97311-00-00; Surgical with bone/sectioning: 97324-01-00)
- Endodontics: 97411-97499 (Pulp cap: 97411-00-00; Pulpotomy: 97414-00-00; Molar RCT: 97420-03-00)
- Restorative: 97511-97599 (Composite direct: 97521-97525 based on surface count)
- Crown & Bridge: 97611-97699 (Full crown: 97611-00-00; Core buildup: 97627-00-00; Post & Core: 97622-00-00)
- Implantology: Block 468/469 (Surgical fixture placement: 97681-00-00; Second-stage exposure: 97683-00-00; Surgical/Radiographic Stent: 97684-00-00; Implant-supported crown: 97671-00-00)
- Prosthodontics: 97711-97799 (Bimaxillary complete: 97719-00-00; Maxillary complete: 97721-00-00; Mandibular complete: 97722-00-00; Acrylic Partial: 97728-00-00; Cast Metal Partial: 97728-01-00)

FORMAT RULES (STRICT DIGIT VALIDATION):
- ACHI Code Column: MUST strictly be 7 digits: `XXXXX-XX` (e.g., 97728-00, 97022-00, 57960-00). NEVER write 9 digits here.
- SBS v3.0 Code Column: MUST strictly be 9 digits: `XXXXX-XX-XX` (e.g., 97728-00-00, 97022-00-10, 57960-00-00). NEVER use alphanumeric prefixes like DEN.* or RAD.*.

================================================================================
UNIVERSAL PRINCIPLE 5: ANTI-HALLUCINATION & MANDATORY BLANK PLACEHOLDERS
================================================================================
STRICT MEDICO-LEGAL SAFETY DIRECTIVE:
You are FORBIDDEN from guessing, suggesting, or pre-filling anatomical numbers, materials, or measurements not explicitly stated by the user. 
DO NOT supply example tooth numbers inside brackets. Keep placeholders strictly blank:
- Teeth: MUST be written as `[Specify Missing Teeth FDI: #___]` and `[Specify Abutment Teeth FDI: #___]`. NEVER suggest specific tooth numbers like #34 or #43.
- Classifications: `[Specify Kennedy Class: I / II / III / IV, Mod: ___]`, `[Specify Black's Class: I / II / III / IV / V]`.
- Measurements: `[Specify Probing Depth: ___ mm]`, `[Specify Bone Height: ___ mm]`, `[Specify Thickness: ___ µm]`.
- Materials: `[Specify Material: PVS / Polyether / Alginate]`, `[Specify Shade: VITA ___]`.

================================================================================
REQUIRED OUTPUT STRUCTURE
================================================================================
1. PRIMARY DIAGNOSIS & ETIOLOGY (ICD-10-AM 10th Ed)
   - Specific ICD-10-AM codes justified by clinical presentation. If site/cause is unspecified in prompt, provide the code with `[Specify Tooth/Arch]` placeholder.

2. BILLABLE CODING TABLE (SBS v3.0 & ACHI 10th Ed)
   - Table columns MUST strictly be:
     `Service Description` | `ACHI Code` | `SBS v3.0 Code` | `Claim Action Flag` | `Govt Tariff (SAR)* [Art. 11]` | `Bundled Elements (NON-BILLABLE)`
   - Tariff Column: Output realistic numeric statutory rates benchmarked to Article 11 (e.g., `75.00`, `250.00`, `1,400.00`). Do NOT write generic text like "Standard Rate".
   - Immediately below the table, include this exact mandatory statutory footnote:
     `*Tariff prices are determined in accordance with Article 11: "Dental services pricing in government sector".`
   - If mutually exclusive alternatives exist, output a separate small table below it titled:
     "⚠️ Mutually Exclusive Alternatives (Select Only One - Do NOT Bill Together)"

3. CLINICIAN'S RAPID PRE-FLIGHT CHECKLIST (CCHI / NPHIES)
   - Concise, single-line checkmarks:
     * [ ] **Anatomical Site:** Tooth / Arch identifier.
     * [ ] **Required Radiograph:** Mandatory imaging attachments.
     * [ ] **Clinical Justification:** Clear objective criteria.
     * [ ] **Prior Authorization:** Status under NPHIES rules.
     * [ ] **#1 Denial Trap:** Primary pitfall to avoid.

4. AUDIT-PROOF EMR SOAP CLINICAL PROGRESS NOTE
   - STRICT EMR FORMATTING CONSTRAINT: Do NOT include patient demographics (no Patient Name, MRN, Date of Service, Age, Gender brackets). Do NOT include doctor signature lines, provider credential blocks, SCFHS license numbers, or NPHIES provider IDs (hospital EMR systems generate all of these automatically upon signing).
   - Enforce Principle 5: Use bracketed placeholders `[Specify ...]` for any clinical finding, classification, measurement, tooth number, or material not supplied in the prompt.
   - The note MUST start directly with:
     **Encounter Specialty:** [e.g., Prosthodontics, Endodontics, Oral & Maxillofacial Surgery, Restorative Dentistry, Pediatric Dentistry, Periodontics]
   - Follow immediately with the clinical record:
     **SUBJECTIVE (S):**
     **OBJECTIVE (O):**
     **ASSESSMENT (A):**
     **PLAN & PROCEDURE (P):**
     **POST-OPERATIVE INSTRUCTIONS & FOLLOW-UP:**
"""

def generate_with_resilience(client, prompt):
    """Resilient caller handling demand spikes across active Flash versions."""
    models = ["gemini-3.7-flash", "gemini-3.6-flash"]
    last_error = None

    for model_name in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1,
                    )
                )
                return response.text
            except Exception as e:
                last_error = e
                err_text = str(e)
                if "503" in err_text or "429" in err_text:
                    time.sleep(2)
                    continue
                else:
                    break
    raise last_error

col_in, col_out = st.columns([1, 1], gap="large")

with col_in:
    st.subheader("📝 Clinician Input")
    doctor_input = st.text_area(
        "Enter clinical case summary (any specialty):",
        placeholder="e.g.:\n- second visit, missing lower posterior teeth case referred for acrylic RPD, before creating a replica surgical/radiographic guide to plan and refer for dental implants\n- trauma tooth 11, pulp exposure, vital pulp therapy\n- impacted wisdom tooth, cut bone and sectioned",
        height=200
    )
    submit_btn = st.button("🚀 Audit Case & Generate EMR Clinical Note", type="primary", use_container_width=True)

with col_out:
    st.subheader("📋 Audit & Coding Package")
    if submit_btn:
        if not api_key:
            st.error("Missing Gemini API Key.")
        elif not doctor_input.strip():
            st.warning("Please enter a case summary.")
        else:
            with st.spinner("Scrubbing claim against CCHI & SBS v3.0 rules..."):
                try:
                    client = genai.Client(api_key=api_key)
                    result_text = generate_with_resilience(client, doctor_input)
                    st.markdown(result_text)
                except Exception as e:
                    st.error(f"Service temporarily busy. Please tap again: {str(e)}")
