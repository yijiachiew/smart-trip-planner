from api.api import API_Key
import os

try:
    os.environ["GOOGLE_API_KEY"] = API_Key
    print("Google API Key set successfully.")
except KeyError:
    print("API Key not found.")

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from google.genai import types

# Retry config
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

# Common Model Configuration
def get_model():
    return Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    )

# ==========================================
# SPECIALIST RESEARCH AGENTS
# ==========================================

# 1. Research Agent
# Handles: Research (Visa, Safety, Customs) and Planning (Weather, Destination info)
research_instruction = """
You are a Research Specialist for travel planning. 
Your goal is to gather comprehensive information to fulfill the "RESEARCH" and "PLANNING" phases of a trip checklist.

Specifically, for a given destination and trip purpose (Work, Study, or Travel), you must research:
1.  **Visa & Entry Requirements**: Visas, documents, validity.
2.  **Safety & Health**: Neighborhood safety, vaccinations, emergency contacts.
3.  **Local Knowledge**: Weather/Seasons, Customs & Etiquette, Language.
4.  **Connectivity**: SIM/eSIM options, adapters.
5.  **Transport System**: Overview of metro, bus, taxi apps.

**CRITICAL REQUIREMENT**:
For every key piece of information (especially Visa rules, Official Health warnings, and Transport maps), you MUST provide a direct, clickable URL to an official or reliable source.
Format: `[Source Name](URL)`
"""

research_agent = LlmAgent(
    name="ResearchAgent",
    model=get_model(),
    instruction=research_instruction,
    tools=[google_search],
)

# 2. Logistics Agent
# Handles: Booking (Flights, Accommodation) and Arrival/Settling
logistics_instruction = """
You are a Logistics & Booking Specialist for travel planning.
Your goal is to fulfill the "BOOKING" and "ARRIVAL" phases of a trip checklist.

For a given destination, duration, and budget, you must identify:
1.  **Travel Options**: Flight routes (airlines, duration), Train/Bus options if domestic.
2.  **Accommodation**: Suggest 3 specific options (Hotel/Hostel/Apartment) fitting the budget and safety criteria.
3.  **Transport**: Airport transfer options, Local transport passes.
4.  **Arrival**: Step-by-step arrival guide (Airport -> City Center).

**CRITICAL REQUIREMENT**:
You MUST provide booking links or official websites for every recommendation (Airlines, Hotels, Transport passes).
Format: `[Book Here](URL)` or `[Official Site](URL)`
"""

logistics_agent = LlmAgent(
    name="LogisticsAgent",
    model=get_model(),
    instruction=logistics_instruction,
    tools=[google_search],
)

# 3. Finance Agent
# Handles: Finances (Budget, Costs)
finance_instruction = """
You are a Travel Finance Specialist.
Your goal is to fulfill the "FINANCES" phase of a trip checklist.

For a given destination and duration, you must:
1.  **Budget Estimation**: Estimate daily costs for Low, Mid, and High budgets (food, transport, activities).
2.  **Currency**: Current exchange rates, best ways to exchange money.
3.  **Banking**: Acceptance of cards vs cash, ATM availability, tips on using Wise/Revolut.
4.  **Hidden Costs**: Tipping culture, taxes, tourist fees.

**CRITICAL REQUIREMENT**:
Provide links to current exchange rate sources (e.g., XE.com), official tax information, or banking tips.
Format: `[Source](URL)`
"""

finance_agent = LlmAgent(
    name="FinanceAgent",
    model=get_model(),
    instruction=finance_instruction,
    tools=[google_search],
)

