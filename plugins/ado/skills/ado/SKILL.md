---
name: ado
description: Azure DevOps integration for work items, PRs, and code reviews. Use when user asks about ADO, work items, PRs, or code reviews.
---

# Azure DevOps Integration Skill

This skill provides tools to interact with Azure DevOps for work items, pull requests, and code reviews.

## Prerequisites Check

**IMPORTANT: Before using any ADO scripts, verify the following:**

### 1. Check Azure CLI Login Status

Run this script first to verify Azure CLI is configured:

```bash
uv run ./scripts/check_az_login.py
```

**If STATUS is NOT_LOGGED_IN:**
- Instruct the user to run: `az login`
- Wait for them to confirm login before proceeding

**If STATUS is NOT_INSTALLED:**
- Direct user to: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

### 2. Check for Organization and Project

Look in the project's `CLAUDE.md` file for ADO configuration:

```markdown
## Azure DevOps Configuration
- Organization: <org_name>
- Project: <project_name>
```

**If not found, ask the user:**
> "What is your Azure DevOps organization and project name?"
>
> Example: organization=`skype`, project=`scc`

Then add to `CLAUDE.md`:

```markdown
## Azure DevOps Configuration
- Organization: <their_org>
- Project: <their_project>
```

---

## Available Scripts

All scripts are in `./scripts/` and run with `uv run`.

### Work Items

#### Get My Work Items
Get all work items assigned to you (excludes Closed/Resolved/Removed):

```bash
uv run ./scripts/get_my_work_items.py <org> <project>
```

#### Get Work Item Details
Get full details of a work item including description, comments, and parent info:

```bash
uv run ./scripts/get_work_item_details.py <org> <project> <work_item_id>
```

---

### Pull Requests

#### Get PRs Assigned to Me (for review)

```bash
uv run ./scripts/get_my_prs.py <org> <project>
```

#### Get PRs Created by Me

```bash
uv run ./scripts/get_my_created_prs.py <org> <project>
```

#### Get PR Details (for code review)
Downloads PR info, comments, original files, modified files, and diffs to a temp folder:

```bash
uv run ./scripts/get_pr_details.py <org> <project> <pr_id>
```

**Output:**
- `summary.md` - LLM-friendly PR metadata and comments
- `original/` - Original file versions
- `modified/` - Modified file versions
- `diffs/` - Unified diff files

---

### PR Comments

#### Get Comments (LLM-friendly format)

```bash
# Get all comments
uv run ./scripts/pr_comment.py <org> <project> <pr_id> get

# Get comments since timestamp
uv run ./scripts/pr_comment.py <org> <project> <pr_id> get --since "2026-01-13 10:00:00"
```

#### Reply to a Comment Thread

```bash
uv run ./scripts/pr_comment.py <org> <project> <pr_id> reply <thread_id> "Your response"
```

#### Create New Comment on File/Line Range

```bash
uv run ./scripts/pr_comment.py <org> <project> <pr_id> new "path/to/file.cs" <start_line> <end_line> "Your comment"
```

**Examples:**
```bash
# Single line comment
uv run ./scripts/pr_comment.py <org> <project> <pr_id> new "src/main.cs" 42 42 "Consider refactoring"

# Multi-line comment (lines 10-15)
uv run ./scripts/pr_comment.py <org> <project> <pr_id> new "src/main.cs" 10 15 "This block needs error handling"
```

#### Create General PR Comment

```bash
uv run ./scripts/pr_comment.py <org> <project> <pr_id> general "Overall feedback here"
```

---

## Code Review Workflow

When asked to review a PR:

1. **Get PR details and files:**
   ```bash
   uv run ./scripts/get_pr_details.py <org> <project> <pr_id>
   ```

2. **Read the summary.md** from the temp folder output

3. **Read the diff files** to understand changes

4. **For each issue found:**
   - If code change needed: note the file and line
   - Add a comment:
     ```bash
     uv run ./scripts/pr_comment.py <org> <project> <pr_id> new "file.cs" <line> <line> "feedback"
     ```

5. **For overall feedback:**
   ```bash
   uv run ./scripts/pr_comment.py <org> <project> <pr_id> general "LGTM with minor suggestions"
   ```

---

## Responding to Review Comments

When asked to address review comments:

1. **Get current comments:**
   ```bash
   uv run ./scripts/pr_comment.py <org> <project> <pr_id> get
   ```

2. **For each actionable comment:**
   - Read the file and line mentioned
   - Make the requested changes
   - Reply to acknowledge:
     ```bash
     uv run ./scripts/pr_comment.py <org> <project> <pr_id> reply <thread_id> "Fixed - updated the implementation"
     ```

3. **For comments since last check:**
   ```bash
   uv run ./scripts/pr_comment.py <org> <project> <pr_id> get --since "2026-01-13 10:00:00"
   ```

---

## Notes

- All scripts use Azure CLI token authentication (`az account get-access-token`)
- Scripts output is designed to be LLM-friendly for parsing
- File paths in comments should NOT start with `/` when running from Git Bash on Windows
- Line ranges show as `lines X-Y` for multi-line comments
