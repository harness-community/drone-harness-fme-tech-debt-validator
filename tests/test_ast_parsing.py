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
    
    def test_multiple_flags_extraction(self, sample_javascript_multiple_flags_code):
        """Test extraction from getTreatments and getTreatmentsWithConfig methods."""
        flags = extract_flags_ast_javascript(sample_javascript_multiple_flags_code)
        
        # Expected flags from single flag methods
        single_flags = {
            "js-single-flag", "single-feature"
        }
        
        # Expected flags from multiple flag methods
        multi_flags = {
            "js-multi-flag-1", "js-multi-flag-2",
            "js-context-flag-1", "js-context-flag-2", 
            "js-config-flag-1", "js-config-flag-2",
            "multi-flag-1", "multi-flag-2",  # from variable resolution
            "mixed-single", "mixed-multi-1", "mixed-multi-2"
        }
        
        all_expected = single_flags | multi_flags
        
        for flag in all_expected:
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
        client.getTreatments(["flag4", "flag5"]);
        service.getTreatmentsWithConfig(["flag6", "flag7"]);
        '''
        flags = extract_flags_ast_javascript(code)
        assert "flag1" in flags
        assert "flag2" in flags
        assert "flag3" in flags
        assert "flag4" in flags
        assert "flag5" in flags
        assert "flag6" in flags
        assert "flag7" in flags
    
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
    
    def test_esprima_available_vs_unavailable(self):
        """Test behavior difference when esprima is available vs unavailable."""
        import app.main
        
        code = '''
        client.getTreatment("available-flag");
        client.getTreatments(["multi-flag-1", "multi-flag-2"]);
        '''
        
        # Test with esprima available (if it's installed)
        if app.main.esprima:
            flags_with_esprima = extract_flags_ast_javascript(code)
            assert len(flags_with_esprima) >= 1  # Should find at least some flags
        
        # Test with esprima unavailable
        original_esprima = app.main.esprima
        app.main.esprima = None
        try:
            flags_without_esprima = extract_flags_ast_javascript(code)
            assert flags_without_esprima == []  # Should return empty
        finally:
            app.main.esprima = original_esprima


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
                List<String> flagList = Arrays.asList("java-multi-flag1", "java-multi-flag2");
                client.getTreatments(userId, flagList);
                service.getTreatmentsWithConfig(userId, Arrays.asList("java-multi-config1", "java-multi-config2"));
            }
        }
        '''
        flags = extract_flags_ast_java(code)
        assert "java-flag" in flags
        assert "java-config-flag" in flags
        assert "java-multi-flag1" in flags
        assert "java-multi-flag2" in flags
        assert "java-multi-config1" in flags
        assert "java-multi-config2" in flags
    
    def test_multiple_arguments_extraction(self, sample_java_code):
        """Test extraction from multiple argument scenarios."""
        flags = extract_flags_ast_java(sample_java_code)
        
        expected_flags = {
            "simple-java-flag", "user-java-flag", 
            "checkout-flow", "complex-java-flag"
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
    
    def test_multiple_flags_extraction(self, sample_java_multiple_flags_code):
        """Test extraction from getTreatments and getTreatmentsWithConfig methods with Arrays.asList."""
        flags = extract_flags_ast_java(sample_java_multiple_flags_code)
        
        # Expected flags from single flag methods
        single_flags = {
            "java-single-flag", "java-single-feature"
        }
        
        # Expected flags from multiple flag methods with Arrays.asList
        multi_flags = {
            "java-multi-flag-1", "java-multi-flag-2",
            "java-context-flag-1", "java-context-flag-2",
            "java-config-flag-1", "java-config-flag-2", 
            "java-list-flag-1", "java-list-flag-2",  # from variable resolution
            "java-mixed-single", "java-mixed-multi-1", "java-mixed-multi-2"
        }
        
        all_expected = single_flags | multi_flags
        
        for flag in all_expected:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
        
        # Should not contain strings from non-getTreatment methods
        assert "not-a-flag" not in flags
    
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
    
    def test_javalang_available_vs_unavailable(self):
        """Test behavior difference when javalang is available vs unavailable."""
        import app.main
        
        code = '''
        public class Test {
            public void method() {
                client.getTreatment("available-flag");
                client.getTreatments(Arrays.asList("multi-flag-1", "multi-flag-2"));
            }
        }
        '''
        
        # Test with javalang available (if it's installed)
        if app.main.javalang:
            flags_with_javalang = extract_flags_ast_java(code)
            assert len(flags_with_javalang) >= 1  # Should find at least some flags
        
        # Test with javalang unavailable
        original_javalang = app.main.javalang
        app.main.javalang = None
        try:
            flags_without_javalang = extract_flags_ast_java(code)
            assert flags_without_javalang == []  # Should return empty
        finally:
            app.main.javalang = original_javalang


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
    
    def test_multiple_flags_extraction(self, sample_python_multiple_flags_code):
        """Test extraction from get_treatments and get_treatments_with_config methods."""
        flags = extract_flags_ast_python(sample_python_multiple_flags_code)
        
        # Expected flags from single flag methods
        single_flags = {
            "python-single-flag", "python-single-feature"
        }
        
        # Expected flags from multiple flag methods with lists
        multi_flags = {
            "python-multi-flag-1", "python-multi-flag-2",
            "python-context-flag-1", "python-context-flag-2",
            "python-config-flag-1", "python-config-flag-2",
            "python-list-flag-1", "python-list-flag-2",  # from variable resolution
            "python-mixed-single", "python-mixed-multi-1", "python-mixed-multi-2"
        }
        
        all_expected = single_flags | multi_flags
        
        for flag in all_expected:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
        
        # Should not contain strings from non-getTreatment methods
        assert "not-a-flag" not in flags
    
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
client.getTreatments(["flag5", "flag6"])
service.get_treatments(["flag7", "flag8"])
handler.get_treatments_with_config(["flag9", "flag10"])
'''
        flags = extract_flags_ast_python(code)
        assert "flag1" in flags
        assert "flag2" in flags
        assert "flag3" in flags
        assert "flag4" in flags
        assert "flag5" in flags
        assert "flag6" in flags
        assert "flag7" in flags
        assert "flag8" in flags
        assert "flag9" in flags
        assert "flag10" in flags
    
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
    
    def test_multiple_flags_extraction(self, sample_csharp_multiple_flags_code):
        """Test extraction from GetTreatments and GetTreatmentsWithConfig methods including async variants."""
        flags = extract_flags_ast_csharp(sample_csharp_multiple_flags_code)
        
        # Expected flags from single flag methods
        single_flags = {
            "csharp-single-flag", "csharp-single-feature"
        }
        
        # Expected flags from multiple flag methods with List<string>
        multi_flags = {
            "csharp-multi-flag-1", "csharp-multi-flag-2",
            "csharp-context-flag-1", "csharp-context-flag-2",
            "csharp-config-flag-1", "csharp-config-flag-2",
            "csharp-list-flag-1", "csharp-list-flag-2",  # from variable resolution
            "csharp-async-flag-1", "csharp-async-flag-2",
            "csharp-async-config-1", "csharp-async-config-2",
            "csharp-mixed-single", "csharp-mixed-multi-1", "csharp-mixed-multi-2"
        }
        
        all_expected = single_flags | multi_flags
        
        for flag in all_expected:
            assert flag in flags, f"Expected flag '{flag}' not found in {flags}"
        
        # Should not contain strings from non-getTreatment methods
        assert "not-a-flag" not in flags
    
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
        var featureFlagNames = new List<string> { "async-multi-flag1", "async-multi-flag2" };
        var multiResults = await client.GetTreatmentsAsync("key", featureFlagNames);
        var multiConfig = await service.GetTreatmentsWithConfigAsync("key", new List<string> { "async-config1", "async-config2" });
        '''
        flags = extract_flags_ast_csharp(code)
        assert "async-flag" in flags
        assert "async-config-flag" in flags
        assert "async-multi-flag1" in flags
        assert "async-multi-flag2" in flags
        assert "async-config1" in flags
        assert "async-config2" in flags


@pytest.mark.ast
class TestRegexFallback:
    """Test regex fallback parsing functionality."""
    
    def test_javascript_patterns(self):
        """Test regex extraction from JavaScript-like code."""
        code = '''
        client.getTreatment("regex-js-flag");
        service.getTreatmentWithConfig("regex-js-config");
        client.getTreatments(["regex-multi-flag1", "regex-multi-flag2"]);
        service.getTreatmentsWithConfig(["regex-multi-config1", "regex-multi-config2"]);
        '''
        flags = extract_flags_regex(code)
        assert "regex-js-flag" in flags
        assert "regex-js-config" in flags
        assert "regex-multi-flag1" in flags
        assert "regex-multi-flag2" in flags
        assert "regex-multi-config1" in flags
        assert "regex-multi-config2" in flags
    
    def test_csharp_patterns(self):
        """Test regex extraction from C#-like code."""
        code = '''
        client.GetTreatment("regex-cs-flag");
        service.GetTreatmentWithConfigAsync("regex-cs-config");
        var flagList = new List<string> { "regex-cs-multi1", "regex-cs-multi2" };
        client.GetTreatments("key", flagList);
        service.GetTreatmentsAsync("key", new List<string> { "regex-cs-async1", "regex-cs-async2" });
        '''
        flags = extract_flags_regex(code)
        assert "regex-cs-flag" in flags
        assert "regex-cs-config" in flags
        assert "regex-cs-multi1" in flags
        assert "regex-cs-multi2" in flags
        assert "regex-cs-async1" in flags
        assert "regex-cs-async2" in flags
    
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
        "getTreatment", "treatment", "getTreatmentWithConfig", "getTreatments", "getTreatmentsWithConfig"
    ])
    def test_all_supported_method_names(self, method_name):
        """Test all supported method name variations."""
        if "getTreatments" in method_name:
            code = f'client.{method_name}(["test-flag"]);'
        else:
            code = f'client.{method_name}("test-flag");'
        flags = extract_flags_ast_javascript(code)
        assert "test-flag" in flags
    
    @pytest.mark.slow
    def test_performance_with_large_codebase(self):
        """Test performance with large codebase simulation."""
        # Simulate a large JavaScript file with many method calls
        large_code_parts = []
        expected_flags = set()
        
        for i in range(500):  # 500 method calls
            single_flag = f"single-flag-{i}"
            multi_flag_1 = f"multi-flag-{i}-1"
            multi_flag_2 = f"multi-flag-{i}-2"
            
            large_code_parts.append(f'client.getTreatment("{single_flag}");')
            large_code_parts.append(f'client.getTreatments(["{multi_flag_1}", "{multi_flag_2}"]);')
            
            expected_flags.update([single_flag, multi_flag_1, multi_flag_2])
        
        large_code = '\n'.join(large_code_parts)
        
        import time
        start_time = time.time()
        flags = extract_flags_ast_javascript(large_code)
        end_time = time.time()
        
        # Should complete within reasonable time (5 seconds)
        assert (end_time - start_time) < 5.0, f"Parsing took too long: {end_time - start_time} seconds"
        
        # Should find all expected flags
        assert len(flags) == len(expected_flags)
        assert expected_flags.issubset(set(flags))


