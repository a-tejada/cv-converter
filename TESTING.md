# CV Converter - Testing Documentation

## Overview

The CV Converter includes a comprehensive automated test suite with **31 tests** covering all critical functionality. All tests achieve a **100% pass rate**, ensuring reliability and code quality.

---

## Test Suite Summary

| Category                 | Tests  | Pass Rate | Description                                            |
| ------------------------ | ------ | --------- | ------------------------------------------------------ |
| **Formatting**           | 6      | 100%      | Date formatting, name normalization, duration handling |
| **Data Validation**      | 6      | 100%      | AI output validation, structure verification, defaults |
| **Template Processing**  | 6      | 100%      | Token replacement, education/certification handling    |
| **Critical Features**    | 3      | 100%      | Multiple roles, file safety, text extraction           |
| **Edge Cases**           | 4      | 100%      | Max capacity, missing data, location extraction        |
| **Production Critical**  | 4      | 100%      | PDF extraction, error handling, cleanup                |
| **Pipeline Integration** | 2      | 100%      | End-to-end mock pipeline, empty data handling          |
| **TOTAL**                | **31** | **100%**  | Comprehensive coverage                                 |

---

## Quick Start

### Prerequisites

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (includes pytest)
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest tests/ -v
```

**Expected Output:**

```
31 passed in ~20s
```

### Run Specific Test Category

```bash
# Formatting tests
pytest tests/test_formatting.py -v

# Data validation tests
pytest tests/test_extraction.py -v

# Template processing tests
pytest tests/test_template.py -v

# Critical features
pytest tests/test_critical_features.py -v

# Edge cases
pytest tests/test_edge_cases.py -v

# Production scenarios
pytest tests/test_production_critical.py -v

# Full pipeline integration
pytest tests/test_pipeline_integration.py -v
```

### Quick Test (Minimal Output)

```bash
pytest tests/ -q
```

---

## Test Categories Detailed

### 1. Formatting Tests (`test_formatting.py`)

**Purpose:** Validate text formatting functions used throughout the application.

**Tests (6):**

- ✅ `test_format_name_all_caps_to_proper` - Converts "JOHN DOE" → "John Doe"
- ✅ `test_format_name_already_proper` - Preserves "John Doe" → "John Doe"
- ✅ `test_format_date_sep_dash_format` - Normalizes "Sep-2015" → "SEP 2015"
- ✅ `test_format_date_present_variations` - Handles "present", "till date" → "Present"
- ✅ `test_format_duration_with_present` - Preserves "Present" in ongoing roles
- ✅ `test_format_duration_date_range` - Formats "Jan 2020 - Dec 2023" → "JAN 2020 to DEC 2023"

**Coverage:** All text formatting and normalization logic

---

### 2. Data Validation Tests (`test_extraction.py`)

**Purpose:** Ensure AI extraction output is properly validated and structured.

**Tests (6):**

- ✅ `test_validate_data_formats_candidate_name` - Formats names from ALL CAPS
- ✅ `test_validate_data_adds_default_language_skills` - Adds "English - Fluent" default
- ✅ `test_validate_data_ensures_experience_structure` - Adds missing fields with defaults
- ✅ `test_validate_data_formats_experience_roles` - Formats job titles properly
- ✅ `test_validate_data_handles_empty_experiences` - Handles CVs with no experience
- ✅ `test_validate_data_ensures_education_structure` - Validates education entry structure

**Coverage:** Complete `CVExtractor._validate_data()` method

---

### 3. Template Processing Tests (`test_template.py`)

**Purpose:** Verify template token replacement and data filling works correctly.

**Tests (6):**

- ✅ `test_fill_template_replaces_basic_tokens` - Replaces name, position, email tokens
- ✅ `test_fill_template_replaces_experience_tokens` - Fills experience data correctly
- ✅ `test_fill_template_removes_empty_responsibility_lines` - Removes unused bullet points
- ✅ `test_fill_template_handles_education` - Processes education entries
- ✅ `test_fill_template_handles_certifications` - Processes certification entries
- ✅ `test_fill_template_no_unreplaced_tokens` - **Critical:** No `{{tokens}}` remain

**Coverage:** Complete `fill_template()` function

---

### 4. Critical Features Tests (`test_critical_features.py`)

**Purpose:** Test application's unique and critical functionality.

**Tests (3):**

- ⭐ `test_multiple_roles_same_company_creates_separate_experiences` - **Key feature:** Multiple roles at same company handled separately
- ✅ `test_safe_filename_removes_special_characters` - Sanitizes filenames with special chars
- ✅ `test_extract_text_from_docx` - Extracts text from DOCX files

**Coverage:** Core differentiating features of the application

---

### 5. Edge Cases Tests (`test_edge_cases.py`)

**Purpose:** Handle uncommon but valid scenarios gracefully.

**Tests (4):**

- ✅ `test_missing_candidate_name_uses_placeholder` - Handles missing names (filename fallback)
- ✅ `test_handles_maximum_20_experiences` - Supports maximum 20 work experiences
- ✅ `test_location_extracted_separately_from_company` - Location field separate from company
- ✅ `test_handles_experience_21_beyond_max` - Gracefully ignores experience 21+

**Coverage:** Boundary conditions and unusual input scenarios

---

### 6. Production Critical Tests (`test_production_critical.py`)

**Purpose:** Ensure production readiness with real-world scenarios.

**Tests (4):**

- ✅ `test_extract_text_from_pdf` - Extracts text from PDF files
- ✅ `test_extract_text_handles_corrupted_file` - Doesn't crash on malformed files
- ⭐ `test_table_row_deletion_removes_empty_experiences` - **Critical:** Cleanup logic for unused rows
- ✅ `test_extract_text_handles_empty_docx` - Handles empty documents

**Coverage:** Error handling and production scenarios

---

### 7. Pipeline Integration Tests (`test_pipeline_integration.py`)

**Purpose:** Test end-to-end data flow through the system.

**Tests (2):**

- ⭐ `test_mock_ai_extraction_end_to_end` - **Full pipeline:** Mock AI → Validate → Fill → Verify
- ✅ `test_empty_certifications_and_education_handled_gracefully` - Handles CVs with no certs/education

**Coverage:** Complete data flow from extraction to output

---

## Test Results

### Latest Test Run

```
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-9.0.2, pluggy-1.6.0
collected 31 items

