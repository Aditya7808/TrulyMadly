"""
Planner Agent - Converts user input into structured execution plans.
"""

import json
import logging
from typing import Optional

from llm.client import LLMClient
from llm.prompts import PromptTemplates
from models import ExecutionPlan, PlanStep, ToolType
from .base import BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Planner Agent that analyzes user tasks and creates execution plans.
    
    Responsibilities:
    - Parse natural language tasks
    - Identify required tools
    - Generate step-by-step execution plans
    - Optimize step ordering and dependencies
    """
    
    name = "PlannerAgent"
    
    async def run(self, task: str) -> ExecutionPlan:
        """
        Create an execution plan for the given task.
        
        Args:
            task: Natural language task description
            
        Returns:
            ExecutionPlan with steps and tool assignments
        """
        self.log(f"Creating plan for task: {task[:100]}...")
        
        messages = PromptTemplates.get_planner_messages(task)
        
        try:
            plan = self.llm.generate(messages, ExecutionPlan)
            self.log(f"Generated plan with {len(plan.steps)} steps")
            return plan
            
        except Exception as e:
            self.log(f"Failed to generate plan: {e}", "error")
            return self._create_fallback_plan(task)
    
    def _create_fallback_plan(self, task: str) -> ExecutionPlan:
        """
        Create a basic fallback plan when LLM fails.
        Attempts to extract intent from the task.
        """
        self.log("Using fallback plan generation", "warning")
        
        task_lower = task.lower()
        steps = []
        step_num = 1
        
        github_keywords = ["github", "repo", "repository", "code", "project", "star"]
        weather_keywords = ["weather", "temperature", "forecast", "climate", "rain", "sunny"]
        
        if any(kw in task_lower for kw in github_keywords):
            query = self._extract_search_query(task, "github")
            steps.append(PlanStep(
                step_number=step_num,
                description="Search GitHub repositories",
                tool=ToolType.GITHUB,
                parameters={"query": query, "limit": 5},
                depends_on=[]
            ))
            step_num += 1
        
        if any(kw in task_lower for kw in weather_keywords):
            city = self._extract_city(task)
            steps.append(PlanStep(
                step_number=step_num,
                description=f"Get weather for {city}",
                tool=ToolType.WEATHER,
                parameters={"city": city},
                depends_on=[]
            ))
            step_num += 1
        
        if not steps:
            steps.append(PlanStep(
                step_number=1,
                description="Search GitHub for relevant repositories",
                tool=ToolType.GITHUB,
                parameters={"query": task[:50], "limit": 5},
                depends_on=[]
            ))
        
        return ExecutionPlan(
            task_summary=task[:200],
            steps=steps,
            reasoning="Fallback plan generated from keyword extraction"
        )
    
    def _extract_search_query(self, task: str, context: str) -> str:
        """Extract a search query from the task."""
        words = task.split()
        skip_words = {"find", "search", "get", "show", "list", "the", "a", "an", 
                      "for", "in", "on", "github", "weather", "and", "with", "top"}
        query_words = [w for w in words if w.lower() not in skip_words]
        return " ".join(query_words[:5]) if query_words else "popular repositories"
    
    def _extract_city(self, task: str) -> str:
        """Extract city name from the task."""
        common_cities = [
            "new york", "london", "tokyo", "paris", "berlin", "sydney",
            "mumbai", "singapore", "dubai", "san francisco", "los angeles",
            "chicago", "seattle", "boston", "toronto", "vancouver"
        ]
        
        task_lower = task.lower()
        for city in common_cities:
            if city in task_lower:
                return city.title()
        
        words = task.split()
        for i, word in enumerate(words):
            if word.lower() in ["in", "for", "at"]:
                if i + 1 < len(words):
                    potential_city = words[i + 1].strip(".,!?")
                    if potential_city[0].isupper():
                        return potential_city
        
        return "London"