@pytest.mark.ast
class TestGetTreatmentsMultipleFlags:
    """Test parsing of getTreatments methods that accept multiple flags."""
    
    def test_javascript_array_literals(self):
        """Test JavaScript array literal parsing."""
        code = '''
        client.getTreatments(["flag-a", "flag-b", "flag-c"]);
        service.getTreatmentsWithConfig(userId, ["config-flag-1", "config-flag-2"]);
        '''
        flags = extract_flags_ast_javascript(code)
        expected = {"flag-a", "flag-b", "flag-c", "config-flag-1", "config-flag-2"}
        assert expected.issubset(set(flags))
    
    def test_java_arrays_aslist(self):
        """Test Java Arrays.asList() parsing."""
        code = '''
        public class Test {
            public void method() {
                List<String> flags = Arrays.asList("java-flag-1", "java-flag-2");
                client.getTreatments(userId, flags);
                service.getTreatments(Arrays.asList("direct-flag-1", "direct-flag-2"));
            }
        }
        '''
        flags = extract_flags_ast_java(code)
        expected = {"java-flag-1", "java-flag-2", "direct-flag-1", "direct-flag-2"}
        assert expected.issubset(set(flags))
    
    def test_python_list_literals(self):
        """Test Python list literal parsing."""
        code = '''
flag_list = ["python-flag-1", "python-flag-2"]
client.get_treatments(user_id, flag_list)
service.get_treatments(["direct-python-flag-1", "direct-python-flag-2"])
'''
        flags = extract_flags_ast_python(code)
        expected = {"python-flag-1", "python-flag-2", "direct-python-flag-1", "direct-python-flag-2"}
        assert expected.issubset(set(flags))
    
    def test_csharp_list_creation(self):
        """Test C# List<string> creation parsing."""
        code = '''
        var featureFlagNames = new List<string> { "csharp-flag-1", "csharp-flag-2" };
        var result = client.GetTreatments("KEY", featureFlagNames);
        var directResult = service.GetTreatments("KEY", new List<string> { "direct-csharp-1", "direct-csharp-2" });
        '''
        flags = extract_flags_ast_csharp(code)
        expected = {"csharp-flag-1", "csharp-flag-2", "direct-csharp-1", "direct-csharp-2"}
        assert expected.issubset(set(flags))
    
    def test_mixed_single_and_multiple_flags(self):
        """Test mixing single flag and multiple flag methods."""
        code = '''
        // Single flags
        client.getTreatment("single-flag-1");
        service.getTreatmentWithConfig("single-flag-2");
        
        // Multiple flags
        client.getTreatments(["multi-flag-1", "multi-flag-2"]);
        service.getTreatmentsWithConfig(["multi-config-1", "multi-config-2"]);
        '''
        flags = extract_flags_ast_javascript(code)
        expected = {
            "single-flag-1", "single-flag-2", 
            "multi-flag-1", "multi-flag-2", 
            "multi-config-1", "multi-config-2"
        }
        assert expected.issubset(set(flags))
    
    def test_variable_resolution_with_arrays(self):
        """Test variable resolution for array variables."""
        code = '''
        const SINGLE_FLAG = "resolved-single";
        const FLAG_ARRAY = ["resolved-multi-1", "resolved-multi-2"];
        
        client.getTreatment(SINGLE_FLAG);
        client.getTreatments(FLAG_ARRAY);
        '''
        flags = extract_flags_ast_javascript(code)
        expected = {"resolved-single", "resolved-multi-1", "resolved-multi-2"}
        assert expected.issubset(set(flags))
    
    def test_regex_fallback_with_arrays(self):
        """Test regex fallback for array patterns."""
        code = '''
        // JavaScript style
        getTreatments(["js-regex-1", "js-regex-2"]);
        
        // Java style  
        getTreatments(Arrays.asList("java-regex-1", "java-regex-2"));
        
        // C# style
        GetTreatments("key", new List<string> { "cs-regex-1", "cs-regex-2" });
        '''
        flags = extract_flags_regex(code)
        expected = {
            "js-regex-1", "js-regex-2",
            "java-regex-1", "java-regex-2", 
            "cs-regex-1", "cs-regex-2"
        }
        assert expected.issubset(set(flags))