tests/test_critical_features.py::test_multiple_roles_same_company_creates_separate_experiences PASSED [  3%]
tests/test_critical_features.py::test_safe_filename_removes_special_characters PASSED [  6%]
tests/test_critical_features.py::test_extract_text_from_docx PASSED [  9%]
tests/test_edge_cases.py::test_missing_candidate_name_uses_placeholder PASSED [ 12%]
tests/test_edge_cases.py::test_handles_maximum_20_experiences PASSED [ 16%]
tests/test_edge_cases.py::test_location_extracted_separately_from_company PASSED [ 19%]
tests/test_edge_cases.py::test_handles_experience_21_beyond_max PASSED [ 22%]
tests/test_extraction.py::test_validate_data_formats_candidate_name PASSED [ 25%]
tests/test_extraction.py::test_validate_data_adds_default_language_skills PASSED [ 29%]
tests/test_extraction.py::test_validate_data_ensures_experience_structure PASSED [ 32%]
tests/test_extraction.py::test_validate_data_formats_experience_roles PASSED [ 35%]
tests/test_extraction.py::test_validate_data_handles_empty_experiences PASSED [ 38%]
tests/test_extraction.py::test_validate_data_ensures_education_structure PASSED [ 41%]
tests/test_formatting.py::test_format_name_all_caps_to_proper PASSED [ 45%]
tests/test_formatting.py::test_format_name_already_proper PASSED [ 48%]
tests/test_formatting.py::test_format_date_sep_dash_format PASSED [ 51%]
tests/test_formatting.py::test_format_date_present_variations PASSED [ 54%]
tests/test_formatting.py::test_format_duration_with_present PASSED [ 58%]
tests/test_formatting.py::test_format_duration_date_range PASSED [ 61%]
tests/test_pipeline_integration.py::test_mock_ai_extraction_end_to_end PASSED [ 64%]
tests/test_pipeline_integration.py::test_empty_certifications_and_education_handled_gracefully PASSED [ 67%]
tests/test_production_critical.py::test_extract_text_from_pdf PASSED [ 70%]
tests/test_production_critical.py::test_extract_text_handles_corrupted_file PASSED [ 74%]
tests/test_production_critical.py::test_table_row_deletion_removes_empty_experiences PASSED [ 77%]
tests/test_production_critical.py::test_extract_text_handles_empty_docx PASSED [ 80%]
tests/test_template.py::test_fill_template_replaces_basic_tokens PASSED [ 83%]
tests/test_template.py::test_fill_template_replaces_experience_tokens PASSED [ 87%]
tests/test_template.py::test_fill_template_removes_empty_responsibility_lines PASSED [ 90%]
tests/test_template.py::test_fill_template_handles_education PASSED [ 93%]
tests/test_template.py::test_fill_template_handles_certifications PASSED [ 96%]
tests/test_template.py::test_fill_template_no_unreplaced_tokens PASSED [100%]

