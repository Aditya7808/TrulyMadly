"""
Agent Orchestrator - Coordinates the multi-agent workflow.
"""

import logging
import time
from typing import Optional, Callable

from llm.client import LLMClient
from models import AgentResponse, ExecutionPlan, ExecutionResult, VerificationResult
from .planner import PlannerAgent
from .executor import ExecutorAgent
from .verifier import VerifierAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the Planner -> Executor -> Verifier workflow.
    
    Provides callbacks for UI integration and progress tracking.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()
        self.planner = PlannerAgent(self.llm)
        self.executor = ExecutorAgent(self.llm)
        self.verifier = VerifierAgent(self.llm)
        
        self._on_plan_created: Optional[Callable] = None
        self._on_step_started: Optional[Callable] = None
        self._on_step_completed: Optional[Callable] = None
        self._on_verification_complete: Optional[Callable] = None
    
    def set_callbacks(
        self,
        on_plan_created: Callable = None,
        on_step_started: Callable = None,
        on_step_completed: Callable = None,
        on_verification_complete: Callable = None
    ) -> None:
        """Set callback functions for progress tracking."""
        self._on_plan_created = on_plan_created
        self._on_step_started = on_step_started
        self._on_step_completed = on_step_completed
        self._on_verification_complete = on_verification_complete
    
    async def run(self, task: str) -> AgentResponse:
        """
        Execute the complete agent workflow.
        
        Args:
            task: Natural language task from user
            
        Returns:
            AgentResponse with full results
        """
        logger.info(f"Starting orchestration for task: {task[:100]}")
        start_time = time.time()
        
        # Phase 1: Planning
        logger.info("Phase 1: Planning")
        plan = await self.planner.run(task)
        
        if self._on_plan_created:
            self._on_plan_created(plan)
        
        # Phase 2: Execution
        logger.info("Phase 2: Execution")
        execution_result = await self._execute_with_callbacks(plan)
        
        # Phase 3: Verification
        logger.info("Phase 3: Verification")
        verification = await self.verifier.run(task, execution_result)
        
        # Phase 4: Retry failed steps if needed
        if not execution_result.success and verification.completeness_score < 1.0:
            logger.info("Phase 4: Retrying failed steps")
            execution_result, verification = await self._retry_failed_steps(
                task, plan, execution_result, verification
            )
        
        if self._on_verification_complete:
            self._on_verification_complete(verification)
        
        total_time = (time.time() - start_time) * 1000
        
        response = AgentResponse(
            task=task,
            plan=plan,
            execution=execution_result,
            verification=verification,
            total_time_ms=total_time,
            success=verification.is_valid and execution_result.success
        )
        
        logger.info(f"Orchestration complete in {total_time:.0f}ms")
        return response
    
    async def _retry_failed_steps(
        self,
        task: str,
        plan: ExecutionPlan,
        execution_result: ExecutionResult,
        verification: VerificationResult
    ):
        """Retry failed steps identified by the verifier."""
        from models import StepStatus
        
        failed_steps = [
            (step, result) for step, result in zip(plan.steps, execution_result.step_results)
            if result.status == StepStatus.FAILED
        ]
        
        if not failed_steps:
            return execution_result, verification
        
        logger.info(f"Retrying {len(failed_steps)} failed steps")
        
        # Retry each failed step once
        for step, old_result in failed_steps:
            new_result = await self.executor._execute_step(step)
            # Update the result in place
            for i, r in enumerate(execution_result.step_results):
                if r.step_number == step.step_number:
                    execution_result.step_results[i] = new_result
                    break
        
        # Recalculate success status
        success_count = sum(
            1 for r in execution_result.step_results 
            if r.status == StepStatus.COMPLETED
        )
        execution_result.success = success_count == len(execution_result.step_results)
        execution_result.partial_success = success_count > 0 and not execution_result.success
        
        # Re-verify
        verification = await self.verifier.run(task, execution_result)
        
        return execution_result, verification
    
    async def _execute_with_callbacks(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute plan with step-level callbacks."""
        if not self._on_step_started and not self._on_step_completed:
            return await self.executor.run(plan)
        
        result = await self.executor.run(plan)
        
        return result
    
    async def run_with_retry(
        self, 
        task: str, 
        max_attempts: int = 2
    ) -> AgentResponse:
        """
        Run with retry on verification failure.
        
        Args:
            task: User task
            max_attempts: Maximum retry attempts
            
        Returns:
            Best AgentResponse from attempts
        """
        best_response = None
        
        for attempt in range(max_attempts):
            logger.info(f"Attempt {attempt + 1}/{max_attempts}")
            
            response = await self.run(task)
            
            if response.success:
                return response
            
            if best_response is None or \
               response.verification.completeness_score > best_response.verification.completeness_score:
                best_response = response
            
            if attempt < max_attempts - 1:
                logger.info("Retrying due to incomplete results")
        
        return best_response
