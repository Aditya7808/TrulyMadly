"""Quick test script for AI Operations Assistant."""
import asyncio
from agents import AgentOrchestrator


async def main():
    print("=" * 60)
    print("AI OPERATIONS ASSISTANT - TEST RUN")
    print("=" * 60)
    
    orchestrator = AgentOrchestrator()
    
    task = "Find top Python machine learning repositories on GitHub and get the weather in Tokyo"
    print(f"\nTask: {task}\n")
    print("-" * 60)
    
    response = await orchestrator.run(task)
    
    print("\n[PLANNER AGENT]")
    print(f"Task Summary: {response.plan.task_summary}")
    print(f"Reasoning: {response.plan.reasoning}")
    print("Steps:")
    for step in response.plan.steps:
        print(f"  {step.step_number}. {step.description} [{step.tool.value}]")
    
    print("\n[EXECUTOR AGENT]")
    for result in response.execution.step_results:
        status = result.status.value.upper()
        print(f"  Step {result.step_number}: {status}")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    print("\n[VERIFIER AGENT]")
    print(f"  Valid: {response.verification.is_valid}")
    print(f"  Completeness: {response.verification.completeness_score:.0%}")
    if response.verification.issues:
        print(f"  Issues: {response.verification.issues}")
    
    print("\n[FINAL RESULT]")
    print(response.verification.formatted_response)
    
    print("\n" + "=" * 60)
    print(f"Total Time: {response.total_time_ms:.0f}ms")
    print(f"Success: {response.success}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
