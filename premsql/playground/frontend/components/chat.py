import pandas as pd 
import streamlit as st
from premsql.playground.backend.backend_client import BackendAPIClient
from premsql.playground.inference_server.api_client import InferenceServerAPIClient
from premsql.playground.backend.api.pydantic_models import CompletionCreationRequest
from premsql.playground.frontend.components.streamlit_plot import StreamlitPlotTool
from premsql.agents.memory import AgentInteractionMemory
from premsql.agents.utils import convert_exit_output_to_agent_output
from premsql.agents.models import ExitWorkerOutput, AgentOutput
from premsql.logger import setup_console_logger

logger = setup_console_logger("FRONTEND-CHAT")

class ChatComponent:
    def __init__(self) -> None:
        self.backend_client = BackendAPIClient()
        self.inference_client = InferenceServerAPIClient()
        self.plotter = StreamlitPlotTool()
    
    def _streamlit_chat_output(self, message: AgentOutput | ExitWorkerOutput):
        if isinstance(message, ExitWorkerOutput):
            message = convert_exit_output_to_agent_output(exit_output=message)

        if message.output_dataframe:
            try:
                df = message.output_dataframe
                df = pd.DataFrame(df["data"], columns=df["columns"])
                if message.plot_config is None:
                    st.dataframe(df)
            except Exception as e:
                st.error(f"Error: {e}")

        if message.analysis:
            st.markdown(message.analysis)
        if message.plot_config:
            df = message.input_dataframe
            if df:
                self.plotter.run(
                    data=pd.DataFrame(df["data"], columns=df["columns"]),
                    plot_config=message.plot_config
                )
        if message.followup_suggestion:
            st.warning(message.followup_suggestion)
        with st.expander(label="Reasoning"):
            if message.sql_string:
                st.code(message.sql_string) 
            if message.reasoning:
                st.markdown(message.reasoning)
            if message.plot_config:
                st.json(message.plot_config)
            if message.error_from_pipeline:
                st.error(message.error_from_pipeline)


    def render_chat_env(self, session_name: str) -> None:
        session_info = self.backend_client.get_session(
            session_name=session_name
        )
        if session_info.status_code == 500:
            st.error(f"Failed to render chat History for session: {session_name}")

        session = session_info.sessions[0]
        session_db_path = session.session_db_path
        base_url = session.base_url
        # TODO: Need to understand how can I start the session

        history = AgentInteractionMemory(
            session_name=session_name, db_path=session_db_path
        )

        messages = history.generate_messages_from_session(session_name=session_name, server_mode=True)
        if not messages:
            st.warning("No chat history available for this session.")
        else:
            for message in messages:
                with st.chat_message("user"): st.markdown(message.question)
                with st.chat_message("assistant"):
                    self._streamlit_chat_output(message=message)
                        
        
        base_url = f"http://{base_url}" if not base_url.startswith("http://") else base_url
        is_session_online_status = self.inference_client.is_online(base_url=base_url)
        if is_session_online_status != 200:
            st.divider()
            st.warning(f"Session ended. Restart Agent Server to start the session at: {base_url}")
        
        else:
            if prompt := st.chat_input("What is your question?"):
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = self.backend_client.create_completion(
                            CompletionCreationRequest(
                                session_name=session_name,
                                question=prompt
                            )
                        )
                        if response.status_code == 200:
                            self._streamlit_chat_output(
                                message=history.get_by_message_id(message_id=response.message_id)
                            )
                        else:
                            st.error("Something went wrong. Try again")


                
        

