#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Get detailed information about an Azure DevOps work item.
Includes title, description, comments, and parent details.

Usage:
    uv run get_work_item_details.py <organization> <project> <work_item_id>

Example:
    uv run get_work_item_details.py skype scc 12345
"""

import subprocess
import json
import sys
import requests
import re

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_azure_token():
    """Get access token from Azure CLI for Azure DevOps."""
    resource = "499b84ac-1321-427f-aa17-267ca6975798"

    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource],
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode != 0:
        print(f"Error getting token: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    token_data = json.loads(result.stdout)
    return token_data["accessToken"]


def get_work_item(organization, project, work_item_id, token):
    """Get work item details with relations."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{work_item_id}?$expand=relations&api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_work_item_comments(organization, project, work_item_id, token):
    """Get all comments for a work item."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workItems/{work_item_id}/comments?api-version=7.1-preview.4"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("comments", [])


def find_parent_id(work_item):
    """Find parent work item ID from relations."""
    relations = work_item.get("relations", [])
    if not relations:
        return None

    for relation in relations:
        # Parent link type
        if relation.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
            # URL format: https://dev.azure.com/{org}/{project}/_apis/wit/workItems/{id}
            url = relation.get("url", "")
            match = re.search(r"/workItems/(\d+)$", url)
            if match:
                return int(match.group(1))

    return None


def strip_html(text):
    """Remove HTML tags from text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&#39;', "'")
    # Collapse multiple whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def print_work_item_details(work_item, comments, label="Work Item"):
    """Print work item details in LLM-friendly markdown format."""
    fields = work_item.get("fields", {})

    item_id = work_item.get("id", "N/A")
    title = fields.get("System.Title", "N/A")
    work_type = fields.get("System.WorkItemType", "N/A")
    state = fields.get("System.State", "N/A")
    assigned_to = fields.get("System.AssignedTo", {})
    if isinstance(assigned_to, dict):
        assigned_to = assigned_to.get("displayName", "Unassigned")
    description = fields.get("System.Description", "")

    print(f"## {label}: #{item_id} [{work_type}]")
    print(f"**Title:** {title}")
    print(f"**State:** {state} | **Assigned:** {assigned_to}")
    print("")
    print("### Description")
    print(strip_html(description) if description else "(No description)")
    print("")

    if comments:
        print(f"### Comments ({len(comments)})")
        for comment in comments:
            author = comment.get("createdBy", {}).get("displayName", "Unknown")
            date = comment.get("createdDate", "")[:10]
            text = strip_html(comment.get("text", ""))
            print(f"- **{author}** ({date}): {text}")


def main():
    if len(sys.argv) < 4:
        print("Usage: uv run get_work_item_details.py <org> <project> <id>", file=sys.stderr)
        sys.exit(1)

    organization = sys.argv[1]
    project = sys.argv[2]
    work_item_id = sys.argv[3]

    print(f"Fetching work item #{work_item_id}...", file=sys.stderr)
    token = get_azure_token()

    work_item = get_work_item(organization, project, work_item_id, token)
    comments = get_work_item_comments(organization, project, work_item_id, token)

    print("# Work Item Details")
    print("")
    print_work_item_details(work_item, comments, "Work Item")

    parent_id = find_parent_id(work_item)
    if parent_id:
        print("")
        parent_item = get_work_item(organization, project, parent_id, token)
        parent_comments = get_work_item_comments(organization, project, parent_id, token)
        print_work_item_details(parent_item, parent_comments, "Parent")


if __name__ == "__main__":
    main()
