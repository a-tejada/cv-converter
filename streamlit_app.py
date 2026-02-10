# ────────────────────────────────────────────────────────────────
#  Libraries
# ────────────────────────────────────────────────────────────────
import os, re, json, time
from io import BytesIO
from typing import Dict, Any, List
from datetime import datetime
import streamlit as st
import PyPDF2
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pdfplumber
from utils import *
from extraction import CVExtractor

# ────────────────────────────────────────────────────────────────
#  Page Configuration
# ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CV Converter", 
    page_icon="📄", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ────────────────────────────────────────────────────────────────
#  Configuration
# ────────────────────────────────────────────────────────────────
DEFAULT_API_KEY = ""

# ────────────────────────────────────────────────────────────────
#  Helper Functions
# ────────────────────────────────────────────────────────────────
def has_formation_bio_experience(data: Dict[str, Any]) -> bool:
    """Check if candidate has Formation Bio in their work experience."""
    experiences = data.get("experiences", [])
    for exp in experiences:
        company = exp.get("company", "").lower()
        if "formation" in company and "bio" in company:
            return True
    return False

def has_education(data: Dict[str, Any]) -> bool:
    """Check if candidate has education entries."""
    education = data.get("education", [])
    return len(education) > 0 and any(edu.get("degree") or edu.get("institution") for edu in education)

