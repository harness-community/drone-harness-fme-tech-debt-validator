"""Git operations for code change detection."""

import logging
import os
import subprocess
import requests
from typing import Dict, List

try:
    from git import Repo
except ImportError:
    Repo = None

from ..extractors import (
    extract_flags_ast_javascript,
    extract_flags_ast_java,
    extract_flags_ast_python,
    extract_flags_ast_csharp,
    extract_flags_regex
)

logger = logging.getLogger(__name__)


class GitCodeAnalyzer:
    """Handles git operations and code analysis for feature flag detection."""
    
    def __init__(self, config: Dict[str, str]):
        self.commit_before = config["commit_before"]
        self.commit_after = config["commit_after"]
        self.api_base_url = config.get("api_base_url", "https://app.harness.io")
        self.harness_token = config["harness_token"]
        self.harness_account = config["harness_account"]
        self.harness_org = config["harness_org"]
        self.harness_project = config["harness_project"]
        
        self.flag_file_mapping = {}  # Track which files contain which flags

    def get_code_changes(self) -> List[str]:
        """Get list of changed files between commits using Harness Code Repository API"""
        try:
            # Try Harness Code API first
            drone_repo = os.getenv("DRONE_REPO_NAME")
            repo_name = drone_repo.split("/")[-1] if drone_repo else None
            api_token = self.harness_token
            account_id = self.harness_account
            org_id = self.harness_org
            project_id = self.harness_project            
            if repo_name and api_token and account_id:
                url = f"{self.api_base_url}/code/api/v1/repos/{repo_name}/diff/{self.commit_before}...{self.commit_after}"
                headers = {
                    "x-api-key": api_token
                }
                querystring = {"accountIdentifier": account_id, "orgIdentifier": org_id, "projectIdentifier": project_id}
                
                logger.info(f"Fetching changes from Harness API: {self.commit_before}...{self.commit_after}")
                response = requests.get(url, headers=headers, params=querystring)
                response.raise_for_status()
                
                data = response.json()
                # Handle both array response and object with 'files' key
                if isinstance(data, list):
                    changed_files = [file['path'] for file in data]
                else:
                    changed_files = [file['path'] for file in data.get('files', [])]
                
                logger.info(f"Found {len(changed_files)} changed files via Harness API")
                return changed_files
            
            # Fallback to GitPython/subprocess
            logger.warning("Harness API credentials not available, falling back to local git")
            if Repo is None:
                logger.error("GitPython not available, falling back to subprocess")
                result = subprocess.run(
                    [
                        "git",
                        "diff",
                        "--name-only",
                        self.commit_before,
                        self.commit_after,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                changed_files = (
                    result.stdout.strip().split("\n")
                    if result.stdout.strip()
                    else []
                )
            else:
                repo = Repo('.')
                diff_output = repo.git.diff('--name-only', self.commit_before, self.commit_after)
                changed_files = diff_output.strip().split('\n') if diff_output.strip() else []
            
            logger.info(
                f"Found {len(changed_files)} changed files between {self.commit_before} and {self.commit_after}"
            )
            return changed_files
        except Exception as e:
            logger.error(f"Failed to get code changes: {e}")
            return []

    def analyze_code_for_flags(self, changed_files: List[str]) -> List[str]:
        """Search for feature flags using AST parsing with regex fallback"""
        feature_flags = []
        self.flag_file_mapping = {}  # Reset mapping

        # Get all changed files and analyze them
        for file_path in changed_files:
            try:
                # Read the current content of the file
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Determine parsing method based on file extension
                file_flags = []
                if file_path.endswith(".js") or file_path.endswith(".jsx"):
                    file_flags = extract_flags_ast_javascript(file_content)
                    method = "JavaScript AST"
                elif file_path.endswith(".java"):
                    file_flags = extract_flags_ast_java(file_content)
                    method = "Java AST"
                elif file_path.endswith(".py"):
                    file_flags = extract_flags_ast_python(file_content)
                    method = "Python AST"
                elif file_path.endswith(".cs"):
                    file_flags = extract_flags_ast_csharp(file_content)
                    method = "C# AST"
                else:
                    file_flags = extract_flags_regex(file_content)
                    method = "Regex"

                # If AST parsing failed or returned nothing, fall back to regex
                if not file_flags and method != "Regex":
                    file_flags = extract_flags_regex(file_content)
                    method += " (fallback to Regex)"

                if file_flags:
                    logger.info(
                        f"Found {len(file_flags)} flags in {file_path} using {method}: {file_flags}"
                    )
                    feature_flags.extend(file_flags)

                    # Track which files contain which flags
                    for flag in file_flags:
                        if flag not in self.flag_file_mapping:
                            self.flag_file_mapping[flag] = []
                        self.flag_file_mapping[flag].append(file_path)
                else:
                    logger.debug(
                        f"No flags found in {file_path} using {method}"
                    )

            except (FileNotFoundError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read file {file_path}: {e}")
                continue

        # Remove duplicates
        feature_flags = list(set(feature_flags))
        logger.info(
            f"Total unique feature flags found: {len(feature_flags)} - {feature_flags}"
        )
        return feature_flags