@pytest.mark.ast
class TestEdgeCasesAndErrorHandling:
    """Test edge cases, error handling, and comprehensive coverage."""
    
    def test_empty_arrays_and_lists(self):
        """Test handling of empty arrays and lists."""
        # JavaScript
        js_code = '''
        client.getTreatments([]);
        service.getTreatmentsWithConfig([]);
        '''
        js_flags = extract_flags_ast_javascript(js_code)
        assert js_flags == []
        
        # Python
        py_code = '''
client.get_treatments([])
service.get_treatments_with_config([])
'''
        py_flags = extract_flags_ast_python(py_code)
        assert py_flags == []
        
        # Java (Arrays.asList with no arguments)
        java_code = '''
        public class Test {
            public void method() {
                client.getTreatments(Arrays.asList());
            }
        }
        '''
        java_flags = extract_flags_ast_java(java_code)
        assert java_flags == []
    
    def test_mixed_variable_and_literal_arrays(self):
        """Test arrays mixing variables and literals."""
        # JavaScript
        js_code = '''
        const FLAG_VAR = "variable-flag";
        client.getTreatments([FLAG_VAR, "literal-flag"]);
        '''
        js_flags = extract_flags_ast_javascript(js_code)
        assert "variable-flag" in js_flags
        assert "literal-flag" in js_flags
        
        # Python
        py_code = '''
FLAG_VAR = "python-variable-flag"
client.get_treatments([FLAG_VAR, "python-literal-flag"])
'''
        py_flags = extract_flags_ast_python(py_code)
        assert "python-variable-flag" in py_flags
        assert "python-literal-flag" in py_flags
    
    def test_nested_arrays_and_complex_expressions(self):
        """Test handling of complex expressions that should be ignored."""
        # JavaScript - nested arrays should be handled at top level only
        js_code = '''
        client.getTreatments(["flag1", ["nested", "array"], "flag2"]);
        '''
        js_flags = extract_flags_ast_javascript(js_code)
        assert "flag1" in js_flags
        assert "flag2" in js_flags
        assert "nested" not in js_flags  # Nested arrays should be ignored
        assert "array" not in js_flags
    
    def test_malformed_syntax_graceful_handling(self):
        """Test graceful handling of malformed syntax."""
        # JavaScript with syntax errors
        js_malformed = '''
        client.getTreatments(["flag1", "flag2"  // missing closing bracket
        '''
        js_flags = extract_flags_ast_javascript(js_malformed)
        assert js_flags == []  # Should return empty on syntax error
        
        # Java with syntax errors
        java_malformed = '''
        public class Test {
            public void method() {
                client.getTreatments(Arrays.asList("flag1", "flag2"  // missing closing paren
            }
        '''
        java_flags = extract_flags_ast_java(java_malformed)
        assert java_flags == []  # Should return empty on syntax error
    
    def test_non_string_array_elements(self):
        """Test arrays with non-string elements are handled correctly."""
        # JavaScript with mixed types
        js_code = '''
        client.getTreatments(["valid-flag", 123, null, "another-flag", true]);
        '''
        js_flags = extract_flags_ast_javascript(js_code)
        assert "valid-flag" in js_flags
        assert "another-flag" in js_flags
        assert len([f for f in js_flags if f in ["valid-flag", "another-flag"]]) == 2
    
    def test_very_large_arrays(self):
        """Test performance with large arrays doesn't cause issues."""
        # Generate a large array
        large_array = '", "'.join([f"flag-{i}" for i in range(100)])
        js_code = f'client.getTreatments(["{large_array}"]);'
        
        js_flags = extract_flags_ast_javascript(js_code)
        assert len(js_flags) == 100
        assert "flag-0" in js_flags
        assert "flag-99" in js_flags
    
    def test_unicode_and_special_characters_in_arrays(self):
        """Test arrays with unicode and special characters."""
        js_code = '''
        client.getTreatments(["flag-with-emoji-🚀", "flag_with_special_chars!@#", "flag-with-unicode-中文"]);
        '''
        js_flags = extract_flags_ast_javascript(js_code)
        assert "flag-with-emoji-🚀" in js_flags
        assert "flag_with_special_chars!@#" in js_flags
        assert "flag-with-unicode-中文" in js_flags
    
    def test_dependency_fallback_handling(self):
        """Test graceful fallback when optional dependencies are missing."""
        # Test esprima fallback
        import app.main
        
        # Mock missing esprima
        original_esprima = app.main.esprima
        app.main.esprima = None
        
        try:
            js_code = 'client.getTreatments(["fallback-flag"]);'
            js_flags = extract_flags_ast_javascript(js_code)
            assert js_flags == []  # Should return empty when esprima unavailable
        finally:
            app.main.esprima = original_esprima
    
    def test_comprehensive_async_csharp_variants(self):
        """Test all C# async method variants comprehensively."""
        csharp_async_code = '''
        public class AsyncFeatureService 
        {
            public async Task TestAllAsyncVariants() 
            {
                // Standard async methods
                var result1 = await client.GetTreatmentAsync("async-single-flag");
                var result2 = await service.GetTreatmentWithConfigAsync("async-config-flag");
                
                // Multiple flag async methods
                var result3 = await client.GetTreatmentsAsync("key", new List<string> { "async-multi-1", "async-multi-2" });
                var result4 = await api.GetTreatmentsWithConfigAsync("key", new List<string> { "async-config-multi-1", "async-config-multi-2" });
                
                // Mixed sync and async
                var result5 = client.GetTreatment("sync-flag");
                var result6 = await client.GetTreatmentsAsync("key", new List<string> { "mixed-async-1", "mixed-async-2" });
            }
        }
        '''
        
        csharp_flags = extract_flags_ast_csharp(csharp_async_code)
        
        expected_async_flags = {
            "async-single-flag", "async-config-flag",
            "async-multi-1", "async-multi-2", 
            "async-config-multi-1", "async-config-multi-2",
            "sync-flag", "mixed-async-1", "mixed-async-2"
        }
        
        for flag in expected_async_flags:
            assert flag in csharp_flags, f"Expected async flag '{flag}' not found in {csharp_flags}"


