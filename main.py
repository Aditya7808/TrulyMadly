"""
FastAPI backend for AI Operations Assistant.
Provides REST API endpoints for task execution.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings, validate_settings
from agents import AgentOrchestrator
from models import AgentResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

orchestrator: Optional[AgentOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global orchestrator
    logger.info("Starting AI Operations Assistant")
    
    config_status = validate_settings()
    if not config_status["openai_configured"]:
        logger.warning("OpenAI API key not configured")
    if not config_status["weather_configured"]:
        logger.warning("OpenWeatherMap API key not configured")
    
    orchestrator = AgentOrchestrator()
    logger.info("Orchestrator initialized")
    
    yield
    
    logger.info("Shutting down AI Operations Assistant")


app = FastAPI(
    title="AI Operations Assistant",
    description="Multi-agent AI assistant with LLM-powered reasoning and API integrations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    """Request model for task submission."""
    task: str = Field(..., min_length=3, max_length=1000, description="Natural language task")
    retry_on_failure: bool = Field(default=False, description="Retry if verification fails")


class TaskResponse(BaseModel):
    """Response model for task results."""
    success: bool
    task: str
    summary: str
    formatted_response: str
    total_time_ms: float
    plan_steps: int
    completed_steps: int
    completeness_score: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    openai_configured: bool
    weather_configured: bool
    github_configured: bool


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and configuration status."""
    status = validate_settings()
    return HealthResponse(
        status="healthy" if status["openai_configured"] else "degraded",
        openai_configured=status["openai_configured"],
        weather_configured=status["weather_configured"],
        github_configured=status["github_configured"]
    )


@app.post("/task", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """
    Execute a natural language task.
    
    The task is processed through:
    1. Planner Agent - Creates execution plan
    2. Executor Agent - Runs tools and APIs
    3. Verifier Agent - Validates and formats results
    """
    global orchestrator
    
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        if request.retry_on_failure:
            response = await orchestrator.run_with_retry(request.task)
        else:
            response = await orchestrator.run(request.task)
        
        completed = sum(
            1 for r in response.execution.step_results 
            if r.status.value == "completed"
        )
        
        return TaskResponse(
            success=response.success,
            task=response.task,
            summary=response.verification.final_output.get("summary", ""),
            formatted_response=response.verification.formatted_response,
            total_time_ms=response.total_time_ms,
            plan_steps=len(response.plan.steps),
            completed_steps=completed,
            completeness_score=response.verification.completeness_score
        )
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/task/full", response_model=AgentResponse)
async def execute_task_full(request: TaskRequest):
    """
    Execute task and return full detailed response.
    
    Returns complete AgentResponse with all plan details,
    step results, and verification data.
    """
    global orchestrator
    
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        if request.retry_on_failure:
            return await orchestrator.run_with_retry(request.task)
        else:
            return await orchestrator.run(request.task)
            
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Operations Assistant",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
