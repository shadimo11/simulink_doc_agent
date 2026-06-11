import streamlit as st
import requests

# FastAPI Backend URL
API_URL = "http://localhost:8000/api/v1/query"

st.set_page_config(page_title="Simulink Intelligence Agent", page_icon="🤖", layout="centered")

st.title("⚙️ Simulink Doc Agent")
st.markdown("*Systems Engineering Copilot for MBD Architectures*")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask about your Simulink architecture..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Analyzing architecture..."):
        try:
            # Send the request to your FastAPI backend
            response = requests.post(API_URL, json={"user_query": prompt})
            response.raise_for_status()
            
            agent_reply = response.json().get("response", "Error: No response generated.")
            
        except requests.exceptions.RequestException as e:
            agent_reply = f"**Backend Connection Failed:** Ensure `python main.py` is running.\n\nError: `{e}`"

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(agent_reply)
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": agent_reply})