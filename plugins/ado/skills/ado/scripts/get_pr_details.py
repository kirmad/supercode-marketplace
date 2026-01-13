#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "requests",
# ]
# ///
"""
Get detailed information about an Azure DevOps pull request.
Downloads original files, modified files, and diffs to a temp folder.

Usage:
    uv run get_pr_details.py <organization> <project> <pr_id>

Example:
    uv run get_pr_details.py skype scc 1329388
"""

import subprocess
import json
import sys
import os
import tempfile
import requests
from datetime import datetime

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


def get_pull_request(organization, project, repo_id, pr_id, token):
    """Get pull request details."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_pull_request_by_id(organization, project, pr_id, token):
    """Get pull request details by PR ID (searches across all repos)."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/pullrequests/{pr_id}?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_pr_threads(organization, project, repo_id, pr_id, token):
    """Get all comment threads for a pull request."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/threads?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("value", [])


def get_pr_iterations(organization, project, repo_id, pr_id, token):
    """Get all iterations for a pull request."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/iterations?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("value", [])


def get_iteration_changes(organization, project, repo_id, pr_id, iteration_id, token):
    """Get file changes for a specific iteration."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/pullrequests/{pr_id}/iterations/{iteration_id}/changes?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json().get("changeEntries", [])


def get_file_content(organization, project, repo_id, object_id, token):
    """Get file content by blob object ID."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/blobs/{object_id}?api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/octet-stream"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return None
    response.raise_for_status()

    return response.content


def get_file_content_from_branch(organization, project, repo_id, file_path, branch_name, token):
    """Get file content from a specific branch using git items API."""
    # URL encode the file path (but keep slashes)
    import urllib.parse
    encoded_path = urllib.parse.quote(file_path, safe='/')

    url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repo_id}/items?path={encoded_path}&versionType=Branch&version={branch_name}&api-version=7.1"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/octet-stream"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return None  # File doesn't exist in target branch (new file)
    response.raise_for_status()

    return response.content


def generate_unified_diff(original_content, modified_content, file_path):
    """Generate a unified diff between two file contents."""
    import difflib

    original_lines = original_content.decode('utf-8', errors='replace').splitlines(keepends=True) if original_content else []
    modified_lines = modified_content.decode('utf-8', errors='replace').splitlines(keepends=True) if modified_content else []

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a{file_path}",
        tofile=f"b{file_path}",
        lineterm=""
    )

    return "".join(diff)


def save_file(folder, subfolder, file_path, content):
    """Save content to a file in the specified folder."""
    if content is None:
        return None

    # Create the directory structure
    full_path = os.path.join(folder, subfolder, file_path.lstrip("/"))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Write content
    with open(full_path, "wb") as f:
        f.write(content)

    return full_path


def save_text_file(folder, filename, content):
    """Save text content to a file."""
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


def generate_markdown_summary(pr_id, title, description, repo_name, source_branch, target_branch,
                               created_by, created_date, threads, files_info):
    """Generate a compact markdown summary for LLM consumption."""
    lines = []

    lines.append(f"# PR #{pr_id}: {title}")
    lines.append(f"**Repo:** {repo_name} | **Branch:** {source_branch} -> {target_branch} | **Author:** {created_by}")
    lines.append("")
    lines.append("## Description")
    lines.append(description if description else "(No description)")
    lines.append("")

    lines.append(f"## Files ({len(files_info)})")
    for f in files_info:
        lines.append(f"- `{f['path']}` ({f['change_type']})")
    lines.append("")

    user_threads = [t for t in threads if any(
        c.get("commentType", "") != "system" for c in t.get("comments", [])
    )]

    if user_threads:
        lines.append(f"## Comments ({len(user_threads)} threads)")
        for thread in user_threads:
            thread_id = thread.get("id")
            thread_context = thread.get("threadContext") or {}
            file_path = thread_context.get("filePath") if thread_context else None
            line_info = ""
            if thread_context:
                right_start = thread_context.get("rightFileStart") or {}
                right_end = thread_context.get("rightFileEnd") or {}
                start_line = right_start.get("line") if right_start else None
                end_line = right_end.get("line") if right_end else None
                if start_line:
                    line_info = f":{start_line}-{end_line}" if end_line and end_line != start_line else f":{start_line}"

            location = f"`{file_path}{line_info}`" if file_path else "General"
            lines.append(f"### Thread #{thread_id} - {location}")
            for comment in thread.get("comments", []):
                if comment.get("commentType") == "system":
                    continue
                author = comment.get("author", {}).get("displayName", "Unknown")
                text = comment.get("content", "").strip()
                lines.append(f"- **{author}**: {text}")
            lines.append("")

    return "\n".join(lines)


