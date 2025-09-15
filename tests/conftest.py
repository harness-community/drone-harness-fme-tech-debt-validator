"""Test configuration and fixtures."""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Fixture providing mock environment variables that auto-applies to all tests."""
    env_vars = {
        "DRONE_COMMIT_BEFORE": "abc123",
        "DRONE_COMMIT_AFTER": "def456",
        "PLUGIN_HARNESS_API_TOKEN": "test-token",
        "HARNESS_ACCOUNT_ID": "test-account",
        "HARNESS_ORG_ID": "test-org",
        "HARNESS_PROJECT_ID": "test-project",
        "PLUGIN_PRODUCTION_ENVIRONMENT_NAME": "Production",
        "PLUGIN_MAX_FLAGS_IN_PROJECT": "50",
        "PLUGIN_FLAG_LAST_MODIFIED_THRESHOLD": "90d",
        "PLUGIN_FLAG_LAST_TRAFFIC_THRESHOLD": "30d",
        "PLUGIN_TAG_REMOVE_THESE_FLAGS": "deprecated,remove",
        "PLUGIN_TAG_PERMANENT_FLAGS": "permanent,keep",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_harness_client():
    """Fixture providing a mock Harness client."""
    client = Mock()

    # Mock workspace
    workspace = Mock()
    workspace.id = "workspace-123"
    client.workspaces.find.return_value = workspace

    # Mock flag metadata
    flag_meta = Mock()
    flag_meta.name = "test-flag"
    flag_meta._tags = [Mock(name="production")]
    client.splits.list.return_value = [flag_meta]

    # Mock environments
    env = Mock()
    env.id = "env-123"
    env.name = "Production"
    client.environments.list.return_value = [env]

    # Mock flag definitions
    flag_def = Mock()
    flag_def.name = "test-flag"
    flag_def.lastUpdateTime = 1640995200  # 2022-01-01
    flag_def.lastTrafficReceivedAt = 1640995200
    flag_def._traffic_allocation = 100
    flag_def._rules = []
    flag_def._default_rule = Mock()
    flag_def._default_rule.buckets = [Mock(size=100)]
    client.split_definitions.list.return_value = [flag_def]

    return client


@pytest.fixture
def mock_git_diff():
    """Fixture providing mock git diff output."""
    return [
        "src/components/Feature.js",
        "src/services/api.java",
        "tests/test_flags.py",
        "config/settings.cs",
    ]


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
    const FEATURE_FLAG = "new-dashboard";
    const USER_ID = "user123";
    
    // Various method signatures
    const result1 = client.getTreatment("simple-flag");
    const result2 = split.getTreatment(USER_ID, "user-context-flag");
    const result3 = splitClient.getTreatment("direct-flag", attributes);
    const result4 = api.getTreatmentWithConfig(FEATURE_FLAG);
    const result5 = service.getTreatmentWithConfig(userId, "complex-flag", config);
    
    // Non-flag calls (should be filtered out)
    const other = someMethod("not-a-flag");
    """


@pytest.fixture
def sample_javascript_multiple_flags_code():
    """Sample JavaScript code with multiple flag methods for testing."""
    return """
    const SINGLE_FLAG = "single-feature";
    const FLAG_ARRAY = ["multi-flag-1", "multi-flag-2"];
    const USER_ID = "user123";
    
    // Single flag methods
    const result1 = client.getTreatment("js-single-flag");
    const result2 = service.getTreatmentWithConfig(SINGLE_FLAG);
    
    // Multiple flag methods with arrays
    const result3 = client.getTreatments(["js-multi-flag-1", "js-multi-flag-2"]);
    const result4 = split.getTreatments(USER_ID, ["js-context-flag-1", "js-context-flag-2"]);
    const result5 = api.getTreatmentsWithConfig(["js-config-flag-1", "js-config-flag-2"]);
    const result6 = service.getTreatmentsWithConfig(USER_ID, FLAG_ARRAY, config);
    
    // Mixed usage
    const result7 = client.getTreatment("mixed-single");
    const result8 = client.getTreatments(["mixed-multi-1", "mixed-multi-2"]);
    
    // Non-flag calls (should be filtered out)
    const other = someMethod(["not-a-flag"]);
    """


