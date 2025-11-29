import os
from kaggle_secrets import UserSecretsClient

try:
    GOOGLE_API_KEY = UserSecretsClient().get_secret("GOOGLE_API_KEY")
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    print("✅ Setup and authentication complete.")
except Exception as e:
    print(
        f"🔑 Authentication Error: Please make sure you have added 'GOOGLE_API_KEY' to your Kaggle secrets. Details: {e}"
    )

    

import uuid
from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from google.adk.apps.app import App, ResumabilityConfig
from google.adk.tools.function_tool import FunctionTool

print("✅ ADK components imported successfully.")



retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# MCP integration with Everything Server
mcp_image_server = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",  # Run MCP server via npx
            args=[
                "-y",  # Argument for npx to auto-confirm install
                "@modelcontextprotocol/server-everything",
            ],
            tool_filter=["getTinyImage"],
        ),
        timeout=30,
    )
)

print("✅ MCP Tool created")



# Create image agent with MCP integration
image_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="image_agent",
    instruction="Use the MCP Tool to generate images for user queries",
    tools=[mcp_image_server],
)



from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(agent=image_agent)

response = await runner.run_debug("Provide a sample tiny image", verbose=True)



from IPython.display import display, Image as IPImage
import base64

for event in response:
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "function_response") and part.function_response:
                for item in part.function_response.response.get("content", []):
                    if item.get("type") == "image":
                        display(IPImage(data=base64.b64decode(item["data"])))

'''🔄 Section 3: Long-Running Operations (Human-in-the-Loop)¶

So far, all tools execute and return immediately:

    User asks → Agent calls tool → Tool returns result → Agent responds

But what if your tools are long-running or you need human approval before completing an action?

Example: A shipping agent should ask for approval before placing a large order.

    User asks → Agent calls tool → Tool PAUSES and asks human → Human approves → Tool completes → Agent responds

This is called a Long-Running Operation (LRO) - the tool needs to pause, wait for external input (human approval), then resume.

When to use Long-Running Operations:

    💰 Financial transactions requiring approval (transfers, purchases)
    🗑️ Bulk operations (delete 1000 records - confirm first!)
    📋 Compliance checkpoints (regulatory approval needed)
    💸 High-cost actions (spin up 50 servers - are you sure?)
    ⚠️ Irreversible operations (permanently delete account)

3.1: What We're Building Today

Let's build a shipping coordinator agent with one tool that:

    Auto-approves small orders (≤5 containers)
    Pauses and asks for approval on large orders (>5 containers)
    Completes or cancels based on the approval decision

This demonstrates the core long-running operation pattern: pause → wait for human input → resume.
3.2: The Shipping Tool with Approval Logic

Here's the complete function.
The ToolContext Parameter

Notice the function signature includes tool_context: ToolContext. ADK automatically provides this object when your tool runs. It gives you two key capabilities:

    Request approval: Call tool_context.request_confirmation()
    Check approval status: Read tool_context.tool_confirmation'''

LARGE_ORDER_THRESHOLD = 5


def place_shipping_order(
    num_containers: int, destination: str, tool_context: ToolContext
) -> dict:
    """Places a shipping order. Requires approval if ordering more than 5 containers (LARGE_ORDER_THRESHOLD).

    Args:
        num_containers: Number of containers to ship
        destination: Shipping destination

    Returns:
        Dictionary with order status
    """

    # -----------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------
    # SCENARIO 1: Small orders (≤5 containers) auto-approve
    if num_containers <= LARGE_ORDER_THRESHOLD:
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-AUTO",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order auto-approved: {num_containers} containers to {destination}",
        }

    # -----------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------
    # SCENARIO 2: This is the first time this tool is called. Large orders need human approval - PAUSE here.
    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint=f"⚠️ Large order: {num_containers} containers to {destination}. Do you want to approve?",
            payload={"num_containers": num_containers, "destination": destination},
        )
        return {  # This is sent to the Agent
            "status": "pending",
            "message": f"Order for {num_containers} containers requires approval",
        }

    # -----------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------
    # SCENARIO 3: The tool is called AGAIN and is now resuming. Handle approval response - RESUME here.
    if tool_context.tool_confirmation.confirmed:
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-HUMAN",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order approved: {num_containers} containers to {destination}",
        }
    else:
        return {
            "status": "rejected",
            "message": f"Order rejected: {num_containers} containers to {destination}",
        }


print("✅ Long-running functions created!")