def print_threads(threads):
    """Print comment threads (for stderr progress)."""
    user_threads = [t for t in threads if any(
        c.get("commentType", "") != "system" for c in t.get("comments", [])
    )]
    print(f"Found {len(user_threads)} comment thread(s)", file=sys.stderr)


def main():
    if len(sys.argv) < 4:
        print("Usage: uv run get_pr_details.py <org> <project> <pr_id>", file=sys.stderr)
        sys.exit(1)

    organization = sys.argv[1]
    project = sys.argv[2]
    pr_id = sys.argv[3]

    print(f"Fetching PR #{pr_id}...", file=sys.stderr)
    token = get_azure_token()

    pr = get_pull_request_by_id(organization, project, pr_id, token)

    repo_id = pr.get("repository", {}).get("id")
    repo_name = pr.get("repository", {}).get("name", "unknown")
    title = pr.get("title", "N/A")
    description = pr.get("description", "(No description)")
    source_branch = pr.get("sourceRefName", "").replace("refs/heads/", "")
    target_branch = pr.get("targetRefName", "").replace("refs/heads/", "")
    created_by = pr.get("createdBy", {}).get("displayName", "Unknown")
    created_date = pr.get("creationDate", "")[:10]

    threads = get_pr_threads(organization, project, repo_id, pr_id, token)
    print_threads(threads)

    temp_dir = tempfile.mkdtemp(prefix=f"pr_{pr_id}_")

    iterations = get_pr_iterations(organization, project, repo_id, pr_id, token)
    if not iterations:
        print("No iterations found.", file=sys.stderr)
        return

    iteration_id = iterations[-1].get("id")
    changes = get_iteration_changes(organization, project, repo_id, pr_id, iteration_id, token)
    print(f"Processing {len(changes)} file(s)...", file=sys.stderr)

    files_info = []
    for change in changes:
        item = change.get("item", {})
        file_path = item.get("path", "")
        change_type = change.get("changeType", "unknown")
        object_id = item.get("objectId")

        if not file_path:
            continue

        file_info = {"path": file_path, "change_type": change_type}

        modified_content = None
        if object_id:
            modified_content = get_file_content(organization, project, repo_id, object_id, token)
            if modified_content:
                save_file(temp_dir, "modified", file_path, modified_content)

        original_content = None
        if change_type in ("edit", "delete", "rename"):
            original_content = get_file_content_from_branch(
                organization, project, repo_id, file_path, target_branch, token
            )
            if original_content:
                save_file(temp_dir, "original", file_path, original_content)

        if modified_content or original_content:
            diff = generate_unified_diff(original_content or b"", modified_content or b"", file_path)
            if diff:
                diff_filename = file_path.lstrip("/").replace("/", "_") + ".diff"
                save_text_file(os.path.join(temp_dir, "diffs"), diff_filename, diff)

        files_info.append(file_info)

    summary_md = generate_markdown_summary(
        pr_id, title, description, repo_name, source_branch, target_branch,
        created_by, created_date, threads, files_info
    )
    save_text_file(temp_dir, "summary.md", summary_md)

    # Output compact result
    print(f"FOLDER: {temp_dir}")
    print(f"FILES: {len(files_info)} | original/ modified/ diffs/ summary.md")


if __name__ == "__main__":
    main()
