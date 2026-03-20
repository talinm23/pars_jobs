

# data scientist, remote US, full-time, most recent, salary range doesn't matter, entry level experience,

import os
from dotenv import load_dotenv
#if os.path.exists('.env'):
#      load_dotenv()
import asyncio
from agents import Agent, Runner, function_tool
from openai.types.responses import ResponseTextDeltaEvent
import streamlit as st
from functions import get_links, scrape_text, concise_table
import time
#from google.adk.runners import InMemoryRunner


script_dir = os.path.dirname(__file__)
prompts_path = os.path.join(script_dir, "prompts", "agent_a.md")
with open(prompts_path, "r") as f:
    agent_a = f.read()

agent_a_agent = Agent(
    name="agent_a_agent",
    instructions=agent_a,
    tools=[scrape_text],   # or [] if it doesn’t need tools
)

'''
prompts_path2 = os.path.join(script_dir, "prompts", "agent_b.md")
with open(prompts_path2, "r") as f:
    agent_b = f.read()

agent_b_agent = Agent(
    name="agent_b_agent",
    instructions=agent_b,
    tools=[concise_table],   # or [] if it doesn’t need tools
)
'''


'''
client = None

def init_client():
    global client
    client = OpenAI(api_key=st.session_state["openai_api_key"])
'''


'''
script_dir = os.path.dirname(__file__)
prompts_path = os.path.join(script_dir, "prompts", "first_query.md")
with open(prompts_path, "r") as f:
    first_query = f.read()

first_query_agent = Agent(
    name="first_query_agent",
    instructions=first_query,
    tools=[scrape_text],   # or [] if it doesn’t need tools
)
'''
prompts_path2 = os.path.join(script_dir, "prompts", "list_to_table.md")
with open(prompts_path2, "r") as f:
    list_to_table = f.read()

list_to_table_agent = Agent(
    name="list_to_table_agent",
    instructions=list_to_table,
    tools=[concise_table],   # or [] if it doesn’t need tools
)



''' #delete later
prompts_path3 = os.path.join(script_dir, "prompts", "make_table.md")
with open(prompts_path3, "r") as f:
    make_table = f.read()

make_table_agent = Agent(
    name="make_table_agent",
    instructions=make_table,
    tools=[],   # or [] if it doesn’t need tools
)
'''

async def run_streamlit_app():
    st.set_page_config(
        page_title="Parsing LinkedIn Jobs Agent",
        page_icon="🤖",
        layout="wide"
    )

    st.title("Parsing LinkedIn Jobs Agent")
    st.markdown("Welcome!"
                "\n\nPlease enter the API keys for OpenAI on the left sidebar. ")

    # Force users to enter their own API key (ignore environment)
    # This ensures the app works as intended for public use

    # Sidebar for API key input
    with st.sidebar:
        st.header("Configuration")

        api_key_openai = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Enter your OpenAI API key to use the agent"
        )

        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.session_state.input_items = []
            st.rerun()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "input_items" not in st.session_state:
        st.session_state.input_items = []
    if "agent" not in st.session_state:
        st.session_state.agent = None

    # Function to initialize agent when needed
    def initialize_agent():
        if st.session_state.agent is None and api_key_openai:
            os.environ["OPENAI_API_KEY"] = api_key_openai

            # Load system instructions
            try:
                script_dir = os.path.dirname(__file__)
                prompts_path = os.path.join(script_dir, "prompts", "system_instructions.md")
                with open(prompts_path, "r") as f:
                    system_instructions = f.read()

                st.session_state.agent = Agent(
                    name="Coordinator Agent",
                    instructions=system_instructions,
                    tools=[get_links, scrape_text, concise_table],)
                return True
            except Exception as e:
                st.error(f"Error initializing agent: {str(e)}")
                return False
        return st.session_state.agent is not None

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        if not api_key_openai:
            st.error("Please enter your OpenAI API key in the sidebar.")
            return

        # Initialize agent if needed
        if not initialize_agent():
            st.error("Failed to initialize agent. Please check your API key.")
            return

        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.input_items.append({"content": prompt, "role": "user"})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                # Run the agent
                result = Runner.run_streamed(
                    st.session_state.agent,
                    input=st.session_state.input_items,max_turns=7
                )
                time.sleep(8)

                # Process streaming events with await
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        full_response += event.data.delta
                        response_placeholder.markdown(full_response + "▌")
                    elif event.type == "run_item_stream_event":
                        if event.item.type == "tool_call_item":
                            # Get tool name and show appropriate status message
                            tool_name = event.item.raw_item.name
                            if tool_name == "get_links":
                                status_msg = f"\n\n-- Getting the links..."
                            elif tool_name == "ai":
                                status_msg = f"\n\n-- Asking the LLM in ai tool..."
                            elif tool_name == "scrape_feed":
                                status_msg = f"\n\n-- Scraping the feed..."
                            elif tool_name == "list_to_table_with_openai":
                                status_msg = f"\n\n-- Asking openai to make list_to_table..."
                            else:
                                status_msg = f"\n\n-- Calling {tool_name}..."
                            response_placeholder.markdown(full_response + status_msg + "▌")
                        elif event.item.type == "tool_call_output_item":
                            # Use generic handling for tool outputs
                            formatted_content = f"Tool output:\n{event.item.output}"
                            completion_msg = f"\n\n-- Tool completed."

                            # Add tool output as user role to input_items
                            st.session_state.input_items.append({
                                "content": formatted_content,
                                "role": "user"
                            })
                            response_placeholder.markdown(full_response + completion_msg + "▌")

                # Final response without cursor
                response_placeholder.markdown(full_response)

                # Add assistant response to session state
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.session_state.input_items.append({"content": full_response, "role": "assistant"})

            except Exception as e:
                st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_streamlit_app())
