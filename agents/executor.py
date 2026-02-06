"""
Executor Agent - Executes plan steps by calling appropriate tools.
"""

import asyncio
import logging
import time
from typing import Dict, List

from models import (
    ExecutionPlan, ExecutionResult, StepResult, StepStatus,
    ToolResult, ToolType
)
from tools import ToolRegistry, GitHubTool, WeatherTool
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """
    Executor Agent that runs plan steps and manages tool execution.
    
    Responsibilities:
    - Execute plan steps in order
    - Call appropriate tools with parameters
    - Handle errors and retries
    - Track execution status and timing
    """
    
    name = "ExecutorAgent"
    max_retries = 3
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all available tools."""
        ToolRegistry.clear()
        ToolRegistry.register(GitHubTool())
        ToolRegistry.register(WeatherTool())
        self.log(f"Registered {len(ToolRegistry.get_all())} tools")
    
    async def run(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        Execute all steps in the plan.
        
        Args:
            plan: ExecutionPlan to execute
            
        Returns:
            ExecutionResult with all step results
        """
        self.log(f"Executing plan with {len(plan.steps)} steps")
        start_time = time.time()
        
        step_results: List[StepResult] = []
        completed_steps: Dict[int, StepResult] = {}
        
        for step in plan.steps:
            if not self._dependencies_met(step.depends_on, completed_steps):
                result = StepResult(
                    step_number=step.step_number,
                    status=StepStatus.FAILED,
                    error_message="Dependencies not met"
                )
            else:
                result = await self._execute_step(step)
            
            step_results.append(result)
            completed_steps[step.step_number] = result
        
        total_time = (time.time() - start_time) * 1000
        
        success_count = sum(1 for r in step_results if r.status == StepStatus.COMPLETED)
        all_success = success_count == len(step_results)
        partial_success = success_count > 0 and not all_success
        
        self.log(f"Execution complete: {success_count}/{len(step_results)} steps succeeded")
        
        return ExecutionResult(
            plan=plan,
            step_results=step_results,
            total_execution_time_ms=total_time,
            success=all_success,
            partial_success=partial_success
        )
    
    def _dependencies_met(
        self, 
        depends_on: List[int], 
        completed: Dict[int, StepResult]
    ) -> bool:
        """Check if all dependencies have completed successfully."""
        for dep in depends_on:
            if dep not in completed:
                return False
            if completed[dep].status != StepStatus.COMPLETED:
                return False
        return True
    
    async def _execute_step(self, step) -> StepResult:
        """
        Execute a single plan step with retries.
        
        Args:
            step: PlanStep to execute
            
        Returns:
            StepResult with execution outcome
        """
        self.log(f"Executing step {step.step_number}: {step.description}")
        
        tool = ToolRegistry.get(step.tool)
        if not tool:
            return StepResult(
                step_number=step.step_number,
                status=StepStatus.FAILED,
                error_message=f"Tool not found: {step.tool}"
            )
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                tool_result = await tool.safe_execute(**step.parameters)
                
                if tool_result.success:
                    return StepResult(
                        step_number=step.step_number,
                        status=StepStatus.COMPLETED,
                        tool_result=tool_result,
                        retry_count=retry_count
                    )
                else:
                    last_error = tool_result.error
                    retry_count += 1
                    self.log(f"Step {step.step_number} failed, retry {retry_count}/{self.max_retries}")
                    
                    if retry_count < self.max_retries:
                        await asyncio.sleep(1 * retry_count)
                        
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                self.log(f"Step {step.step_number} error: {e}", "error")
        
        return StepResult(
            step_number=step.step_number,
            status=StepStatus.FAILED,
            retry_count=retry_count,
            error_message=last_error or "Max retries exceeded"
        )
    
    async def execute_single_tool(
        self, 
        tool_type: ToolType, 
        parameters: dict
    ) -> ToolResult:
        """
        Execute a single tool directly (for verification retries).
        
        Args:
            tool_type: Type of tool to execute
            parameters: Tool parameters
            
        Returns:
            ToolResult from execution
        """
        tool = ToolRegistry.get(tool_type)
        if not tool:
            return ToolResult(
                tool=tool_type,
                success=False,
                error=f"Tool not found: {tool_type}"
            )
        
        return await tool.safe_execute(**parameters)
