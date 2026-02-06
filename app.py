"""
Streamlit UI for AI Operations Assistant.
Provides an interactive interface for task execution with agent visualization.
"""

import streamlit as st
import asyncio
import json
import time
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import validate_settings
from agents import AgentOrchestrator
from models import StepStatus


st.set_page_config(
    page_title="AI Operations Assistant",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)


CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #1f2937;
    }
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        margin-bottom: 1rem;
    }
    .step-success {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 0.25rem 0.25rem 0;
    }
    .step-failed {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 0.25rem 0.25rem 0;
    }
    .step-pending {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 0.25rem 0.25rem 0;
    }
    .metric-card {
        background: #f9fafb;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        border: 1px solid #e5e7eb;
    }
    .result-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        font-family: monospace;
        white-space: pre-wrap;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "history" not in st.session_state:
        st.session_state.history = []
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "current_response" not in st.session_state:
        st.session_state.current_response = None


def get_orchestrator():
    """Get or create the agent orchestrator."""
    if st.session_state.orchestrator is None:
        st.session_state.orchestrator = AgentOrchestrator()
    return st.session_state.orchestrator


def render_sidebar():
    """Render the sidebar with configuration and info."""
    with st.sidebar:
        st.markdown("### Configuration Status")
        
        status = validate_settings()
        
        col1, col2 = st.columns(2)
        with col1:
            if status["openai_configured"]:
                st.success("OpenAI")
            else:
                st.error("OpenAI")
        with col2:
            if status["weather_configured"]:
                st.success("Weather")
            else:
                st.warning("Weather")
        
        if status["github_configured"]:
            st.success("GitHub Token (Optional)")
        else:
            st.info("GitHub: Public API")
        
        st.markdown("---")
        st.markdown("### Available Tools")
        st.markdown("""
        **GitHub Search**
        - Search repositories
        - Get stars, forks, descriptions
        - Filter by language
        
        **Weather**
        - Current weather by city
        - Temperature, humidity, wind
        - Conditions description
        """)
        
        st.markdown("---")
        st.markdown("### Example Tasks")
        examples = [
            "Find top Python machine learning repos and weather in San Francisco",
            "Search GitHub for FastAPI projects with many stars",
            "What's the weather in Tokyo and find popular weather API repos",
            "Find trending JavaScript frameworks on GitHub",
            "Get weather in London and search for weather dashboard repos"
        ]
        
        for example in examples:
            if st.button(example[:50] + "...", key=f"ex_{hash(example)}"):
                st.session_state.example_task = example
        
        st.markdown("---")
        st.markdown("### Architecture")
        st.markdown("""
        ```
        User Task
            |
            v
        [Planner Agent]
            |
            v
        [Executor Agent]
            |
            v
        [Verifier Agent]
            |
            v
        Final Response
        ```
        """)


def render_plan_section(plan):
    """Render the execution plan section."""
    st.markdown("### Planner Agent Output")
    
    with st.expander("View Execution Plan", expanded=True):
        st.markdown(f"**Task Summary:** {plan.task_summary}")
        st.markdown(f"**Reasoning:** {plan.reasoning}")
        
        st.markdown("**Steps:**")
        for step in plan.steps:
            tool_badge = f"`{step.tool.value.upper()}`"
            st.markdown(f"{step.step_number}. {step.description} {tool_badge}")
            if step.parameters:
                st.json(step.parameters)


def render_execution_section(execution):
    """Render the execution results section."""
    st.markdown("### Executor Agent Output")
    
    for result in execution.step_results:
        status = result.status
        step = next(
            (s for s in execution.plan.steps if s.step_number == result.step_number),
            None
        )
        
        if status == StepStatus.COMPLETED:
            css_class = "step-success"
            icon = "[OK]"
        elif status == StepStatus.FAILED:
            css_class = "step-failed"
            icon = "[FAIL]"
        else:
            css_class = "step-pending"
            icon = "[...]"
        
        step_desc = step.description if step else f"Step {result.step_number}"
        
        st.markdown(
            f'<div class="{css_class}">'
            f'<strong>{icon} Step {result.step_number}:</strong> {step_desc}'
            f'</div>',
            unsafe_allow_html=True
        )
        
        if result.tool_result and result.tool_result.data:
            with st.expander(f"View Step {result.step_number} Data"):
                st.json(result.tool_result.data)
        
        if result.error_message:
            st.error(f"Error: {result.error_message}")