============================== 31 passed in 20.15s ===============================
```

---

## Coverage Analysis

### What's Tested

✅ **Core Functions (100%):**

- Text extraction (PDF, DOCX)
- Date/name formatting
- Template token replacement
- Data validation

✅ **Critical Features (100%):**

- Multiple roles at same company
- Table row deletion/cleanup
- Location extraction
- File safety

✅ **Edge Cases:**

- Maximum capacity (20 experiences)
- Missing data handling
- Corrupted file handling
- Empty documents

✅ **Integration:**

- Full pipeline simulation
- Data flow validation

## Adding New Tests

### Test File Structure

Each test file follows this pattern:

```python
# tests/test_example.py
import pytest
from module import function_to_test


def test_descriptive_name():
    """Clear description of what this tests"""
    # Arrange
    input_data = {...}

    # Act
    result = function_to_test(input_data)

    # Assert
    assert result == expected_value
```

### Best Practices

1. **Name tests descriptively:** `test_what_it_does_under_what_condition`
2. **One assertion per test:** Keep tests focused
3. **Use docstrings:** Explain what the test validates
4. **Mock external dependencies:** Don't call real APIs
5. **Test edge cases:** Empty data, maximum capacity, errors

### Example: Adding a New Test

```python
# tests/test_formatting.py

def test_format_date_handles_future_dates():
    """Test that future dates are formatted correctly"""
    assert format_date("Dec-2030") == "DEC 2030"
```

Run the new test:

```bash
pytest tests/test_formatting.py::test_format_date_handles_future_dates -v
```

---

## Troubleshooting Tests

### Common Issues

**Problem:** `ModuleNotFoundError: No module named 'pytest'`

**Solution:**

```bash
pip install pytest reportlab
```

---

**Problem:** `ImportError: cannot import name 'function' from 'module'`

**Solution:** Ensure virtual environment is activated:

```bash
source venv/bin/activate
```

---

**Problem:** Tests pass locally but fail in CI

**Solution:** Check that all dependencies are in `requirements.txt`

---

**Problem:** Slow test execution

**Solution:** Run specific test files instead of entire suite:

```bash
pytest tests/test_formatting.py -v  # Fast (6 tests)
```

---

## Performance

### Test Execution Times

| Test File                      | Tests  | Avg Time |
| ------------------------------ | ------ | -------- |
| `test_formatting.py`           | 6      | ~1s      |
| `test_extraction.py`           | 6      | ~2s      |
| `test_template.py`             | 6      | ~3s      |
| `test_critical_features.py`    | 3      | ~4s      |
| `test_edge_cases.py`           | 4      | ~3s      |
| `test_production_critical.py`  | 4      | ~4s      |
| `test_pipeline_integration.py` | 2      | ~3s      |
| **Total**                      | **31** | **~20s** |

---

## Test Maintenance

### When to Update Tests

- ✅ When adding new features
- ✅ When fixing bugs (add regression test)
- ✅ When changing data structures
- ✅ When modifying extraction logic

### When NOT to Update Tests

- ❌ When changing UI/styling only
- ❌ When updating documentation
- ❌ When refactoring without behavior changes

---

## Support

For questions about testing:

1. Check test docstrings for what each test validates
2. Run individual tests to isolate issues: `pytest tests/test_file.py::test_name -v`
3. Review test output for assertion failures

---

_Last Updated: January 2026_
_Test Suite Version: 1.0_