@pytest.fixture
def sample_java_code():
    """Sample Java code for testing."""
    return """
    public class FeatureService {
        private static final String FLAG_NAME = "checkout-flow";
        private String userId = "user456";
        
        public void checkFeatures() {
            // Various method signatures
            String result1 = client.getTreatment("simple-java-flag");
            String result2 = splitClient.getTreatment(userId, "user-java-flag");
            String result3 = featureClient.getTreatmentWithConfig(FLAG_NAME);
            String result4 = service.getTreatmentWithConfig(userId, "complex-java-flag");
            
            // Non-flag calls
            String other = otherMethod("not-a-flag");
        }
    }
    """


@pytest.fixture
def sample_java_multiple_flags_code():
    """Sample Java code with multiple flag methods for testing."""
    return """
    import java.util.Arrays;
    import java.util.List;
    
    public class FeatureService {
        private static final String SINGLE_FLAG = "java-single-feature";
        private static final List<String> FLAG_LIST = Arrays.asList("java-list-flag-1", "java-list-flag-2");
        private String userId = "user456";
        
        public void checkFeatures() {
            // Single flag methods
            String result1 = client.getTreatment("java-single-flag");
            String result2 = service.getTreatmentWithConfig(SINGLE_FLAG);
            
            // Multiple flag methods with Arrays.asList
            Map<String, String> result3 = client.getTreatments(Arrays.asList("java-multi-flag-1", "java-multi-flag-2"));
            Map<String, String> result4 = split.getTreatments(userId, Arrays.asList("java-context-flag-1", "java-context-flag-2"));
            Map<String, String> result5 = api.getTreatmentsWithConfig(Arrays.asList("java-config-flag-1", "java-config-flag-2"));
            Map<String, String> result6 = service.getTreatmentsWithConfig(userId, FLAG_LIST);
            
            // Mixed usage
            String result7 = client.getTreatment("java-mixed-single");
            Map<String, String> result8 = client.getTreatments(Arrays.asList("java-mixed-multi-1", "java-mixed-multi-2"));
            
            // Non-flag calls
            List<String> other = otherMethod(Arrays.asList("not-a-flag"));
        }
    }
    """


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """
    FLAG_NAME = "payment-gateway"
    user_id = "user789"
    
    def check_features():
        # Various method signatures
        result1 = client.get_treatment("simple-python-flag")
        result2 = split_client.get_treatment(user_id, "user-python-flag")
        result3 = feature_client.get_treatment_with_config(FLAG_NAME)
        result4 = service.get_treatment_with_config(user_id, "complex-python-flag")
        
        # Non-flag calls
        other = other_method("not-a-flag")
    """


@pytest.fixture
def sample_python_multiple_flags_code():
    """Sample Python code with multiple flag methods for testing."""
    return """
    SINGLE_FLAG = "python-single-feature"
    FLAG_LIST = ["python-list-flag-1", "python-list-flag-2"]
    user_id = "user789"
    
    def check_features():
        # Single flag methods
        result1 = client.get_treatment("python-single-flag")
        result2 = service.get_treatment_with_config(SINGLE_FLAG)
        
        # Multiple flag methods with lists
        result3 = client.get_treatments(["python-multi-flag-1", "python-multi-flag-2"])
        result4 = split_client.get_treatments(user_id, ["python-context-flag-1", "python-context-flag-2"])
        result5 = api.get_treatments_with_config(["python-config-flag-1", "python-config-flag-2"])
        result6 = service.get_treatments_with_config(user_id, FLAG_LIST)
        
        # Mixed usage
        result7 = client.get_treatment("python-mixed-single")
        result8 = client.get_treatments(["python-mixed-multi-1", "python-mixed-multi-2"])
        
        # Non-flag calls
        other = other_method(["not-a-flag"])
    """