'''

3.4: Create the Agent, App and Runner¶

Step 1: Create the agent

Add the tool to the Agent. The tool decides internally when to request approval based on the order size.
'''
# Create shipping agent with pausable tool
shipping_agent = LlmAgent(
    name="shipping_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""You are a shipping coordinator assistant.
  
  When users request to ship containers:
   1. Use the place_shipping_order tool with the number of containers and destination
   2. If the order status is 'pending', inform the user that approval is required
   3. After receiving the final result, provide a clear summary including:
      - Order status (approved/rejected)
      - Order ID (if available)
      - Number of containers and destination
   4. Keep responses concise but informative
  """,
    tools=[FunctionTool(func=place_shipping_order)],
)

print("✅ Shipping Agent created!")
'''
Step 2: Wrap in resumable App

The problem: A regular LlmAgent is stateless - each call is independent with no memory of previous interactions. If a tool requests approval, the agent can't remember what it was doing.

The solution: Wrap your agent in an App with resumability enabled. The App adds a persistence layer that saves and restores state.

What gets saved when a tool pauses:

    All conversation messages so far
    Which tool was called (place_shipping_order)
    Tool parameters (10 containers, Rotterdam)
    Where exactly it paused (waiting for approval)

When you resume, the App loads this saved state so the agent continues exactly where it left off - as if no time passed.
'''
# Wrap the agent in a resumable app - THIS IS THE KEY FOR LONG-RUNNING OPERATIONS!
shipping_app = App(
    name="shipping_coordinator",
    root_agent=shipping_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

print("✅ Resumable app created!")



/tmp/ipykernel_48/3673777575.py:5: UserWarning: [EXPERIMENTAL] ResumabilityConfig: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  resumability_config=ResumabilityConfig(is_resumable=True),
'''
Step 3: Create Session and Runner with the App

Pass app=shipping_app instead of agent=... so the runner knows about resumability.
'''
session_service = InMemorySessionService()

# Create runner with the resumable app
shipping_runner = Runner(
    app=shipping_app,  # Pass the app instead of the agent
    session_service=session_service,
)

print("✅ Runner created!")
''
'''
🏗️ Section 4: Building the Workflow¶

‼️ Important: The workflow code uses ADK concepts like Sessions, Runners, and Events. We'll cover what you need to know for long-running operations in this notebook. For deeper understanding, we will cover these topics in Day 3, or you can check out the ADK docs and this video.
4.1: ⚠️ The Critical Part - Handling Events in Your Workflow

The agent won't automatically handle pause/resume. Every long-running operation workflow requires you to:

    Detect the pause: Check if events contain adk_request_confirmation
    Get human decision: In production, show UI and wait for user click. Here, we simulate it.
    Resume the agent: Send the decision back with the saved invocation_id

4.2 Understand Key Technical Concepts

👉 events - ADK creates events as the agent executes. Tool calls, model responses, function results - all become events

👉 adk_request_confirmation event - This event is special - it signals "pause here!"

    Automatically created by ADK when your tool calls request_confirmation()
    Contains the invocation_id
    Your workflow must detect this event to know the agent paused

👉 invocation_id - Every call to run_async() gets a unique invocation_id (like "abc123")

    When a tool pauses, you save this ID
    When resuming, pass the same ID so ADK knows which execution to continue
    Without it, ADK would start a NEW execution instead of resuming the paused one

4.3: Helper Functions to Process Events

These handle the event iteration logic for you.
''
check_for_approval() - Detects if the agent paused

    Loops through all events and looks for the special adk_request_confirmation event
    Returns approval_id (identifies this specific request) and invocation_id (identifies which execution to resume)
    Returns None if no pause detected
'''
def check_for_approval(events):
    """Check if events contain an approval request.

    Returns:
        dict with approval details or None
    """
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_confirmation"
                ):
                    return {
                        "approval_id": part.function_call.id,
                        "invocation_id": event.invocation_id,
                    }
    return None
'''
print_agent_response() - Displays agent text'''
'''
    Simple helper to extract and print text from events
'''
def print_agent_response(events):
    """Print agent's text responses from events."""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Agent > {part.text}")

create_approval_response() - Formats the human decision

'''    Takes the approval info and boolean decision (True/False) from the human
    Creates a FunctionResponse that ADK understands
    Wraps it in a Content object to send back to the agent'''

def create_approval_response(approval_info, approved):
    """Create approval response message."""
    confirmation_response = types.FunctionResponse(
        id=approval_info["approval_id"],
        name="adk_request_confirmation",
        response={"confirmed": approved},
    )
    return types.Content(
        role="user", parts=[types.Part(function_response=confirmation_response)]
    )


print("✅ Helper functions defined")
'''
✅ Helper functions defined

4.4: The Workflow Function - Let's tie it all together!

The run_shipping_workflow() function orchestrates the entire approval flow.

Look for the code explanation in the cell below.
'''