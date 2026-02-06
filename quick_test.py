"""Simple test to verify the orchestrator works."""
import asyncio
from agents import AgentOrchestrator

async def test():
    print("Initializing orchestrator...")
    o = AgentOrchestrator()
    
    print("Running task...")
    r = await o.run('Find Python repos and weather in London')
    
    print(f"SUCCESS: {r.success}")
    print(f"PLAN STEPS: {len(r.plan.steps)}")
    print(f"COMPLETENESS: {r.verification.completeness_score}")
    print(f"TIME: {r.total_time_ms:.0f}ms")
    print(f"\nFORMATTED OUTPUT:\n{r.verification.formatted_response}")

if __name__ == "__main__":
    asyncio.run(test())
