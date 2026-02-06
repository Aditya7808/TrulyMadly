"""
LLM package for AI Operations Assistant.
Provides structured LLM interactions with OpenAI.
"""

from .client import LLMClient
from .prompts import PromptTemplates

__all__ = ["LLMClient", "PromptTemplates"]
