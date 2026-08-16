"""
GitHub Workspace Integration Plugin.
Provides repository search, issue reading, pull request creation, and file commits.
"""
from typing import List, Dict, Any
from core.plugins.base_plugin import BasePlugin
from core.skills import Skill

class GithubPlugin(BasePlugin):
    @property
    def plugin_id(self) -> str:
        return "github"

    @property
    def display_name(self) -> str:
        return "GitHub Code Workspace"

    def get_skills(self, config: Dict[str, Any]) -> List[Skill]:
        token = config.get("token", "")
        default_repo = config.get("repository", "")

        def github_search_repos(query: str) -> str:
            """
            Search repositories on GitHub.
            """
            if token:
                try:
                    import httpx
                    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
                    res = httpx.get(f"https://api.github.com/search/repositories?q={query}", headers=headers)
                    if res.status_code == 200:
                        repos = res.json().get("items", [])[:3]
                        return "\n".join(f"- {r['full_name']}: {r['description']}" for r in repos)
                    return f"GitHub API Error: HTTP {res.status_code}"
                except Exception as e:
                    return f"Failed to connect to GitHub: {e}"
            else:
                return f"[GITHUB SIMULATION] Found repositories for query '{query}':\n- mock-user/cool-agent-os: Agent OS Core Repo\n- mock-user/adgents: Main Framework Node"

        def github_get_issue(issue_number: int, repo: str = default_repo) -> str:
            """
            Read details of a GitHub issue.
            """
            if token and repo:
                try:
                    import httpx
                    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
                    res = httpx.get(f"https://api.github.com/repos/{repo}/issues/{issue_number}", headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        return f"Issue #{issue_number}: {data.get('title')}\nState: {data.get('state')}\nBody: {data.get('body')}"
                    return f"GitHub API Error: HTTP {res.status_code}"
                except Exception as e:
                    return f"Failed to connect to GitHub: {e}"
            else:
                return f"[GITHUB SIMULATION] Issue #{issue_number} in repo '{repo}':\nTitle: Bug: Memory leak in self-healing retry loop\nState: open\nCreated by: developer-agent"

        def github_create_pr(title: str, head: str, base: str = "main", body: str = "", repo: str = default_repo) -> str:
            """
            Create a pull request.
            """
            if token and repo:
                try:
                    import httpx
                    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
                    data = {"title": title, "head": head, "base": base, "body": body}
                    res = httpx.post(f"https://api.github.com/repos/{repo}/pulls", headers=headers, json=data)
                    if res.status_code == 201:
                        pr_info = res.json()
                        return f"PR created successfully: {pr_info.get('html_url')}"
                    return f"Failed to create PR: HTTP {res.status_code} - {res.text}"
                except Exception as e:
                    return f"Failed to connect to GitHub: {e}"
            else:
                print(f"[GITHUB SIMULATION] Created pull request '{title}' in {repo} merging {head} -> {base}")
                return f"Simulated PR created successfully: https://github.com/{repo}/pull/42 (Mocked merging {head} into {base})"

        def github_commit_changes(path: str, content: str, message: str, branch: str = "main", repo: str = default_repo) -> str:
            """
            Commit a file modification directly to GitHub.
            """
            if token and repo:
                try:
                    import httpx
                    import base64
                    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
                    # Get sha of file if exists
                    sha = None
                    res_get = httpx.get(f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}", headers=headers)
                    if res_get.status_code == 200:
                        sha = res_get.json().get("sha")
                    
                    data = {
                        "message": message,
                        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
                        "branch": branch
                    }
                    if sha:
                        data["sha"] = sha
                        
                    res_put = httpx.put(f"https://api.github.com/repos/{repo}/contents/{path}", headers=headers, json=data)
                    if res_put.status_code in (200, 201):
                        return f"Successfully committed changes to '{path}' on branch '{branch}' in repository '{repo}'"
                    return f"Commit failed: HTTP {res_put.status_code} - {res_put.text}"
                except Exception as e:
                    return f"GitHub connection failed: {e}. (Mocked Success: Committed to '{path}')"
            else:
                print(f"[GITHUB SIMULATION] Committed file '{path}' to branch '{branch}' in '{repo}' with message: '{message}'")
                return f"Simulated Commit Successful: committed changes to '{path}' in repository '{repo}' (branch: '{branch}')."

        return [
            Skill(
                name="github_search_repos",
                description="Search for GitHub repositories by query string",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term"}
                    },
                    "required": ["query"]
                },
                handler=github_search_repos,
                category="integration"
            ),
            Skill(
                name="github_get_issue",
                description="Get issue details by issue number",
                parameters={
                    "type": "object",
                    "properties": {
                        "issue_number": {"type": "integer", "description": "GitHub issue number"},
                        "repo": {"type": "string", "description": "Target repo format: 'owner/name'"}
                    },
                    "required": ["issue_number"]
                },
                handler=github_get_issue,
                category="integration"
            ),
            Skill(
                name="github_create_pr",
                description="Create a new Pull Request",
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Pull request title"},
                        "head": {"type": "string", "description": "Name of the branch containing changes"},
                        "base": {"type": "string", "description": "Branch to merge changes into (default: 'main')"},
                        "body": {"type": "string", "description": "PR description text"},
                        "repo": {"type": "string", "description": "Target repo format: 'owner/name'"}
                    },
                    "required": ["title", "head"]
                },
                handler=github_create_pr,
                category="integration"
            ),
            Skill(
                name="github_commit_changes",
                description="Commit content edits directly to a file in the repository",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to commit inside repo"},
                        "content": {"type": "string", "description": "Complete file content body"},
                        "message": {"type": "string", "description": "Git commit message"},
                        "branch": {"type": "string", "description": "Git branch name"},
                        "repo": {"type": "string", "description": "Target repo format: 'owner/name'"}
                    },
                    "required": ["path", "content", "message"]
                },
                handler=github_commit_changes,
                category="integration"
            )
        ]
