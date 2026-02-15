#!/usr/bin/env python3
"""
Update Terraform EKS Module Versions

This script fetches the active Amazon EKS versions from the endoflife.date API
and updates the `variables.tf` file of the EKS Terraform module.
It ensures that the `cluster_version` validation block and error message
reflect the currently supported versions.

Usage:
    python3 version_restrictor.py [path/to/variables.tf]
"""

import json
import logging
import os
import re
import sys
import urllib.request
import urllib.error
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

API_URL = "https://endoflife.date/api/v1/products/amazon-eks"
DEFAULT_MODULE_VARIABLES_FILE = "modules/eks/variables.tf"


def get_active_eks_versions(url: str) -> List[str]:
    """
    Fetches active (non-EOL) EKS versions from the API using urllib.

    Args:
        url: The API URL to fetch versions from.

    Returns:
        A list of active EKS version strings (e.g., ["1.29", "1.30"]).

    Raises:
        urllib.error.URLError: If the API request fails.
    """
    try:
        logger.info(f"Fetching EKS versions")
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                raise urllib.error.HTTPError(url, response.status, "HTTP Error", response.headers, None)
            data = json.loads(response.read().decode())

        # Handle simplified list response or nested 'result' structure
        releases = []
        if isinstance(data, dict) and "result" in data and "releases" in data["result"]:
            releases = data["result"]["releases"]
        elif isinstance(data, list):
            releases = data
        else:
            logger.error(f"Unexpected API response structure. Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            sys.exit(1)

        active_versions = []
        for release in releases:
            # We want active versions, so checks for isEol == False
            if release.get("isEol") is False:
                active_versions.append(release["name"])

        if not active_versions:
            logger.warning("No active EKS versions found in API response.")

        logger.info(f"Found active versions: {active_versions}")
        return active_versions

    except (urllib.error.URLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to fetch versions from API: {e}")
        raise


def update_terraform_file(file_path: str, versions: List[str]) -> None:
    """
    Updates the Terraform variables file with the allowed EKS versions.

    Args:
        file_path: Path to the variables.tf file.
        versions: List of version strings to allow.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Sort versions numerically
        try:
            sorted_versions = sorted(versions, key=lambda s: [int(u) for u in s.split(".")])
        except ValueError:
            logger.warning("Could not sort versions numerically. Falling back to lexical sort.")
            sorted_versions = sorted(versions)

        # Prepare new list string for Terraform
        new_list_str = ", ".join([f'"{v}"' for v in sorted_versions])

        # Regex to find the `contains([...], ...)` block
        # Group 1 is content inside [...]
        condition_regex = r"contains\(\[(.*?)\]"
        match = re.search(condition_regex, content)

        if not match:
            logger.error(f"Could not find 'contains([...])' validation block in {file_path}")
            sys.exit(1)

        # Replace valid versions list
        # using slice replacement to preserve surrounding formatting
        start_idx, end_idx = match.span(1)
        new_content = content[:start_idx] + new_list_str + content[end_idx:]

        # Update error_message
        # Regex to capture 'error_message = ...' until end of line or closing brace if inline
        # Robustly handles missing quotes by capturing everything after '='
        error_msg_regex = r"(error_message\s*=\s*)(.*)"
        error_match = re.search(error_msg_regex, new_content)

        if error_match:
            new_error_msg_val = (
                f'"The cluster_version must be one of: {", ".join(sorted_versions)}."'
            )
            estart_idx, eend_idx = error_match.span(2)
            new_content = (
                new_content[:estart_idx] + new_error_msg_val + new_content[eend_idx:]
            )
        else:
            logger.warning("Could not find 'error_message' to update.")

        # Write changes back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info(f"Successfully updated {file_path}")

    except IOError as e:
        logger.error(f"File I/O error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error updating file: {e}")
        sys.exit(1)


def main():
    # Use sys.argv for simple argument parsing
    # sys.argv[0] is the script name
    # sys.argv[1] would be the first argument if provided
    file_path = DEFAULT_MODULE_VARIABLES_FILE
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    try:
        active_versions = get_active_eks_versions(API_URL)
        if active_versions:
            update_terraform_file(file_path, active_versions)
        else:
            logger.error("No active versions retrieved. Aborting update.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
