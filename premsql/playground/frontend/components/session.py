import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st

from premsql.playground.api_client import APIClient

class SessionComponent:
    def __init__(self, base_url: str, csrf_token: str) -> None:
        self.client = APIClient(base_url=base_url, csrf_token=csrf_token)

    def render_list_sessions(self):
        with st.sidebar: 
            st.sidebar.title("Your Sessions")
            all_sessions = self.client.list_sessions(page_size=100)
            all_sessions = [
                session["session_name"] for session in all_sessions["data"]
            ]
            selected_session = st.selectbox(
                label="Your Sessions (refresh if you have created a new one)",
                options=all_sessions
            )
            return selected_session

    def render_create_session(self):
        with st.sidebar:
            st.sidebar.title("New Session")
            with st.form(
                key="session_creation", clear_on_submit=True,
                border=100,
                enter_to_submit=False
            ):
                session_name = st.text_input(
                    label="session_name",
                    placeholder="do not add space or special characters"
                )
                agent_name = st.text_input(
                    label="agent_name",
                    placeholder="do not add space or special characters"
                ) 
                dsn_or_db_path = st.text_input(
                    label="dsn_or_db_path",
                    placeholder="please put a valid database URI"
                )
                db_type = st.selectbox(
                    label="Select the database type",
                    options=["sqlite", "postgres"]
                )
                config_path = st.file_uploader(
                    label="Upload custom config path",
                    type=".py"
                )

                env_path = st.file_uploader(
                    label="Upload .env file if your agent needs",
                    type=".env"
                )
                include_tables = st.text_input(
                    label="Put a comma seperated names of the table you want to include",
                    placeholder="table1,table2"
                )
                exclude_tables = st.text_input(
                    label="Put a comma seperated names of the table you want to exclude",
                    placeholder="table1,table2"
                )

                if include_tables is not None and exclude_tables is not None:
                    st.warning("Both include and exclude tables can not be entered")
                
                # May be add a widget callback
                button = st.form_submit_button(label="Submit")

            if button:
                config_path_str, env_path_str = None, None
                if config_path is not None:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".py"
                    ) as temp_file:
                        temp_file.write(config_path.getvalue())
                        config_path_str = temp_file.name
                
                if env_path is not None:
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".env"
                    ) as temp_file:
                        temp_file.write(env_path.getvalue())
                        env_path_str = temp_file.name

                response = self.client.create_session(
                    session_data=dict(
                        session_name=session_name,
                        agent_name=agent_name,
                        db_connection_uri=dsn_or_db_path,
                        db_type=db_type,
                        config_path=config_path_str,
                        env_path=env_path_str,
                        include_tables=include_tables,
                        exclude_tables=exclude_tables
                    )
                )

                if response["status"] == "success":
                    st.toast(body=f"New session: {session_name} created. Please refresh", icon="🥳") 
                else:
                    st.toast(body=f"Session creation failed. Try again", icon="❌")
                    st.write(response)
                
                return response

