"""Comprehensive error message formatting with troubleshooting guidance."""

from typing import List


class ErrorMessageFormatter:
    """Provides comprehensive, actionable error messages with troubleshooting guidance"""

    @staticmethod
    def format_flag_removal_error(
        flag_name: str, tag_name: str, files_with_flag: List[str] = None
    ) -> str:
        """Format error message for flags marked for removal"""
        message = f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ FEATURE FLAG REMOVAL REQUIRED
╠══════════════════════════════════════════════════════════════════════
║ Flag: '{flag_name}'
║ Issue: Flag has removal tag '{tag_name}'
║ 
║ 🔧 REQUIRED ACTIONS:
║ 1. Remove all references to '{flag_name}' from your code
║ 2. Clean up any related configuration or documentation
║ 3. Consider the impact on users and gradual rollout strategy
║ 
║ 📁 FILES CONTAINING THIS FLAG:"""

        if files_with_flag:
            for file_path in files_with_flag:
                message += f"\n║    • {file_path}"
        else:
            message += f"\n║    • (Run git grep '{flag_name}' to locate all references)"

        message += """
║ 
║ 💡 HELPFUL COMMANDS:
║    git grep -n "{flag}" --exclude-dir=node_modules
║    rg "{flag}" --type js --type java --type py
║ 
║ 📖 DOCUMENTATION:
║    Best Practices: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════""".format(
            flag=flag_name
        )

        return message

    @staticmethod
    def format_flag_count_error(
        current_count: int, max_allowed: int, flags_in_code: List[str]
    ) -> str:
        """Format error message for flag count limit exceeded"""
        excess_count = current_count - max_allowed
        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ FEATURE FLAG COUNT LIMIT EXCEEDED
╠══════════════════════════════════════════════════════════════════════
║ Current Flags: {current_count}
║ Maximum Allowed: {max_allowed}
║ Excess Count: {excess_count}
║ 
║ 🔧 REQUIRED ACTIONS:
║ 1. Remove {excess_count} feature flag(s) from your code
║ 2. Consider consolidating similar flags
║ 3. Remove unused or deprecated flags
║ 
║ 📋 ALL FLAGS IN CODE:
║    {chr(10).join([f'    • {flag}' for flag in sorted(flags_in_code)])}
║ 
║ 💡 STRATEGIES TO REDUCE FLAG COUNT:
║    • Identify flags at 100% rollout for removal
║    • Combine similar feature toggles
║    • Remove experiment flags after conclusion
║    • Archive flags not used in production
║ 
║ 📖 GOVERNANCE GUIDE:
║    Flag Management: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════"""

    @staticmethod
    def format_stale_flag_error(
        flag_name: str,
        threshold: str,
        last_activity: str,
        flag_type: str = "modified",
    ) -> str:
        """Format error message for stale flags"""
        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ STALE FEATURE FLAG DETECTED
╠══════════════════════════════════════════════════════════════════════
║ Flag: '{flag_name}'
║ Issue: Flag hasn't been {flag_type} in {threshold}
║ Last Activity: {last_activity}
║ 
║ 🔧 REQUIRED ACTIONS:
║ 1. Review if this flag is still needed
║ 2. If needed, add 'permanent' tag to exclude from stale checks
║ 3. If not needed, plan removal strategy
║ 4. Update flag configuration if actively used
║ 
║ 🏷️  TO MARK AS PERMANENT:
║    • Add tag 'permanent' or 'keep' in Harness UI
║    • This will exclude it from future stale flag checks
║ 
║ 🗑️  TO REMOVE SAFELY:
║    1. Verify flag is not actively used in production
║    2. Check traffic metrics and user impact
║    3. Plan gradual removal if needed
║    4. Remove from code and Harness configuration
║ 
║ 📊 CHECK FLAG USAGE:
║    • Review analytics in Harness dashboard
║    • Check production traffic patterns
║    • Verify with product/engineering teams
║ 
║ 📖 RESOURCES:
║    Flag Lifecycle: https://developer.harness.io/docs/feature-management-experimentation/getting-started/overview/manage-the-feature-flag-lifecycle/
╚══════════════════════════════════════════════════════════════════════"""

    @staticmethod
    def format_api_error(
        error_type: str, details: str, suggestions: List[str]
    ) -> str:
        """Format error message for API connectivity issues"""
        suggestion_text = "\n".join(
            [
                f"║    {i+1}. {suggestion}"
                for i, suggestion in enumerate(suggestions)
            ]
        )

        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ HARNESS API CONNECTION ERROR
╠══════════════════════════════════════════════════════════════════════
║ Error Type: {error_type}
║ Details: {details}
║ 
║ 🔧 TROUBLESHOOTING STEPS:
{suggestion_text}
║ 
║ 🔑 VERIFY CREDENTIALS:
║    • Check HARNESS_API_TOKEN is valid and not expired
║    • Verify HARNESS_ACCOUNT_ID is correct
║    • Confirm HARNESS_PROJECT_ID exists
║ 
║ 🌐 NETWORK DIAGNOSTICS:
║    curl -H "x-api-key: $HARNESS_API_TOKEN" \\
║         https://app.harness.io/ng/api/projects
║ 
║ 📖 HARNESS API DOCS:
║    Authentication: https://developer.harness.io/docs/platform/automation/api/api-permissions-reference
║    Getting Started: https://developer.harness.io/docs/platform/automation/api/api-quickstart
╚══════════════════════════════════════════════════════════════════════"""

    @staticmethod
    def format_configuration_error(
        missing_vars: List[str], optional_vars: List[str] = None
    ) -> str:
        """Format error message for configuration issues"""
        required_text = "\n".join([f"║    • {var}" for var in missing_vars])
        optional_text = ""
        if optional_vars:
            optional_text = f"""
║ 
║ 🔧 OPTIONAL CONFIGURATION:
║    These can enhance functionality:
{chr(10).join([f'║    • {var}' for var in optional_vars])}"""

        return f"""
╔══════════════════════════════════════════════════════════════════════
║ ❌ CONFIGURATION ERROR
╠══════════════════════════════════════════════════════════════════════
║ Missing required environment variables
║ 
║ 🔑 REQUIRED VARIABLES:
{required_text}{optional_text}
║ 
║ 
║ 🚀 FOR DRONE/HARNESS CI:
║    steps:
║    - name: feature-flag-check
║      image: your-registry/feature-flag-ci-plugin
║      settings:
║        harness_api_token:
║          from_secret: harness_token
║ 
╚══════════════════════════════════════════════════════════════════════"""