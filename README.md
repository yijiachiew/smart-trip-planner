***

# Project Write-Up: AI Trip Planner Agent

### Problem Statement
Planning a trip is a complex, multi-faceted process that goes far beyond just booking a flight and a hotel. The requirements shift drastically depending on the **purpose** of the trip:
*   **Travelers** need sightseeing itineraries and hidden gems.
*   **Remote Workers** need reliable Wi-Fi, co-working spaces, and tax/visa clarity.
*   **Students** need university proximity, budget housing, and academic calendar alignment.

Following a comprehensive checklist (like the one in `checklist.md`) requires visiting dozens of websites, cross-referencing budgets, and managing logistics manually. It is time-consuming, overwhelming, and easy to miss critical details like visa validity or seasonal packing requirements.

### Why agents?
Agents are the perfect solution for this problem because trip planning requires **specialization** and **orchestration**.
*   **Complexity Management:** A single generic AI prompt often struggles to handle Visa rules, specific packing lists, and detailed budgeting simultaneously without hallucinating or forgetting constraints.
*   **Separation of Concerns:** By using specialized agents, we can have one focused entirely on legal requirements (Visa/Safety) and another focused purely on fun (Attractions).
*   **Tool Use:** Agents can use tools (like Google Search) to fetch real-time data (weather, exchange rates) which is critical for accurate planning.
*   **Workflow:** A hierarchical agent system can mimic a real-world travel agency, where a "Planner" delegates tasks to specialists and compiles the results.

### What you created (Architecture)
I built a **Hierarchical Multi-Agent System** using the `google-adk` framework. The system is designed as a streamlined tree structure to manage context and delegation effectively. 

*Note: The original design included separate Compiler and Edit agents, but these were consolidated into the Interactive Agent to optimize for API resource constraints and latency.*

1.  **Entry Point (`InteractiveAgent`)**: The user interface and final report generator. It captures intent, delegates to the Planner, and handles the final compilation and formatting of the Markdown report.
2.  **The Brain (`PlannerAgent`)**: The central strategist. It drafts the plan outline, delegates research tasks, and verifies that the findings match the user's request before passing them back for formatting.
3.  **The Manager (`ResearchInstructionAgent`)**: Breaks down the plan into specific tasks and orchestrates the specialists.
4.  **The Specialists**:
    *   **`ResearchAgent`**: Handles Visas, Safety, and Local Customs.
    *   **`LogisticsAgent`**: Finds Flights, Accommodation, and Transport.
    *   **`FinanceAgent`**: Estimates Budgets, Currency, and Banking needs.
    *   **`AttractionsAgent`**: Finds Must-sees, Hidden Gems, and purpose-specific spots.
    *   **`PackingAgent`**: Checks weather and creates gear lists.

### Demo
When you run the application via the CLI (`main.py`):
1.  **User Input**: "Plan a 2-week work trip to Tokyo in October. Budget $3000."
2.  **Process**: The system identifies this as a "Work" trip.
    *   The `ResearchAgent` looks up Japan's digital nomad or work visa requirements.
    *   The `LogisticsAgent` finds hotels near major business districts (e.g., Shinjuku/Marunouchi).
    *   The `PackingAgent` checks October weather in Tokyo (cooling down) and suggests business-casual layers.
3.  **Output**: The user receives a structured Markdown report containing:
    *   A narrative summary of the trip.
    *   A **Master Plan Table** with clickable links to book flights, hotels, and apply for visas.
    *   A breakdown of estimated costs vs. the $3000 budget.

### The Build
*   **Language**: Python
*   **Framework**: `google-adk` (Agent Development Kit) for defining agents, tools, and runners.
*   **Model**: `gemini-2.5-flash-lite` (chosen for speed and cost-efficiency in a multi-agent loop).
*   **Tools**: `google_search` tool to allow agents to fetch live information (Exchange rates, Weather, Events).
*   **Pattern**: Hierarchical Orchestration (Manager-Worker pattern).

### If I had more time, this is what I'd do
*   **Smart Plan Optimization & Workarounds**: Implement a "Review Agent" that proactively analyzes the generated plan for friction points.
    *   *Example*: If the researched budget exceeds the user's limit, it would automatically suggest trade-offs (e.g., "If you shift your dates by one week, flight costs drop by 20%" or "Staying in this alternative neighborhood would save $300").
    *   It would allow users to ask "What are my options?" for specific constraints, turning the plan from a static document into a dynamic negotiation.
*   **Stateful Checklist Tracking**: Implement a persistent database to track the `checklist.md` items over time, allowing the user to mark items as "Done" across multiple sessions rather than generating a fresh plan every time.
*   **Direct Booking Integrations**: Replace generic Google Searches with specific APIs (Skyscanner, Booking.com, TripAdvisor) to retrieve real-time availability and exact pricing rather than just informational links.
*   **Personalization Memory**: Create a "User Profile" system where the agents remember preferences across trips (e.g., "User always prefers aisle seats," "User is vegetarian," or "User avoids hostels").
*   **Frontend UI**: Build a web interface (Streamlit or React) that renders the Markdown tables as interactive components, allowing users to drag-and-drop itinerary items.