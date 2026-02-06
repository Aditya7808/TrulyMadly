"""
Verifier Agent - Validates results and produces final output.
"""

import json
import logging
from typing import Dict, Any, List

from llm.client import LLMClient
from llm.prompts import PromptTemplates
from models import (
    ExecutionResult, VerificationResult, StepStatus,
    ToolType
)
from .base import BaseAgent

logger = logging.getLogger(__name__)


class VerifierAgent(BaseAgent):
    """
    Verifier Agent that validates execution results and formats output.
    
    Responsibilities:
    - Validate completeness of results
    - Identify missing or incorrect data
    - Format final user-facing response
    - Suggest retries for failed steps
    """
    
    name = "VerifierAgent"
    
    async def run(
        self, 
        task: str, 
        execution_result: ExecutionResult
    ) -> VerificationResult:
        """
        Verify execution results and create final output.
        
        Args:
            task: Original user task
            execution_result: Results from executor
            
        Returns:
            VerificationResult with validation and formatted output
        """
        self.log("Verifying execution results")
        
        try:
            plan_summary = self._summarize_plan(execution_result.plan)
            results_summary = self._summarize_results(execution_result)
            
            messages = PromptTemplates.get_verifier_messages(
                task=task,
                plan=plan_summary,
                results=results_summary
            )
            
            verification = self.llm.generate(messages, VerificationResult)
            self.log(f"Verification complete: score={verification.completeness_score:.2f}")
            return verification
            
        except Exception as e:
            self.log(f"LLM verification failed: {e}", "error")
            return self._create_fallback_verification(task, execution_result)
    
    def _summarize_plan(self, plan) -> str:
        """Create a text summary of the plan."""
        lines = [f"Task: {plan.task_summary}", "Steps:"]
        for step in plan.steps:
            lines.append(f"  {step.step_number}. {step.description} (tool: {step.tool.value})")
        return "\n".join(lines)
    
    def _summarize_results(self, execution_result: ExecutionResult) -> str:
        """Create a text summary of execution results."""
        lines = []
        for step_result in execution_result.step_results:
            status = step_result.status.value
            lines.append(f"Step {step_result.step_number}: {status}")
            
            if step_result.tool_result and step_result.tool_result.data:
                data_str = json.dumps(step_result.tool_result.data, indent=2, default=str)
                if len(data_str) > 1000:
                    data_str = data_str[:1000] + "..."
                lines.append(f"  Data: {data_str}")
            
            if step_result.error_message:
                lines.append(f"  Error: {step_result.error_message}")
        
        return "\n".join(lines)
    
    def _create_fallback_verification(
        self, 
        task: str, 
        execution_result: ExecutionResult
    ) -> VerificationResult:
        """Create a basic verification when LLM fails."""
        self.log("Using fallback verification", "warning")
        
        completed_steps = [
            r for r in execution_result.step_results 
            if r.status == StepStatus.COMPLETED
        ]
        failed_steps = [
            r for r in execution_result.step_results 
            if r.status == StepStatus.FAILED
        ]
        
        total_steps = len(execution_result.step_results)
        completeness = len(completed_steps) / total_steps if total_steps > 0 else 0
        
        issues = []
        for failed in failed_steps:
            issues.append(f"Step {failed.step_number} failed: {failed.error_message}")
        
        final_output = self._build_final_output(execution_result)
        formatted = self._format_response(task, final_output, issues)
        
        return VerificationResult(
            is_valid=completeness > 0.5,
            completeness_score=completeness,
            issues=issues,
            suggestions=[],
            final_output=final_output,
            formatted_response=formatted
        )
    
    def _build_final_output(self, execution_result: ExecutionResult) -> Dict[str, Any]:
        """Build structured final output from results."""
        output = {"summary": "", "data": {}}
        
        for step_result in execution_result.step_results:
            if step_result.status != StepStatus.COMPLETED:
                continue
            
            if not step_result.tool_result or not step_result.tool_result.data:
                continue
            
            tool = step_result.tool_result.tool.value
            output["data"][tool] = step_result.tool_result.data
        
        parts = []
        if "github" in output["data"]:
            repo_count = len(output["data"]["github"].get("repositories", []))
            parts.append(f"Found {repo_count} GitHub repositories")
        
        if "weather" in output["data"]:
            city = output["data"]["weather"].get("city", "Unknown")
            temp = output["data"]["weather"].get("temperature_celsius", "N/A")
            parts.append(f"Weather in {city}: {temp}C")
        
        output["summary"] = ". ".join(parts) if parts else "Task completed"
        return output
    
    def _format_response(
        self, 
        task: str, 
        output: Dict[str, Any], 
        issues: List[str]
    ) -> str:
        """Format a human-readable response."""
        lines = ["=" * 50, "RESULTS", "=" * 50, ""]
        
        if "github" in output.get("data", {}):
            github_data = output["data"]["github"]
            lines.append("GITHUB REPOSITORIES:")
            lines.append("-" * 30)
            
            for repo in github_data.get("repositories", [])[:5]:
                lines.append(f"  {repo.get('full_name', 'Unknown')}")
                lines.append(f"    Stars: {repo.get('stars', 0):,}")
                desc = repo.get('description', 'No description')
                if desc and len(desc) > 80:
                    desc = desc[:77] + "..."
                lines.append(f"    {desc}")
                lines.append("")
        
        if "weather" in output.get("data", {}):
            weather = output["data"]["weather"]
            lines.append("WEATHER:")
            lines.append("-" * 30)
            lines.append(f"  Location: {weather.get('city', 'Unknown')}, {weather.get('country', '')}")
            lines.append(f"  Temperature: {weather.get('temperature_celsius', 'N/A')}C / {weather.get('temperature_fahrenheit', 'N/A')}F")
            lines.append(f"  Feels Like: {weather.get('feels_like_celsius', 'N/A')}C")
            lines.append(f"  Humidity: {weather.get('humidity', 'N/A')}%")
            lines.append(f"  Conditions: {weather.get('description', 'Unknown')}")
            lines.append(f"  Wind Speed: {weather.get('wind_speed_mps', 'N/A')} m/s")
            lines.append("")
        
        if issues:
            lines.append("ISSUES:")
            lines.append("-" * 30)
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")
        
        lines.append("=" * 50)
        return "\n".join(lines)
