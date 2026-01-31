# CV Converter

AI-powered CV template converter for Formation Bio.

## Features
- Automatic CV data extraction using OpenAI
- Formation Bio experience validation and addition
- Converts CVs to company template format
- Batch processing support
- Hardcoded company template (no upload needed)

## Setup

1. Clone the repository
2. Install Python 3.11
3. Create virtual environment: `python3.11 -m venv venv`
4. Activate: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Configure secrets in `.streamlit/secrets.toml`
7. Run: `streamlit run cv_converter.py`

## Configuration

Create `.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-proj-..."
company_domain = "@formationbio.com"
app_password = "your-team-password"
```

⚠️ **Never commit this file - it's in .gitignore**

## Usage

1. Login with Formation Bio email
2. Upload candidate CV(s)
3. If Formation Bio experience missing, fill in the form
4. Download formatted CVs
