#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Get all Azure DevOps pull requests assigned to me as a reviewer.

Usage:
    uv run get_my_prs.py <organization> <project>

Example:
    uv run get_my_prs.py skype scc
"""

import subprocess
import json
import sys
import requests

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


def get_current_user_id(organization, token):
    """Get the current authenticated user's ID."""
    url = f"https://vssps.dev.azure.com/{organization}/_apis/profile/profiles/me?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("id")


def get_pull_requests_for_reviewer(organization, project, reviewer_id, token):
    """Get all active pull requests where user is a reviewer."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/pullrequests"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    params = {
        "searchCriteria.reviewerId": reviewer_id,
        "searchCriteria.status": "active",
        "$top": 100,
        "api-version": "7.1"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json().get("value", [])


def get_vote_status(vote):
    """Convert vote number to status string."""
    vote_map = {
        10: "Approved",
        5: "Approved with suggestions",
        0: "No vote",
        -5: "Waiting for author",
        -10: "Rejected"
    }
    return vote_map.get(vote, f"Unknown ({vote})")


def print_pull_requests(prs, current_user_id):
    """Print pull requests in LLM-friendly markdown format."""
    if not prs:
        print("No PRs found for review.")
        return

    print(f"# PRs for Review ({len(prs)})")
    print("")

    for pr in prs:
        pr_id = pr.get("pullRequestId", "N/A")
        title = pr.get("title", "N/A")
        repo = pr.get("repository", {}).get("name", "N/A")
        source_branch = pr.get("sourceRefName", "").replace("refs/heads/", "")
        target_branch = pr.get("targetRefName", "").replace("refs/heads/", "")
        created_by = pr.get("createdBy", {}).get("displayName", "Unknown")

        my_vote = 0
        for reviewer in pr.get("reviewers", []):
            if reviewer.get("id") == current_user_id:
                my_vote = reviewer.get("vote", 0)
                break

        print(f"- **PR #{pr_id}**: {title}")
        print(f"  - Repo: {repo} | {source_branch} -> {target_branch}")
        print(f"  - Author: {created_by} | Vote: {get_vote_status(my_vote)}")


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run get_my_prs.py <org> <project>", file=sys.stderr)
        sys.exit(1)

    organization = sys.argv[1]
    project = sys.argv[2]

    print("Fetching PRs...", file=sys.stderr)
    token = get_azure_token()

    user_id = get_current_user_id(organization, token)
    if not user_id:
        print("Error: Could not get current user ID", file=sys.stderr)
        sys.exit(1)

    prs = get_pull_requests_for_reviewer(organization, project, user_id, token)
    print_pull_requests(prs, user_id)


if __name__ == "__main__":
    main()
