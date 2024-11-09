import streamlit as st
from premsql.playground.backend.backend_client import BackendAPIClient
from premsql.playground.backend.api.pydantic_models import SessionCreationRequest

additional_link_markdown = """
Here are some quick links to get you started with Prem:

- Head over to [Prem App](https://app.premai.io/projects/) to start building on Gen AI.
- [Prem AI documentation](https://docs.premai.io/get-started/why-prem)
- [PremSQL documentation](https://docs.premai.io/premsql/introduction)
"""

class SessionComponent:
    def __init__(self) -> None:
        self.backend_client = BackendAPIClient()
    
    def render_list_sessions(self):
        with st.sidebar:
            st.sidebar.title("Your Past Sessions")
            all_sessions = self.backend_client.list_sessions(page_size=100).sessions
            if all_sessions:
                all_sessions = [session.session_name for session in all_sessions]

                selected_session = st.selectbox(
                    label="Your Sessions (refresh if you have created a new one)",
                    options=all_sessions,
                )
                return selected_session
    
    def render_register_session(self):
        with st.sidebar:
            st.sidebar.title("Register new Session")
            with st.form(
                key="session_creation",
                clear_on_submit=True,
                border=100,
                enter_to_submit=False,
            ):
                base_url = st.text_input(
                    label="base_url",
                    placeholder="the base url in which AgentServer is running"
                )
                button = st.form_submit_button(label="Submit")
            if button:
                response = self.backend_client.create_session(
                    request=SessionCreationRequest(base_url=base_url)
                )
                if response.status_code == 500:
                    st.toast(body=st.markdown(response.error_message), icon="❌")
                else:
                    st.toast(body=f"Session: {response.session_name} created successfully", icon="🥳")
                return response
    
    def render_additional_links(self):
        with st.sidebar:
            with st.container(height=200):
                st.markdown(additional_link_markdown)

    
    def render_delete_session_view(self):
        with st.sidebar:
            with st.expander(label="Delete a session"):
                with st.form(key="delete_session", clear_on_submit=True, enter_to_submit=False):
                    session_name = st.text_input(label="Enter session name")
                    button = st.form_submit_button(label="Submit")
                    if button:
                        all_sessions = self.backend_client.list_sessions(page_size=100).sessions
                        all_sessions = [session.session_name for session in all_sessions]
                        if session_name not in all_sessions:
                            st.error("Session does not exist")
                        else:
                            self.backend_client.delete_session(session_name=session_name)
                            st.success(f"Deleted session: {session_name}. Please refresh")