def render_verification_section(verification):
    """Render the verification results section."""
    st.markdown("### Verifier Agent Output")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Completeness",
            f"{verification.completeness_score:.0%}"
        )
    
    with col2:
        st.metric(
            "Valid",
            "Yes" if verification.is_valid else "No"
        )
    
    with col3:
        st.metric(
            "Issues",
            len(verification.issues)
        )
    
    if verification.issues:
        with st.expander("View Issues"):
            for issue in verification.issues:
                st.warning(issue)
    
    if verification.suggestions:
        with st.expander("View Suggestions"):
            for suggestion in verification.suggestions:
                st.info(suggestion)


def render_final_result(verification):
    """Render the final formatted result."""
    st.markdown("### Final Result")
    
    st.markdown(
        f'<div class="result-box">{verification.formatted_response}</div>',
        unsafe_allow_html=True
    )
    
    with st.expander("View Raw JSON Output"):
        st.json(verification.final_output)


async def execute_task(task: str):
    """Execute the task and return results."""
    orchestrator = get_orchestrator()
    response = await orchestrator.run(task)
    return response


def main():
    """Main application entry point."""
    init_session_state()
    
    st.markdown('<p class="main-header">AI Operations Assistant</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Multi-agent system with LLM-powered reasoning and real API integrations</p>',
        unsafe_allow_html=True
    )
    
    render_sidebar()
    
    # Task input
    default_task = st.session_state.get("example_task", "")
    task = st.text_area(
        "Enter your task:",
        value=default_task,
        height=100,
        placeholder="Example: Find top Python AI repositories and check the weather in New York"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        submit = st.button("Execute Task", type="primary", use_container_width=True)
    with col2:
        if st.button("Clear", use_container_width=False):
            st.session_state.current_response = None
            st.session_state.example_task = ""
            st.rerun()
    
    if submit and task:
        status = validate_settings()
        if not status["openai_configured"]:
            st.error("OpenAI API key is required. Please set OPENAI_API_KEY in your .env file.")
            return
        
        with st.spinner("Processing task..."):
            progress_bar = st.progress(0, text="Initializing...")
            
            try:
                progress_bar.progress(10, text="Planner Agent: Creating execution plan...")
                
                response = asyncio.run(execute_task(task))
                
                progress_bar.progress(100, text="Complete!")
                time.sleep(0.5)
                progress_bar.empty()
                
                st.session_state.current_response = response
                st.session_state.history.append({
                    "task": task,
                    "response": response,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                progress_bar.empty()
                st.error(f"Execution failed: {str(e)}")
                return
    
    # Display results
    if st.session_state.current_response:
        response = st.session_state.current_response
        
        st.markdown("---")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Time", f"{response.total_time_ms:.0f}ms")
        with col2:
            st.metric("Plan Steps", len(response.plan.steps))
        with col3:
            completed = sum(
                1 for r in response.execution.step_results 
                if r.status == StepStatus.COMPLETED
            )
            st.metric("Completed", f"{completed}/{len(response.plan.steps)}")
        with col4:
            status_text = "Success" if response.success else "Partial"
            st.metric("Status", status_text)
        
        st.markdown("---")
        
        # Agent outputs in tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "Final Result",
            "Planner",
            "Executor", 
            "Verifier"
        ])
        
        with tab1:
            render_final_result(response.verification)
        
        with tab2:
            render_plan_section(response.plan)
        
        with tab3:
            render_execution_section(response.execution)
        
        with tab4:
            render_verification_section(response.verification)
    
    # History section
    if st.session_state.history and len(st.session_state.history) > 1:
        st.markdown("---")
        with st.expander("View Task History"):
            for i, item in enumerate(reversed(st.session_state.history[:-1])):
                st.markdown(f"**{i+1}. {item['task'][:100]}...**")
                st.caption(item['timestamp'])


if __name__ == "__main__":
    main()
