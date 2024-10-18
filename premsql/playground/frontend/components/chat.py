import streamlit as st
from premsql.playground.api_client import APIClient
import random
import time

class ChatComponent:
    def __init__(self, base_url: str, csrf_token: str) -> None:
        self.client = APIClient(
            base_url=base_url,
            csrf_token=csrf_token
        )
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def get_chat_history(session_name):
        return st.session_state.chat_histories.get(session_name, [])
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def generate_response():
        responses = [
            "Hello there! How can I assist you today?",
            "Hi, human! Is there anything I can help you with?",
            "Do you need help?",
        ]
        return random.choice(responses)
    
    def render_chat_env(self, session_name):
        chat_history = self.get_chat_history(session_name)
        
        # Display existing chat history
        for message in chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Handle new user input
        if prompt := st.chat_input("What is up?"):
            # Add and display user message
            chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate and display assistant response
            with st.chat_message("assistant"):
                response = self.generate_response()
                
                # Simulate streaming
                message_placeholder = st.empty()
                full_response = ""
                for chunk in response.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            
            # Add assistant response to chat history
            chat_history.append({"role": "assistant", "content": response})
            
            # Update session state
            st.session_state.chat_histories[session_name] = chat_history
            
            # Use query parameters to force a rerun without full page reload
            #st.rerun()