def add_formation_bio_experience(data: Dict[str, Any], fb_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add Formation Bio experience as the first entry."""
    # Parse responsibilities from text area (split by newlines, filter empty)
    responsibilities = [r.strip() for r in fb_data["responsibilities"].split('\n') if r.strip()]
    
    new_experience = {
        "company": "Formation Bio",
        "location": fb_data["location"],
        "role": fb_data["job_title"],
        "duration": f"{fb_data['start_date']} - Present",
        "responsibilities": responsibilities
    }
    
    data["experiences"].insert(0, new_experience)
    data["position"] = fb_data["job_title"]
    
    return data

def add_education(data: Dict[str, Any], edu_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add education entry."""
    new_education = {
        "institution": edu_data["institution"],
        "duration": edu_data.get("duration", ""),
        "degree": edu_data["degree"]
    }
    
    if "education" not in data:
        data["education"] = []
    
    data["education"].append(new_education)
    
    return data

# ────────────────────────────────────────────────────────────────
#  Authentication Functions
# ────────────────────────────────────────────────────────────────
def check_company_email():
    """Verify user has company email domain and password."""
    try:
        COMPANY_DOMAIN = st.secrets["company_domain"]
        APP_PASSWORD = st.secrets["app_password"]
    except:
        st.error("⚠️ Company domain or password not configured. Contact administrator.")
        st.stop()
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("## 🔐 CV Converter Login Page")
        st.markdown("Please authenticate with your company email and password to access the CV converter.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            email = st.text_input("Enter your company email address:", 
                                placeholder=f"yourname{COMPANY_DOMAIN}")
            password = st.text_input("Enter password:", type="password")
            
            if st.button("Access CV Converter", type="primary", use_container_width=True):
                if email.lower().endswith(COMPANY_DOMAIN.lower()) and password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.login_time = datetime.now()
                    
                    st.success(f"✅ Welcome {email}!")
                    st.rerun()
                else:
                    if not email.lower().endswith(COMPANY_DOMAIN.lower()):
                        st.error(f"❌ Access restricted to {COMPANY_DOMAIN} emails only")
                    else:
                        st.error("❌ Invalid password")
                    
        st.markdown("---")
        st.caption("This tool is for authorized personnel only. Unauthorized access is prohibited.")
        
    return st.session_state.authenticated

def check_session_timeout():
    """Check if session has timed out (30 minutes)."""
    if "login_time" in st.session_state:
        elapsed = datetime.now() - st.session_state.login_time
        if elapsed.total_seconds() > 1800:
            st.warning("⏱️ Session expired. Please login again.")
            for key in ["authenticated", "user_email", "login_time"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

# ────────────────────────────────────────────────────────────────
#  Formation Bio Experience Input Form
# ────────────────────────────────────────────────────────────────
def show_formation_bio_form(cv_name: str, cv_index: int) -> Dict[str, Any]:
    """Show form to collect Formation Bio experience details."""
    
    st.warning(f"⚠️ **{cv_name}**: No Formation Bio experience found in resume.")
    st.markdown("### Add Formation Bio Experience")
    st.markdown("Please provide the candidate's Formation Bio role details:")
    
    form_key = f"fb_form_{cv_index}"
    
    with st.form(key=form_key):
        col1, col2 = st.columns(2)
        
        with col1:
            job_title = st.text_input(
                "Job Title *",
                placeholder="e.g., Validation Manager",
                key=f"job_title_{cv_index}"
            )
            
            department = st.text_input(
                "Department *",
                placeholder="e.g., QA",
                key=f"department_{cv_index}"
            )
            
            start_date = st.text_input(
                "Start Date *",
                placeholder="MMM YYYY (e.g., JAN 2024)",
                key=f"start_date_{cv_index}"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value="New York, NY",
                key=f"location_{cv_index}"
            )
        
        st.markdown("---")
        st.markdown("**Responsibilities (in present tense):**")
        st.caption("Enter each responsibility on a new line. Start with '•' or '-' for bullet points.")
        
        responsibilities = st.text_area(
            "Responsibilities *",
            value=default_resp,
            height=200,
            placeholder="• Lead validation efforts for GxP systems\n• Develop and maintain validation documentation\n• Coordinate with cross-functional teams",
            key=f"responsibilities_{cv_index}"
        )
        
        submitted = st.form_submit_button("✅ Add Formation Bio Experience", use_container_width=True)
        
        if submitted:
            # Validation
            errors = []
            if not job_title.strip():
                errors.append("Job Title is required")
            if not department.strip():
                errors.append("Department is required")
            if not start_date.strip():
                errors.append("Start Date is required")
            if not responsibilities.strip() or len([r for r in responsibilities.split('\n') if r.strip()]) < 3:
                errors.append("At least 3 responsibilities are required")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
                return None
            
            # Format start date to match template style (MMM YYYY)
            formatted_date = format_date(start_date.strip())
            
            return {
                "job_title": f"{job_title.strip()}, {department.strip()}",
                "start_date": formatted_date,
                "location": location.strip(),
                "responsibilities": responsibilities.strip()
            }
    
    return None

# ────────────────────────────────────────────────────────────────
#  Education Input Form
# ────────────────────────────────────────────────────────────────
def show_education_form(cv_name: str, cv_index: int) -> Dict[str, Any]:
    """Show form to collect education details."""
    
    st.warning(f"⚠️ **{cv_name}**: No education found in resume.")
    st.markdown("### Add Education")
    st.markdown("Please provide the candidate's education details:")
    
    form_key = f"edu_form_{cv_index}"
    
    with st.form(key=form_key):
        institution = st.text_input(
            "Institution *",
            placeholder="e.g., University of Massachusetts Dartmouth",
            key=f"institution_{cv_index}"
        )
        
        degree = st.text_input(
            "Degree *",
            placeholder="e.g., Bachelor of Science: Marine Concentration",
            key=f"degree_{cv_index}"
        )
        
        duration = st.text_input(
            "Duration (Optional)",
            placeholder="e.g., 2015 - 2019 or SEP 2015 - MAY 2019",
            key=f"duration_{cv_index}"
        )
        
        submitted = st.form_submit_button("✅ Add Education", use_container_width=True)
        
        if submitted:
            errors = []
            if not institution.strip():
                errors.append("Institution is required")
            if not degree.strip():
                errors.append("Degree is required")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
                return None
            
            return {
                "institution": institution.strip(),
                "degree": degree.strip(),
                "duration": format_duration(duration.strip()) if duration.strip() else ""
            }
    
    return None

# ────────────────────────────────────────────────────────────────
#  Main Application Function
# ────────────────────────────────────────────────────────────────
def main():
    if not check_company_email():
        return
    
    check_session_timeout()
    
    # Display header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📄 Formation Bio CV Formatter")
        st.markdown("Upload your CV/Resume to automatically reformat it into the standard Formation Bio template. Note: The tool can make errors, always review the output and make any necessary edits before finalizing your document as PDF. Once complete, to upload your final version to ComplianceWire.")
    with col2:
        st.markdown(f"**Logged in as:**  \n{st.session_state.user_email}")
        if st.button("🚪 Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Initialize session state
    if 'converted_cvs' not in st.session_state:
        st.session_state.converted_cvs = []
    if 'conversion_done' not in st.session_state:
        st.session_state.conversion_done = False
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = []
    if 'pending_formation_bio' not in st.session_state:
        st.session_state.pending_formation_bio = []
    if 'pending_education' not in st.session_state:
        st.session_state.pending_education = []
    if 'processing_stage' not in st.session_state:
        st.session_state.processing_stage = 'upload'

    # Get API key
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        if DEFAULT_API_KEY:
            api_key = DEFAULT_API_KEY
        else:
            st.error("⚠️ API key not configured. Contact administrator.")
            st.stop()

    # Load hardcoded template
    TEMPLATE_PATH = "company_template.docx"
    
    if not os.path.exists(TEMPLATE_PATH):
        st.error(f"⚠️ Template file not found: {TEMPLATE_PATH}")
        st.info("Please add 'company_template.docx' to the project folder.")
        st.stop()
    
    # File upload - only CVs
    cvs = st.file_uploader("Upload Candidate CV(s)", type=["pdf", "docx", "txt"],
                          accept_multiple_files=True)
    if cvs:
        st.info(f"📁 {len(cvs)} CV(s) uploaded")

    # Process button
    if st.button("🔄 Process CVs", type="primary", disabled=not(api_key and cvs)):
        
        extractor = CVExtractor(api_key)
        
        with open(TEMPLATE_PATH, 'rb') as f:
            st.session_state.tpl_bytes = f.read()
        
        st.session_state.extracted_data = []
        st.session_state.pending_formation_bio = []
        st.session_state.pending_education = []

        prog = st.progress(0.0)
        status = st.empty()

        for i, cv in enumerate(cvs):
            status.text(f"Extracting data from {cv.name}...")
            
            try:
                text = extract_text(cv)
                if not text:
                    st.warning(f"⚠️ Could not extract text from {cv.name}")
                    continue

                with st.spinner(f"Analyzing {cv.name}..."):
                    data = extractor.extract(text)

                candidate_name = data.get("candidate_name", "")
                if not candidate_name or candidate_name == "Candidate Name Not Provided":
                    candidate_name = cv.name.replace('.pdf', '').replace('.docx', '').replace('.txt', '').replace('_', ' ').replace('-', ' ')
                    words_to_remove = ['resume', 'cv', 'curriculum', 'vitae', 'curriculumvitae']
                    for word in words_to_remove:
                        candidate_name = re.sub(r'\b' + word + r'\b', '', candidate_name, flags=re.IGNORECASE)
                    candidate_name = ' '.join(candidate_name.split()).strip()
                    data["candidate_name"] = candidate_name

                has_fb = has_formation_bio_experience(data)
                has_edu = has_education(data)
                
                st.session_state.extracted_data.append({
                    "name": candidate_name,
                    "data": data,
                    "has_formation_bio": has_fb,
                    "has_education": has_edu,
                    "index": i
                })
                
                if not has_fb:
                    st.session_state.pending_formation_bio.append(i)
                if not has_edu:
                    st.session_state.pending_education.append(i)

                prog.progress((i + 1) / len(cvs))
                
            except Exception as e:
                st.error(f"❌ Error processing {cv.name}: {str(e)}")

        status.empty()
        prog.empty()
        
        st.session_state.processing_stage = 'check_requirements'
        st.rerun()

    # Check Requirements Stage
    if st.session_state.processing_stage == 'check_requirements':
        
        # Formation Bio Check
        if st.session_state.pending_formation_bio:
            st.markdown("---")
            st.markdown("## 🔍 Formation Bio Experience Check")
            
            for idx in st.session_state.pending_formation_bio[:]:
                cv_data = st.session_state.extracted_data[idx]
                
                with st.container():
                    fb_data = show_formation_bio_form(cv_data["name"], idx)
                    
                    if fb_data:
                        updated_data = add_formation_bio_experience(cv_data["data"], fb_data)
                        st.session_state.extracted_data[idx]["data"] = updated_data
                        st.session_state.extracted_data[idx]["has_formation_bio"] = True
                        st.session_state.pending_formation_bio.remove(idx)
                        st.success(f"✅ Formation Bio experience added for {cv_data['name']}")
                        st.rerun()
                    
                    st.markdown("---")
        
        # Education Check
        if not st.session_state.pending_formation_bio and st.session_state.pending_education:
            st.markdown("---")
            st.markdown("## 🎓 Education Check")
            
            for idx in st.session_state.pending_education[:]:
                cv_data = st.session_state.extracted_data[idx]
                
                with st.container():
                    edu_data = show_education_form(cv_data["name"], idx)
                    
                    if edu_data:
                        updated_data = add_education(cv_data["data"], edu_data)
                        st.session_state.extracted_data[idx]["data"] = updated_data
                        st.session_state.extracted_data[idx]["has_education"] = True
                        st.session_state.pending_education.remove(idx)
                        st.success(f"✅ Education added for {cv_data['name']}")
                        st.rerun()
                    
                    st.markdown("---")
        
        # All requirements met
        if not st.session_state.pending_formation_bio and not st.session_state.pending_education:
            st.success("✅ All required information collected!")
            
            if st.button("📄 Generate Final CVs", type="primary", use_container_width=True):
                converted = []
                prog = st.progress(0.0)
                status = st.empty()
                
                for i, cv_data in enumerate(st.session_state.extracted_data):
                    status.text(f"Generating CV for {cv_data['name']}...")
                    
                    try:
                        filled = fill_template(
                            Document(BytesIO(st.session_state.tpl_bytes)), 
                            cv_data["data"]
                        )

                        buf = BytesIO()
                        filled.save(buf)
                        buf.seek(0)

                        converted.append({
                            "name": cv_data["name"],
                            "buffer": buf,
                            "data": cv_data["data"]
                        })

                        prog.progress((i + 1) / len(st.session_state.extracted_data))
                        
                    except Exception as e:
                        st.error(f"❌ Error generating CV for {cv_data['name']}: {str(e)}")

                status.empty()
                prog.empty()
                
                st.session_state.converted_cvs = converted
                st.session_state.conversion_done = True
                st.session_state.processing_stage = 'complete'
                st.rerun()

    # Display results
    if st.session_state.conversion_done and st.session_state.converted_cvs:
        st.markdown("---")
        st.markdown("### 📥 Download Converted CVs")
        
        # Download all as zip
        if len(st.session_state.converted_cvs) > 1:
            if st.button("📦 Download All as ZIP", type="secondary"):
                import zipfile
                zip_buffer = BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for conv in st.session_state.converted_cvs:
                        fname = safe_filename(f"{conv['name']}_Formatted.docx")
                        zip_file.writestr(fname, conv['buffer'].getvalue())
                
                zip_buffer.seek(0)
                st.download_button(
                    "⬇️ Download ZIP Archive",
                    zip_buffer.getvalue(),
                    file_name="converted_cvs.zip",
                    mime="application/zip"
                )
        
        # Individual CV downloads
        for idx, conv in enumerate(st.session_state.converted_cvs):
            with st.expander(f"📄 {conv['name']}", expanded=True):
                data = conv['data']
                
                st.markdown(f"**Current Position:** {data.get('position', 'N/A')}")
                st.markdown(f"**Total Experience:** {data.get('total_experience_years', 'N/A')} years")
                
                fname = safe_filename(f"{conv['name']}_Formatted.docx")
                st.download_button(
                    f"⬇️ Download {fname}",
                    conv['buffer'].getvalue(),
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_{idx}"
                )

if __name__ == "__main__":
    main()