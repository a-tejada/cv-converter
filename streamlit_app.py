# ────────────────────────────────────────────────────────────────
#  Libraries
# ────────────────────────────────────────────────────────────────
import os, re
from io import BytesIO
from typing import Dict, Any, List
import streamlit as st
import streamlit_authenticator as stauth
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
    responsibilities = [r.strip() for r in fb_data["responsibilities"].split('\n') if r.strip()]
    
    new_experience = {
        "company": "Formation Bio",
        "location": fb_data["location"],
        "role": fb_data["job_title"],
        "duration": f"{fb_data['start_date']} to Present",
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
def _hash_password(password: str) -> str:
    if hasattr(stauth.Hasher, "hash"):
        return stauth.Hasher.hash(password)
    return stauth.Hasher([password]).generate()[0]

def _logout_with_compat(authenticator, label: str, key: str):
    try:
        return authenticator.logout(label, "main", key=key)
    except TypeError:
        return authenticator.logout(location="main", key=key)

def _normalize_company_domain(raw_domain: str) -> str:
    domain = raw_domain.strip().lower()
    return domain if domain.startswith("@") else f"@{domain}"

def _is_company_email(email: str, company_domain: str) -> bool:
    return email.lower().strip().endswith(company_domain)

def _seed_user_credentials(credentials: Dict[str, Any], email: str, hashed_password: str) -> None:
    user_email = email.lower().strip()
    credentials["usernames"][user_email] = {
        "name": user_email.split("@")[0],
        "email": user_email,
        "password": hashed_password,
    }

def _force_logout(authenticator) -> None:
    """Immediately clear auth session and cookie."""
    try:
        authenticator.authentication_controller.logout()
    except Exception:
        pass
    try:
        authenticator.cookie_controller.delete_cookie()
    except Exception:
        pass
    for key in ["authentication_status", "username", "name", "email", "roles", "user_email", "user_name"]:
        if key in st.session_state:
            del st.session_state[key]

def check_company_email():
    """Authenticate any company-domain email with shared password + cookie persistence."""
    try:
        company_domain = _normalize_company_domain(st.secrets["company_domain"])
        app_password = st.secrets["app_password"]
        auth_cookie_key = st.secrets["auth_cookie_key"]
        auth_cookie_name = st.secrets.get("auth_cookie_name", "cv_converter_auth")
        auth_cookie_expiry_days = float(st.secrets.get("auth_cookie_expiry_days", 7))
    except Exception:
        st.error("⚠️ Authentication settings not configured. Contact administrator.")
        st.stop()

    credentials = {"usernames": {}}
    hashed_password = _hash_password(app_password)

    authenticator = stauth.Authenticate(
        credentials,
        auth_cookie_name,
        auth_cookie_key,
        auth_cookie_expiry_days,
    )

    token = authenticator.cookie_controller.get_cookie()
    token_username = (token or {}).get("username", "").lower().strip() if isinstance(token, dict) else ""
    if token_username and _is_company_email(token_username, company_domain):
        _seed_user_credentials(credentials, token_username, hashed_password)
        try:
            authenticator.authentication_controller.login(token=token)
        except Exception:
            _force_logout(authenticator)
    elif token_username:
        _force_logout(authenticator)

    if st.session_state.get("authentication_status"):
        user_email = (st.session_state.get("username") or "").lower().strip()
        if _is_company_email(user_email, company_domain):
            st.session_state.user_email = user_email
            st.session_state.user_name = st.session_state.get("name") or user_email.split("@")[0]
            return authenticator
        st.error(f"❌ Access restricted to {company_domain} emails only")
        _force_logout(authenticator)
        return None

    st.markdown("## 🔐 CV Converter Login Page")
    st.markdown("Please authenticate with your company email and password to access the CV converter.")
    with st.form("domain_auth_form"):
        email = st.text_input("Company Email", placeholder=f"you{company_domain}")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Access CV Converter", type="primary", use_container_width=True)

    if submitted:
        clean_email = email.lower().strip()
        if not _is_company_email(clean_email, company_domain):
            st.error(f"❌ Access restricted to {company_domain} emails only")
        elif password != app_password:
            st.error("❌ Invalid email or password")
        else:
            _seed_user_credentials(credentials, clean_email, hashed_password)
            if authenticator.authentication_controller.login(clean_email, password):
                authenticator.cookie_controller.set_cookie()
                st.session_state.user_email = clean_email
                st.session_state.user_name = clean_email.split("@")[0]
                st.rerun()
            else:
                st.error("❌ Invalid email or password")
    else:
        st.info("Please enter your credentials.")

    st.markdown("---")
    st.caption("This tool is for authorized personnel only. Unauthorized access is prohibited.")
    return None

# ────────────────────────────────────────────────────────────────
#  Formation Bio Experience Input Form
# ────────────────────────────────────────────────────────────────
def show_formation_bio_form(cv_name: str, cv_index: int) -> Dict[str, Any]:
    """Show form to collect Formation Bio experience details."""
    
    st.markdown("### Add Formation Bio Experience")
    st.markdown(f"**{cv_name}** - Please provide your Formation Bio role details:")
    
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
            height=200,
            placeholder="• Lead validation efforts for GxP systems\n• Develop and maintain validation documentation\n• Coordinate with cross-functional teams",
            key=f"responsibilities_{cv_index}"
        )
        
        submitted = st.form_submit_button("✅ Add Formation Bio Experience", use_container_width=True)
        
        if submitted:
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
    
    st.markdown("### Add Education")
    st.markdown(f"**{cv_name}** - Please provide your education details:")
    
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
    authenticator = check_company_email()
    if not authenticator:
        return
    
    # Display header
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("📄 Formation Bio CV Formatter")
        st.markdown("### Format your CV to Formation Bio's template for ComplianceWire")
    with col2:
        _logout_with_compat(authenticator, "🚪 Logout", "logout_button")
        st.caption(f"👤 {st.session_state.user_email.split('@')[0]}")
    
    st.markdown("---")
    
    # Instructions
    with st.expander("ℹ️ How to use this tool", expanded=False):
        st.markdown("""
        **Step-by-step guide:**
        
        1. **Upload** your CV file (PDF, DOCX, or TXT)
        2. **Review** your name and correct if needed
        3. **Add Formation Bio role** if it's not on your CV yet
        4. **Add education** if missing from your CV
        5. **Download** your formatted CV and upload to ComplianceWire
        
        **Important:** Always review the output before uploading to ComplianceWire. The tool uses AI and may make errors.
        """)
    
    st.markdown("")

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
    st.markdown("### 📤 Step 1: Upload Your CV")
    cvs = st.file_uploader(
        "Select your CV file (or multiple if processing for your team)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="Upload PDF, DOCX, or TXT files."
    )
    
    if cvs:
        st.success(f"✅ {len(cvs)} file(s) uploaded: {', '.join([cv.name for cv in cvs])}")
    else:
        st.info("👆 Upload your CV file to begin")

    # Process button
    st.markdown("")
    if st.button("🔄 Process CVs", type="primary", disabled=not(api_key and cvs), use_container_width=True):
        
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
                
                data["extracted_name"] = candidate_name

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

    # Check Requirements Stage - Name Review
    if st.session_state.processing_stage == 'check_requirements':
        
        st.markdown("---")
        st.markdown("### ✏️ Step 2: Review Names")
        st.markdown("Verify the AI extracted the correct name. Edit if needed:")
        
        st.markdown("")
        
        name_changes = {}
        for idx, cv_data in enumerate(st.session_state.extracted_data):
            with st.container():
                st.markdown(f"**Employee #{idx + 1}**")
                col1, col2 = st.columns([3, 2])
                with col1:
                    corrected_name = st.text_input(
                        "Full Name",
                        value=cv_data["name"],
                        key=f"name_correction_{idx}",
                        label_visibility="collapsed",
                        help="Edit the full name if needed (First Last)"
                    )
                    if corrected_name != cv_data["name"]:
                        name_changes[idx] = corrected_name
                with col2:
                    st.caption(f"AI extracted: {cv_data.get('data', {}).get('extracted_name', cv_data['name'])}")
                st.markdown("")
        
        col1, col2 = st.columns(2)
        with col1:
            if name_changes and st.button("💾 Save Name Changes", use_container_width=True):
                for idx, new_name in name_changes.items():
                    st.session_state.extracted_data[idx]["name"] = new_name
                    st.session_state.extracted_data[idx]["data"]["candidate_name"] = new_name
                st.success("✅ Names updated!")
                st.rerun()
        
        with col2:
            if st.button("Continue to Next Step →", type="primary", use_container_width=True):
                st.session_state.processing_stage = 'check_formation_bio'
                st.rerun()
    
    # Formation Bio Check Stage
    if st.session_state.processing_stage == 'check_formation_bio':
        
        if st.session_state.pending_formation_bio:
            st.markdown("---")
            st.markdown("### 🏢 Step 3: Add Your Formation Bio Role")
            st.markdown("Add your Formation Bio experience:")
            st.markdown("")
            
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
        
        if not st.session_state.pending_formation_bio and st.session_state.pending_education:
            st.markdown("---")
            st.markdown("### 🎓 Step 4: Add Your Education")
            st.markdown("Add your education information:")
            st.markdown("")
            
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
        
        if not st.session_state.pending_formation_bio and not st.session_state.pending_education:
            st.markdown("---")
            st.success("✅ All information collected!")
            st.markdown("### 📄 Step 5: Generate Formatted CVs")
            st.markdown("Ready to create the formatted CVs with Formation Bio template.")
            st.markdown("")
            
            if st.button("🚀 Generate CVs", type="primary", use_container_width=True):
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
        st.markdown("### ✅ Success! Your CVs are Ready")
        st.markdown(f"**{len(st.session_state.converted_cvs)} CV(s) formatted and ready to download**")
        st.markdown("")
        
        if len(st.session_state.converted_cvs) > 1:
            st.markdown("**Download all CVs at once:**")
            if st.button("📦 Download All as ZIP", type="secondary", use_container_width=True):
                import zipfile
                zip_buffer = BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for conv in st.session_state.converted_cvs:
                        fname = safe_filename(f"{conv['name']}_Formatted.docx")
                        zip_file.writestr(fname, conv['buffer'].getvalue())
                
                zip_buffer.seek(0)
                st.download_button(
                    "⬇️ Click Here to Download ZIP",
                    zip_buffer.getvalue(),
                    file_name="formation_bio_cvs.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            st.markdown("---")
        
        st.markdown("**Download individual CVs:**")
        for idx, conv in enumerate(st.session_state.converted_cvs):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"**{idx + 1}. {conv['name']}**")
            
            with col2:
                fname = safe_filename(f"{conv['name']}_Formatted.docx")
                st.download_button(
                    "⬇️ Download",
                    conv['buffer'].getvalue(),
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_{idx}",
                    use_container_width=True
                )
        
        st.markdown("")
        st.info("💡 **Next Steps:** Review the downloaded CVs and upload final versions to ComplianceWire.")

if __name__ == "__main__":
    main()
