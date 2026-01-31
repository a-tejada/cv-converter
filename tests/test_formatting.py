# tests/test_formatting.py
import pytest
from utils import format_name, format_date, format_duration


def test_format_name_all_caps_to_proper():
    """Test converting ALL CAPS names to Proper Case"""
    assert format_name("JOHN DOE") == "John Doe"
    assert format_name("JANE SMITH") == "Jane Smith"


def test_format_name_already_proper():
    """Test that already proper names stay unchanged"""
    assert format_name("John Doe") == "John Doe"


def test_format_date_sep_dash_format():
    """Test Sep-2015 format gets normalized to SEP 2015"""
    assert format_date("Sep-2015") == "SEP 2015"
    assert format_date("Jan-2020") == "JAN 2020"


def test_format_date_present_variations():
    """Test that 'present' variations normalize to 'Present'"""
    assert format_date("present") == "Present"
    assert format_date("Present") == "Present"
    assert format_date("till date") == "Present"


def test_format_duration_with_present():
    """Test duration formatting preserves 'Present' for ongoing roles"""
    result = format_duration("Sep-2015 - Present")
    assert "Present" in result
    assert "SEP" in result  # Month should be uppercase


def test_format_duration_date_range():
    """Test duration with start and end dates"""
    result = format_duration("Jan 2020 - Dec 2023")  # Space within dates
    assert "to" in result  # Should have "to" separator
    assert "JAN" in result
    assert "DEC" in result