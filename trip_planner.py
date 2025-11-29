import asyncio
from api.api import API_Key
import os

# Ensure API Key is set
try:
    os.environ["GOOGLE_API_KEY"] = API_Key
    print("Google API Key set successfully.")
except KeyError:
    print("API Key not found in api.api")

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import agents
from trip_agents import (
    research_agent, 
    logistics_agent, 
    finance_agent, 
    attractions_agent, 
    packing_agent,
    compiler_agent,
    edit_agent
)

# Retry config
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Common model for orchestrators
def get_model():
    return Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    )

# ==========================================
# HIERARCHICAL AGENTS
# ==========================================

# 1. Research Instruction Agent
# Manages the specialists
research_instruction_agent = LlmAgent(
    name="ResearchInstructionAgent",
    model=get_model(),
    instruction="""
    You are the **Research Instruction Agent**.
    
    Your goal is to execute the research phase of the trip planning process.
    1.  Receive a trip outline or criteria from the Planner Agent.
    2.  Break this down into specific research tasks.
    3.  Delegate these tasks to your specialist tools:
        - `ResearchAgent`: General info, visa, safety.
        - `LogisticsAgent`: Flights, hotels, transport.
        - `FinanceAgent`: Budget, currency.
        - `AttractionsAgent`: Sightseeing.
        - `PackingAgent`: Clothing, gear.
    4.  Collect their responses.
    5.  Return the aggregated raw research findings.
    """,
    tools=[
        AgentTool(research_agent),
        AgentTool(logistics_agent),
        AgentTool(finance_agent),
        AgentTool(attractions_agent),
        AgentTool(packing_agent)
    ],
)

# 2. Planner Agent
# Drafts outline and coordinates the Research -> Compile -> Edit flow
planner_agent = LlmAgent(
    name="PlannerAgent",
    model=get_model(),
    instruction="""
    You are the **Planner Agent**. You act as the central brain for the trip planning workflow.
    
    **Workflow**:
    1.  **Draft Outline**: specific destination, dates, and constraints based on user input.
    2.  **Research**: Call `ResearchInstructionAgent` to gather detailed information based on your outline.
    3.  **Compile & Reconcile**: Call `AgentCompiler` with the research findings. Ask it to check for consistency.
    4.  **Formatting**: Call `EditAgent` with the reconciled plan to generate the final user-facing report.
    
    Return the output from the `EditAgent` as your final response.
    """,
    tools=[
        AgentTool(research_instruction_agent),
        AgentTool(compiler_agent),
        AgentTool(edit_agent)
    ],
)

# 3. Interactive Agent (Entry Point)
# User -> Interactive -> Planner
interactive_agent = LlmAgent(
    name="InteractiveAgent",
    model=get_model(),
    instruction="""
    You are the **Interactive Agent**, the user's direct point of contact for trip planning.
    
    Your responsibilities:
    1.  **Understand**: Clarify the user's request (Destination, Budget, Purpose, etc.).
    2.  **Delegate**: Once you have enough information, pass the request to the `PlannerAgent` to generate the full plan.
    3.  **Relay**: Present the final formatted plan (returned by the PlannerAgent) to the user.
    
    If the user provides feedback or modifications on an existing plan, pass those back to the PlannerAgent to refine the plan.
    """,
    tools=[
        AgentTool(planner_agent)
    ],
)

# Export the main entry point as trip_coordinator for compatibility with main.py and tests
trip_coordinator = interactive_agent

async def main():
    print("✈️ Trip Planner AI System Initialized (Hierarchical Architecture)")
    
    # Sample User Query
    user_query = "Plan a 2-week work trip to Tokyo, Japan in October. Budget is $3000 USD (excluding flights). I need to work remotely from a co-working space."
    
    print(f"\n📝 Processing Request: {user_query}\n")
    print("...Delegating tasks to Interactive -> Planner -> Research Agents...")

    # Setup Runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=trip_coordinator,
        session_service=session_service,
        app_name="trip_planner"
    )

    # Run
    await runner.run_debug(user_query)

if __name__ == "__main__":
    asyncio.run(main())
