"""Harness API client for feature flag operations."""

import logging
import requests
from typing import Dict
from splitapiclient.main import get_client
from formatters import ErrorMessageFormatter

logger = logging.getLogger(__name__)


class HarnessApiClient:
    """Handles all Harness API interactions for feature flag data."""

    def __init__(self, config: Dict[str, str]):
        self.api_base_url = config.get("api_base_url", "https://app.harness.io")
        self.harness_token = config["harness_token"]
        self.harness_account = config["harness_account"]
        self.harness_org = config["harness_org"]
        self.harness_project = config["harness_project"]
        self.production_environment_name = config.get("production_environment_name", "Production")

        self.client = get_client(
            {
                "harness_mode": True,
                "harness_token": self.harness_token,
                "account_identifier": self.harness_account,
            }
        )

        self.flag_data = []
        self.meta_flag_data = {}

    def fetch_flags(self) -> bool:
        """Fetch feature flags from Harness API."""
        try:
            # Fetch projects with timeout and error handling
            url = (
                f"{self.api_base_url}/ng/api/projects/{self.harness_project}"
                f"?accountIdentifier={self.harness_account}"
                f"&orgIdentifier={self.harness_org}"
            )

            headers = {"x-api-key": self.harness_token}

            logger.info(f"Fetching projects from Harness API: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            try:
                projects_data = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from Harness API: {e}")
                return False

            # Validate response structure
            if not isinstance(projects_data, dict) or "data" not in projects_data:
                logger.error("Unexpected response structure from Harness API")
                return False

            harness_project = projects_data["data"]["project"]

            # Get workspace and flag data with error handling
            try:
                workspace = self.client.workspaces.find(harness_project["name"])
                if not workspace:
                    logger.error(f"Workspace not found for project: {harness_project['name']}")
                    return False

                logger.info(f"Found workspace: {workspace.id}")

                metaFlagDefs = self.client.splits.list(workspace.id)
                # Convert to dictionary for faster lookups by flag name
                self.meta_flag_data = {flag.name: flag for flag in metaFlagDefs}
                logger.info(f"Loaded {len(self.meta_flag_data)} flag definitions")

                environment = self.client.environments.find(self.production_environment_name, workspace.id)

                production_env_found = False
                if environment:
                    production_env_found = True
                    logger.info(f"Found production environment: {environment.name}")

                    flagDefs = self.client.split_definitions.list(workspace.id, environment.id)
                    for flagDef in flagDefs:
                        self.flag_data.append(flagDef)

                    logger.info(f"Loaded {len(self.flag_data)} production flag configurations")

                if not production_env_found:
                    logger.warning(f"Production environment '{self.production_environment_name}' not found")

            except Exception as e:
                logger.error(f"Error accessing Harness Split.io client: {e}")
                return False

            return True

        except requests.exceptions.Timeout:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Connection Timeout",
                "Request to Harness API timed out after 30 seconds",
                [
                    "Check your network connectivity",
                    "Verify firewall settings allow HTTPS to app.harness.io",
                    "Try running the curl command manually to test connectivity",
                    "Check if Harness API is experiencing downtime",
                ],
            )
            logger.error(error_msg)
            return False
        except requests.exceptions.ConnectionError:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Network Connection Error",
                "Cannot establish connection to Harness API",
                [
                    "Check internet connectivity",
                    "Verify DNS resolution for app.harness.io",
                    "Check proxy settings if behind corporate firewall",
                    "Try accessing https://app.harness.io in browser",
                ],
            )
            logger.error(error_msg)
            return False
        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, "status_code", "Unknown")
            error_suggestions = []

            if status_code == 401:
                error_suggestions = [
                    "Verify HARNESS_API_TOKEN is correct and not expired",
                    "Check if token has required permissions for Feature Flags",
                    "Generate a new API token from Harness UI if needed",
                ]
            elif status_code == 403:
                error_suggestions = [
                    "API token lacks permissions for this project",
                    "Verify HARNESS_ACCOUNT_ID and HARNESS_PROJECT_ID are correct",
                    "Check token permissions in Harness Access Control",
                ]
            elif status_code == 404:
                error_suggestions = [
                    "Verify project exists and IDs are correct",
                    "Check if project has Feature Flags enabled",
                    "Confirm account/org/project hierarchy is correct",
                ]
            else:
                error_suggestions = [
                    "Check Harness API status page for known issues",
                    "Retry the operation after a brief delay",
                    "Contact Harness support if problem persists",
                ]

            error_msg = ErrorMessageFormatter.format_api_error(f"HTTP {status_code} Error", str(e), error_suggestions)
            logger.error(error_msg)
            return False
        except requests.exceptions.RequestException as e:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Request Error",
                str(e),
                [
                    "Check if all required environment variables are set",
                    "Verify API endpoint URL is correct",
                    "Check request format and headers",
                    "Review network configuration",
                ],
            )
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = ErrorMessageFormatter.format_api_error(
                "Unexpected Error",
                str(e),
                [
                    "Check all environment variables are properly set",
                    "Verify Python dependencies are installed correctly",
                    "Enable debug logging for more details",
                    "Report this issue if it persists",
                ],
            )
            logger.error(error_msg)
            return False
