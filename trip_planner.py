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
    packing_agent
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
# Drafts outline and coordinates the Research
# Updated: Removed Compiler and Edit Agents as per request. Returns raw findings to Interactive Agent.
planner_agent = LlmAgent(
    name="PlannerAgent",
    model=get_model(),
    instruction="""
    You are the **Planner Agent**. You act as the central strategist for the trip planning workflow.
    
    **Workflow**:
    1.  **Draft Outline**: Analyze the user's request (from InteractiveAgent) to define the destination, dates, constraints, and key interests.
    2.  **Research**: Call `ResearchInstructionAgent` to gather detailed information based on your outline.
    3.  **Verify**: Ensure the research findings are sufficient to answer the user's request. If significant info is missing, refine your request to the ResearchInstructionAgent.
    4.  **Return**: Return the *comprehensive raw research findings* directly to the InteractiveAgent. Do not summarize them excessively; provide the full details needed for the final report.
    """,
    tools=[
        AgentTool(research_instruction_agent)
    ],
)

# 3. Interactive Agent (Entry Point)
# User -> Interactive -> Planner
# Updated: Handles compilation and formatting (previously done by EditAgent)
interactive_agent = LlmAgent(
    name="InteractiveAgent",
    model=get_model(),
    instruction="""
    You are the **Interactive Agent**, the user's direct point of contact and final report generator.
    
    **Responsibilities**:
    1.  **Understand**: Clarify the user's request (Destination, Budget, Purpose, etc.).
    2.  **Delegate**: Once you have enough information, pass the request to the `PlannerAgent`.
    3.  **Compile & Format**: 
        - Receive the raw research findings from the `PlannerAgent`.
        - **Synthesize** this information into a cohesive, beautiful Markdown report.
        - **Reconcile** any inconsistencies (e.g., budget vs costs) in your narrative.
    
    **MANDATORY FORMATTING REQUIREMENTS for the Final Report**:
    1.  **Narrative Sections**: Clear, engaging descriptions for Trip Overview, Logistics, Sightseeing, etc.
    2.  **MASTER PLAN TABLE**: 
        - This is a MANDATORY final section.
        - Create a comprehensive Markdown table summarizing the entire trip.
        - Columns must be: **Category**, **Recommendation/Action**, **Details**, **Link/Source**.
        - Rows should cover: Visa, Flights, Accommodation, Top Attractions, Packing Essentials, Budget Est.
        - Ensure every row has a valid link in the Link/Source column.
    3.  **Links**: Ensure all links provided in the research are preserved and clickable.
    
    Do not invent new information. Only format the information provided by the PlannerAgent.
    """,
    tools=[
        AgentTool(planner_agent)
    ],
)

# Export the main entry point as trip_coordinator for compatibility with main.py and tests
trip_coordinator = interactive_agent

async def main():
    print("✈️ Trip Planner AI System Initialized (Streamlined Architecture)")
    
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
