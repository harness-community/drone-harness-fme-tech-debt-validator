"""Tests for AST parsing functionality."""
import pytest
from app.main import (
    extract_flags_ast_javascript,
    extract_flags_ast_java,
    extract_flags_ast_python,
    extract_flags_ast_csharp,
    extract_flags_regex
)


@pytest.mark.ast
class TestJavaScriptASTParsing:
    """Test JavaScript AST parsing functionality."""
    
    def test_simple_string_literals(self):
        """Test extraction of simple string literals."""
        code = '''
        client.getTreatment("simple-flag");
        service.getTreatmentWithConfig("config-flag");
        '''
        flags = extract_flags_ast_javascript(code)
        assert "simple-flag" in flags
        assert "config-flag" in flags
        assert len(flags) == 2
    
    def test_multiple_arguments_extraction(self, sample_javascript_code):
        """Test extraction from multiple argument scenarios using 'extract all' approach."""
        flags = extract_flags_ast_javascript(sample_javascript_code)
        
        # Expected flags include all string arguments to getTreatment methods
        expected_flags = {
            "simple-flag", "user-context-flag", "direct-flag", 
            "new-dashboard", "complex-flag", "user123"  # user123 is extracted as designed
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
        
        # Should not contain strings from non-getTreatment methods
        assert "not-a-flag" not in flags
    
    def test_variable_resolution(self):
        """Test resolution of variables to flag names."""
        code = '''
        const FLAG_A = "feature-a";
        const FLAG_B = "feature-b";
        
        client.getTreatment(FLAG_A);
        service.getTreatment(userId, FLAG_B);
        '''
        flags = extract_flags_ast_javascript(code)
        assert "feature-a" in flags
        assert "feature-b" in flags
    
    def test_different_method_names(self):
        """Test detection of different method name variants."""
        code = '''
        client.getTreatment("flag1");
        service.treatment("flag2");
        api.getTreatmentWithConfig("flag3");
        '''
        flags = extract_flags_ast_javascript(code)
        assert "flag1" in flags
        assert "flag2" in flags
        assert "flag3" in flags
    
    def test_invalid_javascript(self):
        """Test handling of invalid JavaScript code."""
        invalid_code = "this is not valid javascript {["
        flags = extract_flags_ast_javascript(invalid_code)
        assert flags == []
    
    def test_no_esprima_fallback(self, monkeypatch):
        """Test fallback when esprima is not available."""
        # Mock esprima as None
        import app.main
        monkeypatch.setattr(app.main, 'esprima', None)
        
        code = 'client.getTreatment("test-flag");'
        flags = extract_flags_ast_javascript(code)
        assert flags == []


@pytest.mark.ast
class TestJavaASTParsing:
    """Test Java AST parsing functionality."""
    
    def test_simple_string_literals(self):
        """Test extraction of simple string literals."""
        code = '''
        public class Test {
            public void method() {
                client.getTreatment("java-flag");
                service.getTreatmentWithConfig("java-config-flag");
            }
        }
        '''
        flags = extract_flags_ast_java(code)
        assert "java-flag" in flags
        assert "java-config-flag" in flags
    
    def test_multiple_arguments_extraction(self, sample_java_code):
        """Test extraction from multiple argument scenarios."""
        flags = extract_flags_ast_java(sample_java_code)
        
        expected_flags = {
            "simple-java-flag", "user-java-flag", 
            "checkout-flow", "complex-java-flag"
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
    
    def test_variable_resolution(self):
        """Test resolution of Java variables."""
        code = '''
        public class Test {
            private static final String FLAG_NAME = "java-feature";
            
            public void method() {
                client.getTreatment(FLAG_NAME);
            }
        }
        '''
        flags = extract_flags_ast_java(code)
        assert "java-feature" in flags
    
    def test_invalid_java(self):
        """Test handling of invalid Java code."""
        invalid_code = "this is not valid java code"
        flags = extract_flags_ast_java(invalid_code)
        assert flags == []
    
    def test_no_javalang_fallback(self, monkeypatch):
        """Test fallback when javalang is not available."""
        import app.main
        monkeypatch.setattr(app.main, 'javalang', None)
        
        code = 'client.getTreatment("test-flag");'
        flags = extract_flags_ast_java(code)
        assert flags == []


@pytest.mark.ast
class TestPythonASTParsing:
    """Test Python AST parsing functionality."""
    
    def test_simple_string_literals(self):
        """Test extraction of simple string literals."""
        code = '''
client.get_treatment("python-flag")
service.get_treatment_with_config("python-config-flag")
'''
        flags = extract_flags_ast_python(code)
        assert "python-flag" in flags
        assert "python-config-flag" in flags
    
    def test_multiple_arguments_extraction(self, sample_python_code):
        """Test extraction from multiple argument scenarios."""
        flags = extract_flags_ast_python(sample_python_code)
        
        expected_flags = {
            "simple-python-flag", "user-python-flag",
            "payment-gateway", "complex-python-flag"
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
    
    def test_variable_resolution(self):
        """Test resolution of Python variables."""
        code = '''
FLAG_NAME = "python-feature"
client.get_treatment(FLAG_NAME)
'''
        flags = extract_flags_ast_python(code)
        assert "python-feature" in flags
    
    def test_different_method_names(self):
        """Test different Python method name variants."""
        code = '''
client.getTreatment("flag1")
service.get_treatment("flag2")
api.treatment("flag3")
handler.get_treatment_with_config("flag4")
'''
        flags = extract_flags_ast_python(code)
        assert "flag1" in flags
        assert "flag2" in flags
        assert "flag3" in flags
        assert "flag4" in flags
    
    def test_invalid_python(self):
        """Test handling of invalid Python code."""
        invalid_code = "this is not valid python syntax $$"
        flags = extract_flags_ast_python(invalid_code)
        assert flags == []


@pytest.mark.ast
class TestCSharpParsing:
    """Test C# parsing functionality (regex-based)."""
    
    def test_simple_string_literals(self):
        """Test extraction of simple string literals."""
        code = '''
        client.GetTreatment("csharp-flag");
        service.GetTreatmentWithConfig("csharp-config-flag");
        '''
        flags = extract_flags_ast_csharp(code)
        assert "csharp-flag" in flags
        assert "csharp-config-flag" in flags
    
    def test_multiple_arguments_extraction(self, sample_csharp_code):
        """Test extraction from multiple argument scenarios."""
        flags = extract_flags_ast_csharp(sample_csharp_code)
        
        expected_flags = {
            "simple-csharp-flag", "user-csharp-flag",
            "mobile-app", "complex-csharp-flag"
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
    
    def test_variable_resolution(self):
        """Test resolution of C# variables."""
        code = '''
        string flagName = "csharp-feature";
        client.GetTreatment(flagName);
        '''
        flags = extract_flags_ast_csharp(code)
        assert "csharp-feature" in flags
    
    def test_async_methods(self):
        """Test detection of async method variants."""
        code = '''
        var result = await client.GetTreatmentAsync("async-flag");
        var config = await service.GetTreatmentWithConfigAsync("async-config-flag");
        '''
        flags = extract_flags_ast_csharp(code)
        assert "async-flag" in flags
        assert "async-config-flag" in flags


@pytest.mark.ast
class TestRegexFallback:
    """Test regex fallback parsing functionality."""
    
    def test_javascript_patterns(self):
        """Test regex extraction from JavaScript-like code."""
        code = '''
        client.getTreatment("regex-js-flag");
        service.getTreatmentWithConfig("regex-js-config");
        '''
        flags = extract_flags_regex(code)
        assert "regex-js-flag" in flags
        assert "regex-js-config" in flags
    
    def test_csharp_patterns(self):
        """Test regex extraction from C#-like code."""
        code = '''
        client.GetTreatment("regex-cs-flag");
        service.GetTreatmentWithConfigAsync("regex-cs-config");
        '''
        flags = extract_flags_regex(code)
        assert "regex-cs-flag" in flags
        assert "regex-cs-config" in flags
    
    def test_mixed_language_patterns(self):
        """Test regex extraction from mixed language patterns."""
        code = '''
        // JavaScript
        client.getTreatment("js-flag");
        
        // C#
        Client.GetTreatment("cs-flag");
        
        // Python-style
        client.get_treatment("py-flag");
        '''
        flags = extract_flags_regex(code)
        assert "js-flag" in flags
        assert "cs-flag" in flags
        assert "py-flag" in flags
    
    def test_multiple_arguments_in_regex(self):
        """Test regex extraction with multiple arguments."""
        code = '''
        client.getTreatment(userId, "multi-arg-flag", attributes);
        service.GetTreatment(user, "another-multi-flag");
        '''
        flags = extract_flags_regex(code)
        assert "multi-arg-flag" in flags
        assert "another-multi-flag" in flags
    
    def test_no_false_positives(self):
        """Test that regex doesn't pick up non-flag method calls."""
        code = '''
        client.getTreatment("real-flag");
        client.getUser("user123");
        service.processData("data-value");
        '''
        flags = extract_flags_regex(code)
        assert "real-flag" in flags
        assert "user123" not in flags
        assert "data-value" not in flags


@pytest.mark.ast
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_code(self):
        """Test handling of empty code."""
        assert extract_flags_ast_javascript("") == []
        assert extract_flags_ast_java("") == []
        assert extract_flags_ast_python("") == []
        assert extract_flags_ast_csharp("") == []
        assert extract_flags_regex("") == []
    
    def test_no_method_calls(self):
        """Test code with no relevant method calls."""
        code = '''
        const variable = "value";
        function someFunction() {
            return "result";
        }
        '''
        assert extract_flags_ast_javascript(code) == []
    
    def test_method_calls_without_strings(self):
        """Test method calls without string arguments."""
        code = '''
        client.getTreatment(someVariable);
        service.getTreatment(123);
        api.getTreatment(null);
        '''
        # Should return empty since variables aren't resolved
        flags = extract_flags_ast_javascript(code)
        assert flags == []
    
    def test_nested_method_calls(self):
        """Test nested method calls."""
        code = '''
        const result = client.getTreatment(
            service.getUserId(), 
            "nested-flag"
        );
        '''
        flags = extract_flags_ast_javascript(code)
        assert "nested-flag" in flags
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in flags."""
        code = '''
        client.getTreatment("flag-with-unicode-🚀");
        service.getTreatment("flag_with_special_chars!@#");
        '''
        flags = extract_flags_ast_javascript(code)
        assert "flag-with-unicode-🚀" in flags
        assert "flag_with_special_chars!@#" in flags
    
    @pytest.mark.parametrize("method_name", [
        "getTreatment", "treatment", "getTreatmentWithConfig"
    ])
    def test_all_supported_method_names(self, method_name):
        """Test all supported method name variations."""
        code = f'client.{method_name}("test-flag");'
        flags = extract_flags_ast_javascript(code)
        assert "test-flag" in flags