"""
LLM Client for interacting with OpenAI API.
Handles structured outputs and error handling.
"""

import json
import logging
from typing import Optional, Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Client for LLM interactions with structured output support."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((json.JSONDecodeError, KeyError))
    )
    def generate(self, messages: list, response_model: Optional[Type[T]] = None) -> T | str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with role and content
            response_model: Optional Pydantic model for structured output
            
        Returns:
            Parsed Pydantic model if response_model provided, else raw string
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"} if response_model else None
            )
            
            content = response.choices[0].message.content
            
            if response_model:
                parsed_json = json.loads(content)
                return response_model.model_validate(parsed_json)
            
            return content
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {content}")
            raise
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    def generate_with_fallback(
        self, 
        messages: list, 
        response_model: Type[T],
        fallback_value: T
    ) -> T:
        """
        Generate with a fallback value if all retries fail.
        
        Args:
            messages: List of message dicts
            response_model: Pydantic model for parsing
            fallback_value: Value to return if generation fails
            
        Returns:
            Parsed response or fallback value
        """
        try:
            return self.generate(messages, response_model)
        except Exception as e:
            logger.warning(f"Using fallback value due to error: {e}")
            return fallback_value
