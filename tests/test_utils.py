"""Utility functions for testing."""
import tempfile
import os
from typing import Dict, List
from unittest.mock import Mock


def create_temp_file_with_content(content: str, suffix: str = '.txt') -> str:
    """Create a temporary file with given content."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
        f.write(content)
        return f.name


def cleanup_temp_file(file_path: str) -> None:
    """Clean up a temporary file."""
    try:
        os.unlink(file_path)
    except FileNotFoundError:
        pass


def create_mock_flag_detail(name: str, **kwargs) -> Mock:
    """Create a mock flag detail object."""
    flag_detail = Mock()
    flag_detail.name = name
    flag_detail.lastUpdateTime = kwargs.get('lastUpdateTime', 1640995200)
    flag_detail.lastTrafficRecievedAt = kwargs.get('lastTrafficRecievedAt', 1640995200)
    flag_detail._traffic_allocation = kwargs.get('traffic_allocation', 50)
    flag_detail._rules = kwargs.get('rules', [])
    flag_detail._default_rule = kwargs.get('default_rule', Mock())
    return flag_detail


def create_mock_flag_meta(name: str, tags: List[str] = None) -> Mock:
    """Create a mock flag metadata object."""
    flag_meta = Mock()
    flag_meta.name = name
    
    if tags:
        tag_mocks = [Mock(name=tag) for tag in tags]
        flag_meta._tags = tag_mocks
        # Mock the map/any chain for tag checking
        flag_meta._tags.map = Mock(return_value=Mock(any=Mock(return_value=any(tag in ['deprecated', 'remove'] for tag in tags))))
    else:
        flag_meta._tags = []
    
    return flag_meta


def create_sample_code_files() -> Dict[str, str]:
    """Create sample code files for different languages."""
    return {
        'test.js': '''
        const FLAG_A = "feature-a";
        client.getTreatment("simple-flag");
        service.getTreatment(userId, "user-flag");
        api.getTreatmentWithConfig(FLAG_A);
        ''',
        'test.java': '''
        public class Test {
            private static final String FLAG_B = "feature-b";
            public void method() {
                client.getTreatment("java-flag");
                service.getTreatment(userId, FLAG_B);
            }
        }
        ''',
        'test.py': '''
        FLAG_C = "feature-c"
        client.get_treatment("python-flag")
        service.get_treatment(user_id, FLAG_C)
        ''',
        'test.cs': '''
        public class Test {
            private string flagD = "feature-d";
            public void Method() {
                client.GetTreatment("csharp-flag");
                service.GetTreatment(userId, flagD);
            }
        }
        '''
    }


class MockHarnessResponse:
    """Mock Harness API response builder."""
    
    @staticmethod
    def create_projects_response(projects: List[Dict[str, str]]):
        """Create a mock projects API response."""
        return {
            'data': {
                'content': projects
            }
        }
    
    @staticmethod
    def create_environments_response(environments: List[Dict[str, str]]):
        """Create a mock environments response."""
        return [Mock(**env) for env in environments]
    
    @staticmethod
    def create_flag_definitions_response(flags: List[Dict[str, any]]):
        """Create mock flag definitions response."""
        return [create_mock_flag_detail(**flag) for flag in flags]


def assert_flags_found(actual_flags: List[str], expected_flags: List[str]):
    """Assert that expected flags are found in actual flags."""
    for flag in expected_flags:
        assert flag in actual_flags, f"Expected flag '{flag}' not found in {actual_flags}"


def assert_flags_not_found(actual_flags: List[str], unexpected_flags: List[str]):
    """Assert that unexpected flags are not found in actual flags."""
    for flag in unexpected_flags:
        assert flag not in actual_flags, f"Unexpected flag '{flag}' found in {actual_flags}"