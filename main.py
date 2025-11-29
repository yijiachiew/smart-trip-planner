import asyncio
import os
import sys
import datetime
import re

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the API Key setup first to ensure env vars are set
try:
    from api.api import API_Key
    os.environ["GOOGLE_API_KEY"] = API_Key
except ImportError:
    print("Warning: api.api module not found or API_Key missing.")
except Exception as e:
    print(f"Warning setting API Key: {e}")

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from trip_planner import trip_coordinator
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)

def save_transcript(user_input, agent_response, session_id):
    """Saves the conversation exchange to a markdown file."""
    filename = f"transcript_{session_id}.md"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create file with header if it doesn't exist
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Trip Planner Session Transcript: {session_id}\n")
            f.write(f"Started: {timestamp}\n\n")
    
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"## {timestamp}\n\n")
        f.write(f"**User**: {user_input}\n\n")
        f.write(f"**TripCoordinator**: {agent_response}\n\n")
        f.write("---\n\n")

def extract_markdown_tables(text):
    """Extracts markdown tables from text."""
    lines = text.split('\n')
    table_lines = []
    tables = []
    inside_table = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check for table row (starts and ends with | usually, or just contains |)
        # Robust check: look for pipe and ensure it's not just a sentence with a pipe.
        # Markdown tables usually start with a header row, then a separator row |---|
        
        if stripped.startswith('|'):
            if not inside_table:
                # Potential start of table. Check if next line is separator.
                if i + 1 < len(lines) and set(lines[i+1].strip()) <= set('| -:'):
                     inside_table = True
            
            if inside_table:
                table_lines.append(line)
        else:
            if inside_table:
                # Table ended
                tables.append("\n".join(table_lines))
                table_lines = []
                inside_table = False
    
    # Capture last table if text ended
    if inside_table and table_lines:
        tables.append("\n".join(table_lines))
        
    return tables

def save_plan_table(agent_response, session_id):
    """Extracts and saves the plan table."""
    tables = extract_markdown_tables(agent_response)
    
    if not tables:
        print("No structured table found in the response to save.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trip_plan_{session_id}_{timestamp}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Trip Plan Summary - {timestamp}\n\n")
        for i, table in enumerate(tables):
            f.write(table)
            f.write("\n\n")
            
    print(f"Plan table saved to {filename}")

async def print_agent_response(response_events):
    """Helper to extract and print the final text response from the agent.
       Returns the extracted text.
    """
    found_text = ""
    
    # Handle different response types from run_debug
    events = []
    if isinstance(response_events, list):
        events = response_events
    elif hasattr(response_events, "events"):
        events = response_events.events
    else:
        # Fallback if it's a single event or other object
        events = [response_events]

    for event in events:
        # We are looking for the model's text response
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"\nTripCoordinator:\n{part.text}\n")
                    found_text += part.text + "\n"
    
    return found_text

async def main():
    print("\n" + "="*50)
    print("🌍 WELCOME TO THE AI TRIP PLANNER 🌍")
    print("="*50)
    print("I can help you plan trips (Work, Study, or Travel).")
    print("Tell me your destination, budget, and purpose.")
    print("Type 'quit', 'exit', or 'bye' to end the session.")
    print("-" * 50 + "\n")

    # Initialize Session and Runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=trip_coordinator,
        session_service=session_service,
        app_name="trip_planner_cli"
    )
    
    # Session ID for context
    session_id = "user_session_1"
    
    print(f"Transcript will be saved to transcript_{session_id}.md\n")

    while True:
        try:
            # Display prompt and wait for input
            user_input = input("👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+D or Ctrl+C gracefully
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("\nSafe travels! Goodbye.\n")
            break

        print("\nThinking... (I'm consulting my specialist agents)\n")

        # Run the agent with the user input
        try:
            # Use run_debug as run() seems to have signature issues in this version
            try:
                response = await runner.run_debug(user_input, session_id=session_id)
            except TypeError:
                # Fallback if run_debug doesn't accept session_id
                response = await runner.run_debug(user_input)
                
            agent_text = await print_agent_response(response)
            
            # Save to transcript
            if agent_text:
                save_transcript(user_input, agent_text, session_id)
                
                # Check for table and offer to save
                if "|" in agent_text and "---" in agent_text:
                    print("\nStructured plan detected.")
                    save_opt = input("   Save plan table to file? (y/n): ").strip().lower()
                    if save_opt == 'y':
                        save_plan_table(agent_text, session_id)
                
        except Exception as e:
            print(f"\nAn error occurred during processing: {e}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
