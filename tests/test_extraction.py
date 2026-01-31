# tests/test_extraction.py
import pytest
from extraction import CVExtractor


def test_validate_data_formats_candidate_name():
    """Test that candidate names get formatted from ALL CAPS to Proper Case"""
    extractor = CVExtractor("fake-api-key")  # API key not used for this test
    
    data = {
        "candidate_name": "JOHN DOE",
        "position": "SENIOR ENGINEER",
        "experiences": []
    }
    
    validated = extractor._validate_data(data)
    
    assert validated["candidate_name"] == "John Doe"
    assert validated["position"] == "Senior Engineer"


def test_validate_data_adds_default_language_skills():
    """Test that default language skills are added if missing"""
    extractor = CVExtractor("fake-api-key")
    
    data = {
        "candidate_name": "Jane Doe",
        "experiences": []
    }
    
    validated = extractor._validate_data(data)
    
    assert "language_skills" in validated
    assert "English - Fluent" in validated["language_skills"]

def test_validate_data_ensures_experience_structure():
    """Test that experiences have all required fields with defaults"""
    extractor = CVExtractor("fake-api-key")
    
    data = {
        "candidate_name": "Jane Doe",
        "experiences": [
            {
                "role": "Engineer",
                "duration": "2020 - 2023"
                # Missing company, responsibilities
            }
        ]
    }
    
    validated = extractor._validate_data(data)
    
    exp = validated["experiences"][0]
    assert "company" in exp
    assert "role" in exp
    assert "duration" in exp
    assert "responsibilities" in exp
    assert isinstance(exp["responsibilities"], list)

def test_validate_data_formats_experience_roles():
    """Test that experience role names get formatted from ALL CAPS"""
    extractor = CVExtractor("fake-api-key")
    
    data = {
        "candidate_name": "Jane Doe",
        "experiences": [
            {
                "company": "Tech Corp",
                "role": "SENIOR SOFTWARE ENGINEER",
                "duration": "Jan 2020 - Dec 2023",
                "responsibilities": ["Task 1"]
            }
        ]
    }
    
    validated = extractor._validate_data(data)
    
    assert validated["experiences"][0]["role"] == "Senior Software Engineer"


def test_validate_data_handles_empty_experiences():
    """Test that empty experiences list is handled properly"""
    extractor = CVExtractor("fake-api-key")
    
    data = {
        "candidate_name": "Jane Doe"
    }
    
    validated = extractor._validate_data(data)
    
    assert "experiences" in validated
    assert isinstance(validated["experiences"], list)
    assert len(validated["experiences"]) == 0


def test_validate_data_ensures_education_structure():
    """Test that education entries have proper structure"""
    extractor = CVExtractor("fake-api-key")
    
    data = {
        "candidate_name": "Jane Doe",
        "experiences": [],
        "education": [
            {
                "degree": "BS Computer Science"
                # Missing institution and duration
            }
        ]
    }
    
    validated = extractor._validate_data(data)
    
    edu = validated["education"][0]
    assert "institution" in edu
    assert "duration" in edu
    assert "degree" in edu
