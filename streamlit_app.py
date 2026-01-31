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
DEFAULT_API_KEY = ""  # Add hardcoded API Key here if you don't want use secrets.toml file

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

def add_formation_bio_experience(data: Dict[str, Any], fb_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add Formation Bio experience as the first entry."""
    new_experience = {
        "company": "Formation Bio",
        "location": fb_data["location"],
        "role": fb_data["job_title"],
        "duration": fb_data["dates"],
        "responsibilities": fb_data["responsibilities"]
    }
    
    # Insert at the beginning
    data["experiences"].insert(0, new_experience)
    
    # Update position if this is their current role
    if "Present" in fb_data["dates"]:
        data["position"] = fb_data["job_title"]
    
    return data

# ────────────────────────────────────────────────────────────────
#  Authentication Functions
# ────────────────────────────────────────────────────────────────
def check_company_email():
    """Verify user has company email domain and password."""
    
    # Get company domain and password from secrets
    try:
        COMPANY_DOMAIN = st.secrets["company_domain"]
        APP_PASSWORD = st.secrets["app_password"]
    except:
        st.error("⚠️ Company domain or password not configured. Contact administrator.")
        st.stop()
    
    # Initialize authentication state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # If not authenticated, show login form
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
        if elapsed.total_seconds() > 1800:  # 30 minutes
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
                "Job Title and Department *",
                placeholder="e.g., Validation Manager, QA",
                key=f"job_title_{cv_index}"
            )
            
            dates = st.text_input(
                "Dates *",
                placeholder="MMM YYYY - Present (e.g., JAN 2024 - Present)",
                value="",
                key=f"dates_{cv_index}"
            )
        
        with col2:
            location = st.text_input(
                "Location",
                value="New York, NY",
                key=f"location_{cv_index}"
            )
        
        st.markdown("**Responsibilities (3-5 bullet points in present tense):**")
        
        resp1 = st.text_area("Responsibility 1 *", key=f"resp1_{cv_index}", height=70)
        resp2 = st.text_area("Responsibility 2 *", key=f"resp2_{cv_index}", height=70)
        resp3 = st.text_area("Responsibility 3 *", key=f"resp3_{cv_index}", height=70)
        resp4 = st.text_area("Responsibility 4 (Optional)", key=f"resp4_{cv_index}", height=70)
        resp5 = st.text_area("Responsibility 5 (Optional)", key=f"resp5_{cv_index}", height=70)
        
        submitted = st.form_submit_button("✅ Add Formation Bio Experience", use_container_width=True)
        
        if submitted:
            # Validation
            errors = []
            if not job_title.strip():
                errors.append("Job Title is required")
            if not dates.strip():
                errors.append("Dates are required")
            if not resp1.strip() or not resp2.strip() or not resp3.strip():
                errors.append("At least 3 responsibilities are required")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
                return None
            
            # Collect responsibilities
            responsibilities = [resp1.strip(), resp2.strip(), resp3.strip()]
            if resp4.strip():
                responsibilities.append(resp4.strip())
            if resp5.strip():
                responsibilities.append(resp5.strip())
            
            return {
                "job_title": job_title.strip(),
                "dates": dates.strip(),
                "location": location.strip(),
                "responsibilities": responsibilities
            }
    
    return None

# ────────────────────────────────────────────────────────────────
#  Main Application Function
# ────────────────────────────────────────────────────────────────
def main():
    # Check authentication first
    if not check_company_email():
        return
    
    # Check session timeout
    check_session_timeout()
    
    # Display header with user info
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📄 CV Company Template Converter")
        st.markdown("Effortlessly reformat candidate CVs into your company's standard template.")
    with col2:
        st.markdown(f"**Logged in as:**  \n{st.session_state.user_email}")
        if st.button("🚪 Logout"):
            # Clear session
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
    if 'processing_stage' not in st.session_state:
        st.session_state.processing_stage = 'upload'  # upload, check_formation, convert

    # Get API key from secrets
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
    
    # Show template loaded status
    st.success(f"✅ Company template loaded: {TEMPLATE_PATH}")
    
    # File upload - only CVs now
    cvs = st.file_uploader("Upload Candidate CV(s)", type=["pdf", "docx", "txt"],
                          accept_multiple_files=True)
    if cvs:
        st.info(f"📁 {len(cvs)} CV(s) uploaded")

    # Process button - Initial extraction
    if st.button("🔄 Process CVs", type="primary", disabled=not(api_key and cvs)):
        
        extractor = CVExtractor(api_key)
        
        # Load template from file
        with open(TEMPLATE_PATH, 'rb') as f:
            st.session_state.tpl_bytes = f.read()
        
        st.session_state.extracted_data = []
        st.session_state.pending_formation_bio = []

        prog = st.progress(0.0)
        status = st.empty()

        for i, cv in enumerate(cvs):
            status.text(f"Extracting data from {cv.name}...")
            
            try:
                # Extract text
                text = extract_text(cv)
                if not text:
                    st.warning(f"⚠️ Could not extract text from {cv.name}")
                    continue

                # Extract structured data
                with st.spinner(f"Analyzing {cv.name}..."):
                    data = extractor.extract(text)

                # Use filename if name extraction failed
                candidate_name = data.get("candidate_name", "")
                if not candidate_name or candidate_name == "Candidate Name Not Provided":
                    candidate_name = cv.name.replace('.pdf', '').replace('.docx', '').replace('.txt', '').replace('_', ' ').replace('-', ' ')
                    words_to_remove = ['resume', 'cv', 'curriculum', 'vitae', 'curriculumvitae']
                    for word in words_to_remove:
                        candidate_name = re.sub(r'\b' + word + r'\b', '', candidate_name, flags=re.IGNORECASE)
                    candidate_name = ' '.join(candidate_name.split()).strip()
                    data["candidate_name"] = candidate_name

                # Check for Formation Bio experience
                has_fb = has_formation_bio_experience(data)
                
                st.session_state.extracted_data.append({
                    "name": candidate_name,
                    "data": data,
                    "has_formation_bio": has_fb,
                    "index": i
                })
                
                if not has_fb:
                    st.session_state.pending_formation_bio.append(i)

                prog.progress((i + 1) / len(cvs))
                
            except Exception as e:
                st.error(f"❌ Error processing {cv.name}: {str(e)}")

        status.empty()
        prog.empty()
        
        # Move to Formation Bio check stage
        st.session_state.processing_stage = 'check_formation'
        st.rerun()

    # Formation Bio Check Stage
    if st.session_state.processing_stage == 'check_formation' and st.session_state.pending_formation_bio:
        st.markdown("---")
        st.markdown("## 🔍 Formation Bio Experience Check")
        
        # Show forms for CVs missing Formation Bio
        for idx in st.session_state.pending_formation_bio:
            cv_data = st.session_state.extracted_data[idx]
            
            with st.container():
                fb_data = show_formation_bio_form(cv_data["name"], idx)
                
                if fb_data:
                    # Add Formation Bio experience to data
                    updated_data = add_formation_bio_experience(cv_data["data"], fb_data)
                    st.session_state.extracted_data[idx]["data"] = updated_data
                    st.session_state.extracted_data[idx]["has_formation_bio"] = True
                    st.session_state.pending_formation_bio.remove(idx)
                    st.success(f"✅ Formation Bio experience added for {cv_data['name']}")
                    st.rerun()
                
                st.markdown("---")
        
    # Convert Stage - Show convert button only when all Formation Bio data is collected
    if st.session_state.processing_stage == 'check_formation' and not st.session_state.pending_formation_bio:
        st.success("✅ All Formation Bio information collected!")
        
        if st.button("📄 Generate Final CVs", type="primary", use_container_width=True):
            converted = []
            prog = st.progress(0.0)
            status = st.empty()
            
            for i, cv_data in enumerate(st.session_state.extracted_data):
                status.text(f"Generating CV for {cv_data['name']}...")
                
                try:
                    # Fill template
                    filled = fill_template(
                        Document(BytesIO(st.session_state.tpl_bytes)), 
                        cv_data["data"]
                    )

                    # Save to buffer
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
        
        # Option to download all as zip
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
                # Show extracted data summary
                data = conv['data']
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Extracted Information:**")
                    st.write(f"- Position: {data.get('position', 'N/A')}")
                    st.write(f"- Experience: {data.get('total_experience_years', 'N/A')} years")
                    st.write(f"- Email: {data.get('email', 'N/A')}")
                    st.write(f"- Phone: {data.get('phone', 'N/A')}")
                
                with col2:
                    st.markdown("**Experience Summary:**")
                    actual_experiences = [exp for exp in data.get('experiences', []) 
                                        if exp.get('company') and exp.get('company') != 'N/A']
                    st.write(f"Total experiences: {len(actual_experiences)}")
                    for exp_idx, exp in enumerate(actual_experiences[:3]):
                        st.write(f"{exp_idx+1}. {exp['company']} - {exp.get('role', '')}")
                
                # Download button
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