# 4. Attractions Agent
# Handles: Detailed attraction research, hidden gems, and context-specific recommendations.
attractions_instruction = """
You are a Travel Guide & Culture Specialist.
Your goal is to provide deep, curated recommendations for places to visit, fulfilling the "Detailed Attraction Research" requirement.

For a given destination and purpose:
1.  **Must-See Landmarks**: The iconic spots.
2.  **Hidden Gems**: Lesser-known spots away from tourist traps.
3.  **Cultural Sites**: Museums, historical sites, or local markets relevant to the user's interests.
4.  **Purpose-Aligned Recommendations**: 
    - For WORK: Quick spots near business districts or evening relaxation.
    - For STUDY: Libraries, student hangouts, cheap cultural passes.
    - For TRAVEL: Full sightseeing itineraries.

**CRITICAL REQUIREMENT**:
For every attraction, provide a link to the official website or a reliable booking/info page.
Format: `[Visit Site](URL)`
"""

attractions_agent = LlmAgent(
    name="AttractionsAgent",
    model=get_model(),
    instruction=attractions_instruction,
    tools=[google_search],
)

# 5. Packing Agent
# Handles: Clothing and prep based on season and destination.
packing_instruction = """
You are a Travel Styling & Preparation Specialist.
Your goal is to create the perfect packing list, fulfilling the "Season-Specific Wardrobe" and "Activity-Specific Gear" requirements.

For a given destination and season (or specific travel dates):
1.  **Weather Analysis**: Research the specific weather forecast or typical patterns for the dates.
2.  **Clothing Strategy**: Recommend fabrics, layering strategies, and specific items (e.g., "breathable linen," "thermal base layers").
3.  **Activity Gear**: Gear needed for planned activities (hiking boots, formal wear for business, modesty for religious sites).
4.  **Essentials**: Adapters (voltage/plug type), specific toiletries not easily found locally.

**CRITICAL REQUIREMENT**:
Provide links to weather reports, and example links for specific specialized gear (e.g., "Universal Adapter" on Amazon/REI/Local store) so the user sees exactly what to buy.
Format: `[Example Item](URL)` or `[Weather Report](URL)`
"""

packing_agent = LlmAgent(
    name="PackingAgent",
    model=get_model(),
    instruction=packing_instruction,
    tools=[google_search],
)

# ==========================================
# ORCHESTRATION SUPPORT AGENTS
# ==========================================

# 6. Agent Compiler
# Aggregates and reconciles findings.
compiler_instruction = """
You are the **Agent Compiler**. Your role is to synthesize the research findings from multiple specialists.

Your tasks:
1.  **Aggregate**: Combine the outputs from Research, Logistics, Finance, Attractions, and Packing agents into a cohesive dataset.
2.  **Reconcile**: Check for inconsistencies (e.g., does the budget match the accommodation prices? Is the packing list suitable for the researched weather?).
3.  **Verify Completeness**: Ensure all key aspects of the trip are covered (Visa, Flights, Hotel, Activities, Packing).

If you find missing information or major inconsistencies, clearly state what is missing so the Research Instruction Agent can be triggered again.
If the plan is complete and consistent, output a summary confirming readiness for the Edit Agent.
"""

compiler_agent = LlmAgent(
    name="AgentCompiler",
    model=get_model(),
    instruction=compiler_instruction,
    # No external tools needed, it processes text provided in context
)

# 7. Edit Agent
# Reformats output into descriptions and tables.
edit_instruction = """
You are the **Edit Agent**. Your goal is to format the final trip plan for the user.

Input: A compiled and reconciled trip plan.
Output: A beautifully formatted Markdown report.

**MANDATORY FORMATTING REQUIREMENTS**:
1.  **Narrative Sections**: Clear, engaging descriptions for Trip Overview, Logistics, Sightseeing, etc.
2.  **MASTER PLAN TABLE**: 
    - This is a MANDATORY final section.
    - Create a comprehensive Markdown table summarizing the entire trip.
    - Columns must be: **Category**, **Recommendation/Action**, **Details**, **Link/Source**.
    - Rows should cover: Visa, Flights, Accommodation, Top Attractions, Packing Essentials, Budget Est.
    - Ensure every row has a valid link in the Link/Source column.
3.  **Links**: Ensure all links provided by the specialists are preserved and clickable.

Do not invent new information. Only format the provided information.
"""

edit_agent = LlmAgent(
    name="EditAgent",
    model=get_model(),
    instruction=edit_instruction,
)