@pytest.fixture
def sample_csharp_code():
    """Sample C# code for testing."""
    return """
    public class FeatureService 
    {
        private static readonly string FlagName = "mobile-app";
        private string userId = "user101";
        
        public void CheckFeatures() 
        {
            // Various method signatures
            var result1 = client.GetTreatment("simple-csharp-flag");
            var result2 = splitClient.GetTreatment(userId, "user-csharp-flag");
            var result3 = featureClient.GetTreatmentWithConfig(FlagName);
            var result4 = service.GetTreatmentWithConfigAsync(userId, "complex-csharp-flag");
            
            // Non-flag calls
            var other = OtherMethod("not-a-flag");
        }
    }
    """


@pytest.fixture
def sample_csharp_multiple_flags_code():
    """Sample C# code with multiple flag methods for testing."""
    return """
    using System.Collections.Generic;
    
    public class FeatureService 
    {
        private static readonly string SingleFlag = "csharp-single-feature";
        private static readonly List<string> FlagList = new List<string> { "csharp-list-flag-1", "csharp-list-flag-2" };
        private string userId = "user101";
        
        public async Task CheckFeatures() 
        {
            // Single flag methods
            var result1 = client.GetTreatment("csharp-single-flag");
            var result2 = service.GetTreatmentWithConfig(SingleFlag);
            
            // Multiple flag methods with List<string>
            var result3 = client.GetTreatments("key", new List<string> { "csharp-multi-flag-1", "csharp-multi-flag-2" });
            var result4 = split.GetTreatments(userId, new List<string> { "csharp-context-flag-1", "csharp-context-flag-2" });
            var result5 = api.GetTreatmentsWithConfig("key", new List<string> { "csharp-config-flag-1", "csharp-config-flag-2" });
            var result6 = service.GetTreatmentsWithConfig(userId, FlagList);
            
            // Async multiple flag methods
            var result7 = await client.GetTreatmentsAsync("key", new List<string> { "csharp-async-flag-1", "csharp-async-flag-2" });
            var result8 = await api.GetTreatmentsWithConfigAsync("key", new List<string> { "csharp-async-config-1", "csharp-async-config-2" });
            
            // Mixed usage
            var result9 = client.GetTreatment("csharp-mixed-single");
            var result10 = client.GetTreatments("key", new List<string> { "csharp-mixed-multi-1", "csharp-mixed-multi-2" });
            
            // Non-flag calls
            var other = OtherMethod(new List<string> { "not-a-flag" });
        }
    }
    """


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize git repo
        os.system(f"cd {temp_dir} && git init")
        os.system(f'cd {temp_dir} && git config user.email "test@test.com"')
        os.system(f'cd {temp_dir} && git config user.name "Test User"')

        # Create some test files
        test_files = {
            "src/test.js": 'client.getTreatment("test-flag");',
            "src/test.java": 'client.getTreatment("java-flag");',
            "src/test.py": 'client.get_treatment("python-flag");',
        }

        for file_path, content in test_files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        # Initial commit
        os.system(f"cd {temp_dir} && git add .")
        os.system(f'cd {temp_dir} && git commit -m "Initial commit"')

        yield temp_dir


@pytest.fixture
def mock_requests_response():
    """Mock requests response for API calls."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"data": {"content": [{"identifier": "test-project", "name": "Test Project"}]}}
    response.raise_for_status.return_value = None
    return response


@pytest.fixture
def mock_failed_requests_response():
    """Mock failed requests response for error testing."""
    response = Mock()
    response.status_code = 404
    response.json.side_effect = ValueError("No JSON object could be decoded")
    response.raise_for_status.side_effect = Exception("404 Not Found")
    return response
