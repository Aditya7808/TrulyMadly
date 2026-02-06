"""
Base tool class and tool registry.
All tools must inherit from BaseTool.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time

from models import ToolResult, ToolType

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    name: str = ""
    tool_type: ToolType = None
    description: str = ""
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Returns:
            ToolResult with success status and data/error
        """
        pass
    
    def _create_result(
        self, 
        success: bool, 
        data: Optional[Any] = None, 
        error: Optional[str] = None,
        execution_time_ms: float = 0
    ) -> ToolResult:
        """Helper to create a standardized ToolResult."""
        return ToolResult(
            tool=self.tool_type,
            success=success,
            data=data,
            error=error,
            execution_time_ms=execution_time_ms
        )
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """
        Execute with timing and error handling.
        
        Returns:
            ToolResult with execution time tracked
        """
        start_time = time.time()
        try:
            result = await self.execute(**kwargs)
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Tool {self.name} failed: {e}")
            return self._create_result(
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )


class ToolRegistry:
    """Registry for managing available tools."""
    
    _tools: Dict[ToolType, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        cls._tools[tool.tool_type] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    @classmethod
    def get(cls, tool_type: ToolType) -> Optional[BaseTool]:
        """Get a tool by type."""
        return cls._tools.get(tool_type)
    
    @classmethod
    def get_all(cls) -> Dict[ToolType, BaseTool]:
        """Get all registered tools."""
        return cls._tools.copy()
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools."""
        cls._tools.clear()
