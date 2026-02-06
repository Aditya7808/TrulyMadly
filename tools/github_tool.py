"""
GitHub API tool for searching repositories and fetching details.
"""

import logging
from typing import Optional, List
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import ToolResult, ToolType, GitHubRepository
from .base import BaseTool

logger = logging.getLogger(__name__)


class GitHubTool(BaseTool):
    """Tool for interacting with GitHub API."""
    
    name = "GitHub"
    tool_type = ToolType.GITHUB
    description = "Search GitHub repositories and fetch repository information"
    
    def __init__(self):
        self.base_url = settings.github_api_base
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Ops-Assistant"
        }
        if settings.github_token:
            self.headers["Authorization"] = f"token {settings.github_token}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make an authenticated request to GitHub API."""
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def execute(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        limit: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        Search GitHub repositories.
        
        Args:
            query: Search query string
            sort: Sort by (stars, forks, updated)
            order: Order direction (asc, desc)
            limit: Maximum number of results (1-10)
            
        Returns:
            ToolResult with list of repositories
        """
        try:
            limit = max(1, min(10, limit))
            
            params = {
                "q": query,
                "sort": sort,
                "order": order,
                "per_page": limit
            }
            
            logger.info(f"Searching GitHub for: {query}")
            data = await self._make_request("/search/repositories", params)
            
            repositories = []
            for item in data.get("items", [])[:limit]:
                repo = {
                    "name": item.get("name", ""),
                    "full_name": item.get("full_name", ""),
                    "description": item.get("description"),
                    "stargazers_count": item.get("stargazers_count", 0),
                    "forks_count": item.get("forks_count", 0),
                    "language": item.get("language"),
                    "html_url": item.get("html_url", "")
                }
                repositories.append(GitHubRepository.model_validate(repo))
            
            return self._create_result(
                success=True,
                data={
                    "total_count": data.get("total_count", 0),
                    "repositories": [r.model_dump() for r in repositories]
                }
            )
            
        except httpx.HTTPStatusError as e:
            error_msg = f"GitHub API error: {e.response.status_code}"
            if e.response.status_code == 403:
                error_msg += " (Rate limit exceeded)"
            elif e.response.status_code == 422:
                error_msg += " (Invalid query)"
            logger.error(error_msg)
            return self._create_result(success=False, error=error_msg)
            
        except Exception as e:
            logger.error(f"GitHub tool error: {e}")
            return self._create_result(success=False, error=str(e))
    
    async def get_repository(self, owner: str, repo: str) -> ToolResult:
        """
        Get details for a specific repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            ToolResult with repository details
        """
        try:
            data = await self._make_request(f"/repos/{owner}/{repo}")
            
            repo_data = {
                "name": data.get("name", ""),
                "full_name": data.get("full_name", ""),
                "description": data.get("description"),
                "stargazers_count": data.get("stargazers_count", 0),
                "forks_count": data.get("forks_count", 0),
                "language": data.get("language"),
                "html_url": data.get("html_url", "")
            }
            
            repository = GitHubRepository.model_validate(repo_data)
            return self._create_result(success=True, data=repository.model_dump())
            
        except Exception as e:
            logger.error(f"Failed to get repository {owner}/{repo}: {e}")
            return self._create_result(success=False, error=str(e))
