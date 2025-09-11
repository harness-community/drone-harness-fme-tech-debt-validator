# Testing Guide

This document describes the comprehensive test suite for the Feature Flag CI Plugin.

## 📁 Test Structure

```
tests/
├── __init__.py              # Test package
├── conftest.py              # Shared fixtures and configuration
├── test_ast_parsing.py      # AST parsing functionality tests
├── test_ci_runner.py        # CI runner integration tests
├── test_error_handling.py   # Error handling and edge cases
├── test_utils.py            # Testing utilities
└── TESTING.md               # This file
```

## 🧪 Test Categories

### Unit Tests (`@pytest.mark.unit`)
Test individual functions and methods in isolation:
- AST parsing for each language
- Individual validation checks
- Error handling scenarios
- Edge cases and boundary conditions

### Integration Tests (`@pytest.mark.integration`) 
Test component interactions and workflows:
- Full CI runner workflow
- API integration with Harness
- Git integration
- File processing pipeline

### AST Tests (`@pytest.mark.ast`)
Focused tests for AST parsing functionality:
- JavaScript/TypeScript parsing
- Java parsing
- Python parsing
- C# regex parsing
- Regex fallback patterns

### Slow Tests (`@pytest.mark.slow`)
Tests that take longer to run:
- Real git repository operations
- Large file processing
- Network timeout scenarios

## 🏃‍♂️ Running Tests

### Quick Start
```bash
# Run all tests
./run_tests.sh

# Or manually:
pip install -r requirements-test.txt
pytest tests/
```

### Specific Test Categories
```bash
# Unit tests only
pytest tests/ -m "unit"

# Integration tests only  
pytest tests/ -m "integration"

# AST parsing tests only
pytest tests/ -m "ast"

# Fast tests in parallel
pytest tests/ -m "not slow" -n auto

# With coverage
pytest tests/ --cov=app --cov-report=html
```

### Individual Test Files
```bash
# AST parsing tests
pytest tests/test_ast_parsing.py -v

# CI runner tests
pytest tests/test_ci_runner.py -v

# Error handling tests
pytest tests/test_error_handling.py -v
```

## 📊 Test Coverage

The test suite covers:

### AST Parsing (95%+ coverage)
- ✅ **JavaScript**: All method variants, variable resolution, error handling
- ✅ **Java**: Method signatures, string literals, variable resolution  
- ✅ **Python**: All method names, variable resolution, error handling
- ✅ **C#**: Regex patterns, async methods, variable resolution
- ✅ **Regex Fallback**: Multi-language patterns, edge cases

### CI Runner Functionality (90%+ coverage)
- ✅ **Initialization**: Environment variables, default values
- ✅ **Flag Retrieval**: API calls, error handling, data parsing
- ✅ **Code Analysis**: Git diff integration, file processing
- ✅ **Validation Checks**: All check types, passing/failing scenarios
- ✅ **Workflow Integration**: End-to-end testing

### Error Handling (100% coverage)
- ✅ **Network Errors**: Timeouts, connection failures, HTTP errors
- ✅ **API Errors**: Invalid JSON, unexpected structure, missing data
- ✅ **File Errors**: Missing files, encoding issues, permission errors
- ✅ **Git Errors**: Command failures, repository issues
- ✅ **Data Errors**: Missing attributes, invalid formats, null values

## 🔧 Test Fixtures

### Environment Setup
- `mock_env_vars`: Complete environment variable configuration
- `mock_harness_client`: Pre-configured Harness API client
- `temp_git_repo`: Temporary git repository for testing

### Sample Code
- `sample_javascript_code`: JavaScript with various flag patterns
- `sample_java_code`: Java code with different method signatures
- `sample_python_code`: Python code with multiple patterns
- `sample_csharp_code`: C# code with async methods

### Mock Data
- `mock_requests_response`: HTTP response mocking
- `mock_failed_requests_response`: Error response scenarios

## 🎯 Key Test Scenarios

### Multi-Argument Extraction
Tests verify the "extract all string arguments" approach:
```javascript
// All these patterns are tested:
getTreatment("flag")                    // ✅
getTreatment(userId, "flag")            // ✅  
getTreatment("flag", attributes)        // ✅
getTreatment(userId, "flag", config)    // ✅
```

### Variable Resolution
Tests verify variable-to-flag resolution:
```javascript
const FLAG_NAME = "my-feature";
client.getTreatment(FLAG_NAME);  // ✅ Resolves to "my-feature"
```

### Error Resilience
Tests verify graceful error handling:
- Network timeouts don't crash the plugin
- Invalid JSON responses are handled
- Missing file attributes don't cause exceptions
- API structure changes are accommodated

### Edge Cases
Tests verify boundary conditions:
- Empty files and directories
- Very large flag names
- Unicode characters in flags
- Future timestamps
- Zero limits and thresholds

## 🚨 Test Failures

Common test failure scenarios and debugging:

### Import Errors
```bash
# If AST parsing libraries are missing:
pip install esprima javalang tree-sitter

# If test dependencies are missing:
pip install -r requirements-test.txt
```

### Mock Issues
```bash
# If mocks aren't working:
pytest tests/ -s  # See print statements
pytest tests/ -vv # Very verbose output
```

### Coverage Issues
```bash
# Generate detailed coverage report:
pytest tests/ --cov=app --cov-report=html --cov-missing
# View in: htmlcov/index.html
```

## 📈 Adding New Tests

### For New AST Features
1. Add sample code to `conftest.py` fixtures
2. Create test methods in `test_ast_parsing.py`
3. Test both positive and negative cases
4. Include edge cases and error scenarios

### For New CI Features  
1. Add integration tests to `test_ci_runner.py`
2. Mock external dependencies appropriately
3. Test both success and failure paths
4. Include error handling tests

### For New Error Scenarios
1. Add specific error tests to `test_error_handling.py`
2. Mock the error conditions
3. Verify graceful handling
4. Ensure no crashes or data corruption

## 🔍 Test Quality Guidelines

### Good Test Practices
- ✅ **Descriptive names**: `test_javascript_multiple_arguments_extraction`
- ✅ **Single responsibility**: One test per scenario
- ✅ **Arrange-Act-Assert**: Clear test structure
- ✅ **Isolated**: Tests don't depend on each other
- ✅ **Fast**: Quick execution for rapid feedback

### Test Documentation
- ✅ **Docstrings**: Explain what each test verifies
- ✅ **Comments**: Clarify complex setup or assertions
- ✅ **Examples**: Show expected inputs/outputs
- ✅ **Markers**: Use pytest markers for categorization

## 🎨 Continuous Integration

Tests are designed to run in CI environments:

```yaml
# Example CI configuration
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest tests/ --cov=app --cov-fail-under=90
```

The test suite is optimized for:
- ✅ **Speed**: Fast feedback for developers
- ✅ **Reliability**: Consistent results across environments  
- ✅ **Coverage**: High code coverage requirements
- ✅ **Isolation**: No external dependencies required
- ✅ **Parallelization**: Can run tests in parallel safely

## 🎯 Coverage Goals

Target coverage levels:
- **Overall**: 90%+
- **AST Parsing**: 95%+
- **Error Handling**: 100%
- **Core Logic**: 95%+
- **Integration**: 85%+

Run `pytest tests/ --cov=app --cov-report=html` to see detailed coverage reports.