"""
Base agent class that all agents inherit from.
"""

from abc import ABC, abstractmethod
from typing import Any
import logging

from llm.client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    name: str = "BaseAgent"
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        logger.info(f"Initialized {self.name}")
    
    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """
        Execute the agent's main task.
        
        Returns:
            Agent-specific result
        """
        pass
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message with agent context."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"[{self.name}] {message}")