@pytest.mark.ast
class TestRegexFallbackRobustness:
    """Test comprehensive regex fallback functionality."""
    
    def test_regex_with_all_language_array_patterns(self):
        """Test regex fallback handles all language array patterns correctly."""
        mixed_code = '''
        // JavaScript style arrays
        getTreatments(["js-regex-1", "js-regex-2"]);
        getTreatmentsWithConfig(["js-config-1", "js-config-2"]);
        
        // Java style Arrays.asList
        getTreatments(Arrays.asList("java-regex-1", "java-regex-2"));
        getTreatmentsWithConfig(Arrays.asList("java-config-1", "java-config-2"));
        
        // C# style List<string>
        GetTreatments("key", new List<string> { "cs-regex-1", "cs-regex-2" });
        GetTreatmentsAsync("key", new List<string> { "cs-async-1", "cs-async-2" });
        GetTreatmentsWithConfigAsync("key", new List<string> { "cs-async-config-1", "cs-async-config-2" });
        
        // Python style lists (also covered by JS pattern)
        get_treatments(["py-regex-1", "py-regex-2"]);
        '''
        
        flags = extract_flags_regex(mixed_code)
        
        expected_flags = {
            "js-regex-1", "js-regex-2", "js-config-1", "js-config-2",
            "java-regex-1", "java-regex-2", "java-config-1", "java-config-2",
            "cs-regex-1", "cs-regex-2", "cs-async-1", "cs-async-2",
            "cs-async-config-1", "cs-async-config-2", "py-regex-1", "py-regex-2"
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected regex flag '{flag}' not found in {flags}"
    
    def test_regex_edge_cases_whitespace_and_formatting(self):
        """Test regex handles various whitespace and formatting scenarios."""
        code_with_formatting = '''
        // Various whitespace scenarios
        getTreatments( [ "whitespace-flag-1" , "whitespace-flag-2" ] );
        getTreatments([
            "multiline-flag-1",
            "multiline-flag-2"
        ]);
        
        // Various C# formatting
        GetTreatments("key",new List<string>{"no-space-1","no-space-2"});
        GetTreatments( "key" , new List<string> { "extra-space-1" , "extra-space-2" } );
        
        // Java formatting variations
        getTreatments(Arrays.asList( "java-space-1" , "java-space-2" ));
        getTreatments(Arrays.asList(
            "java-multiline-1",
            "java-multiline-2"
        ));
        '''
        
        flags = extract_flags_regex(code_with_formatting)
        
        expected_flags = {
            "whitespace-flag-1", "whitespace-flag-2",
            "multiline-flag-1", "multiline-flag-2",
            "no-space-1", "no-space-2",
            "extra-space-1", "extra-space-2",
            "java-space-1", "java-space-2",
            "java-multiline-1", "java-multiline-2"
        }
        
        for flag in expected_flags:
            assert flag in flags, f"Expected formatted flag '{flag}' not found in {flags}"