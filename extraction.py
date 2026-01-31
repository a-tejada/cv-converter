# extraction.py
# AI-powered CV data extraction using OpenAI

import re
import json
from typing import Dict, Any
import streamlit as st
from openai import OpenAI
from utils import format_name, format_duration

# ────────────────────────────────────────────────────────────────
#  Enhanced OpenAI wrapper for comprehensive extraction
# ────────────────────────────────────────────────────────────────
class CVExtractor:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Fast and cost-effective, or use "gpt-4o" for better quality

    def extract(self, cv_text: str) -> Dict[str, Any]:
        prompt = f"""Extract comprehensive information from this CV and return as JSON.

CRITICAL INSTRUCTIONS:
1. CRITICAL - Extract the candidate's FULL NAME from the CV:
   - The name is usually at the very top of the CV, often in large or bold text
   - This is the PERSON'S NAME (e.g., "Jane DOE", "John Smith", "Maria Garcia")
   - This is NOT their job title (e.g., "Quality Systems Manager", "Senior Engineer")
   - If you cannot find a name, look for:
     * Text near the top that looks like a personal name
     * Name before contact information (phone/email)
     * Name in header section
   - If truly no name is found, use "Candidate Name Not Provided"
   - DO NOT use job titles, positions, or company names as the candidate name
2. Extract ALL experiences (up to 20, most recent first)
3. IMPORTANT: Each role is a SEPARATE experience, even if at the same company:
   - If someone had "Manager Role A" (2023-2025) and "Specialist Role B" (2021-2023) at Company X, create TWO separate experience entries
   - Do NOT consolidate multiple roles at the same company into one entry
   - Do NOT use "Project Name: [Name], Location: [Location], Duration: [Start - End]" format
   - Each role should have its own company, location, role, duration, and responsibilities listed separately
4. For each experience, you MUST include:
   - Company name: Just the company name, no location appended (e.g., "Formation Bio")
   - Location: Separate field for city, state, and/or country (e.g., "New York, NY")
     * Look for location in company line, job title line, or anywhere in the experience section
     * Location can be city, country, or both (e.g., "Dubai", "Sharjah", "Dubai, UAE", "Delhi, India")
     * If location is split (e.g., "Dubai" on one line, "UAE" on another), combine them as "Dubai, UAE"
   - Job title/role (in proper case, not ALL CAPS)
   - Duration: Use the date format provided (e.g., "MAY 2025 - Present" or "OCT 2021 - JAN 2025")
   - Responsibilities: 
     * List responsibilities directly for each role
     * Extract EVERY responsibility mentioned
     * If there's an "Environment:" or "Technologies:" or "Versions:" section, add it as the LAST bullet point
     * Format environment info as: "Environment/Technologies: [list all tools, versions, technologies mentioned]"
     * Do NOT add bullet points - they will be added by the template
5. Extract ALL technical skills comprehensively
6. Extract ALL certifications with their FULL names and IDs if mentioned
7. If no professional summary exists, create one based on the CV content
8. For candidate name, use proper case (e.g., "Jane Doe" not "JANE DOE")
9. For position/role, use proper case (e.g., "Quality Systems Manager" not "QUALITY SYSTEMS MANAGER")
10. For education, extract as structured data:
    - Institution: University/college name only
    - Duration: Years if mentioned (e.g., "2015 to 2019"), empty if not available
    - Degree: Full degree with major (e.g., "Bachelor of Science: Marine Concentration")
    - List PhD/MD first, then graduate degrees, then undergraduate
11. For certifications, extract as structured data:
    - Name: Full certificate name
    - Year: Year obtained (YYYY format)
    - Provider: Issuing organization/institution
    - Location: City, State if mentioned, empty if not available

Return this exact JSON structure:
{{
  "candidate_name": "Full name in proper case (THE PERSON'S NAME, not their job title)",
  "position": "Current or most recent job title in proper case",
  "education": [
    {{
      "institution": "University name only",
      "duration": "MMM YYYY to MMM YYYY (if available, otherwise empty string)",
      "degree": "Degree type: Major/Concentration"
    }}
  ],
  "total_experience_years": "Number only (e.g., 11)",
  "phone": "Phone number with country code if present",
  "email": "Email address",
  "intro_paragraph": "Professional summary add as many sentences as available in CV in paragraph format, word it in a structured manner, summarize if needed.",
  "experiences": [
    {{
      "company": "Company name only (no location here)",
      "location": "City, State or City, Country (separate from company)",
      "role": "Job title in proper case",
      "duration": "MMM YYYY - MMM YYYY (or Present)",
      "responsibilities": [
        "First responsibility",
        "Second responsibility",
        "All other responsibilities",
        "Environment: Oracle 19c/12c, SQL * Plus, TOAD, SQL*Loader, SQL Developer, Shell Scripts, UNIX, Windows 10"
      ]
    }}
  ],
  "technical_skills": ["List ALL technical skills mentioned"],
  "certifications": [
    {{
      "name": "Certificate name",
      "year": "YYYY",
      "provider": "Issuing organization",
      "location": "City, State (if available, otherwise empty string)"
    }}
  ],
  "language_skills": ["Language - Proficiency level"]
}}

CV TEXT:
{cv_text}

RETURN ONLY THE JSON:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert CV parser that extracts structured data from resumes. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}  # Ensures JSON response
            )
            
            raw = response.choices[0].message.content
            
            # Extract JSON
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return self._validate_data(data)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            st.warning(f"⚠️ Extraction error: {str(e)}")
            return self._get_empty_data()        

    def _validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure data structure is complete and properly formatted."""
        # Placeholder for candidate name if not found (will be overridden by filename later)
        if not data.get("candidate_name") or data.get("candidate_name") == "Candidate Name Not Provided":
            data["candidate_name"] = "Candidate Name Not Provided"
        # Format candidate name and position
        if "candidate_name" in data:
            data["candidate_name"] = format_name(data["candidate_name"])
        
        if "position" in data:
            data["position"] = format_name(data["position"])
        
        # Default language skills if not found
        if "language_skills" not in data or not data["language_skills"]:
            data["language_skills"] = ["English - Fluent"]
        
        # Ensure experiences exist and have proper structure
        if "experiences" not in data:
            data["experiences"] = []
        
        # Format existing experiences
        for i, exp in enumerate(data["experiences"]):
            if "role" in exp:
                exp["role"] = format_name(exp["role"])
            if "duration" in exp:
                # Special handling for first experience
                exp["duration"] = format_duration(exp["duration"], is_first_experience=(i == 0))
        
        # Ensure each experience has all fields
        for exp in data["experiences"]:
            if "company" not in exp or not exp["company"]:
                exp["company"] = ""
            if "role" not in exp or not exp["role"]:
                exp["role"] = ""
            if "duration" not in exp or not exp["duration"]:
                exp["duration"] = ""
            if "responsibilities" not in exp or not isinstance(exp["responsibilities"], list):
                exp["responsibilities"] = []
        
        # Ensure education exists and has proper structure
        if "education" not in data:
            data["education"] = []
        
        if not isinstance(data["education"], list):
            # If education is a string (old format), convert to list
            data["education"] = []
        
        # Ensure each education entry has all fields and format duration
        for edu in data["education"]:
            if "institution" not in edu or not edu["institution"]:
                edu["institution"] = ""
            if "duration" not in edu or not edu["duration"]:
                edu["duration"] = ""
            else:
                # Format education duration like work experience
                edu["duration"] = format_duration(edu["duration"])
            if "degree" not in edu or not edu["degree"]:
                edu["degree"] = ""
        
        # Ensure certifications exist and have proper structure
        if "certifications" not in data:
            data["certifications"] = []
        
        if not isinstance(data["certifications"], list):
            # If certifications is a string (old format), convert to list
            data["certifications"] = []
        
        # Ensure each certification has all fields
        for cert in data["certifications"]:
            if "name" not in cert or not cert["name"]:
                cert["name"] = ""
            if "year" not in cert or not cert["year"]:
                cert["year"] = ""
            if "provider" not in cert or not cert["provider"]:
                cert["provider"] = ""
            if "location" not in cert or not cert["location"]:
                cert["location"] = ""
            
        return data

    def _get_empty_data(self) -> Dict[str, Any]:
        return {
            "candidate_name": "",
            "position": "",
            "education": [],
            "total_experience_years": "",
            "phone": "",
            "email": "",
            "intro_paragraph": "",
            "experiences": [],  # Empty list, no padding
            "technical_skills": [],
            "certifications": [],
            "language_skills": ["English - Fluent"]
        }