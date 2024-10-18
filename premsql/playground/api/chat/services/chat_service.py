import requests
from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from datetime import datetime

from chat.models import ChatMessage, Session
from chat.serializers import (
    ChatMessageCreationRequest,
    ChatMessageCreationResponse,
    ChatMessageListRequest,
    ChatMessageListResponse,
    ChatMessageSummary
)
from chat.constants import BASE_URL, INFERENCE_SERVER_PORT, INFERENCE_SERVER_URL
from .server_operator import ServerManager

def query_inference_server(
    server_url: str,
    question: str,
    additional_knowledge: Optional[str]=None,
    few_shot_examples: Optional[str]=None,
) -> dict:
    endpoint = f"{server_url}/query"
    payload = {
        "question": question,
        "additional_knowledge": additional_knowledge,
        "few_shot_examples": few_shot_examples
    }

    try:
        response = requests.post(
            endpoint, json=payload
        )

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise requests.RequestException(
            f"Error querying the inference server: {str(e)}"
        )
    except ValueError as e:
        raise ValueError(
            f"Error parsing the server response: {str(e)}"
        )

class ChatService:
    def __init__(self):
        self.manager = ServerManager()

    def single_chat_cycle(
        self, request: ChatMessageCreationRequest
    ) -> ChatMessageCreationResponse:
        try:
            session = Session.objects.get(session_name=request.session_name)
        except Session.DoesNotExist:
            return ChatMessageCreationResponse(
                status="error",
                status_code=500,
                error_message=f"Session: {request.session_name} does not exist"
            )
        
        if not self.manager.is_running(port=INFERENCE_SERVER_PORT):
            status = self.manager.start(
                dsn_or_db_path=session.db_connection_uri,
                agent_name=session.agent_name,
                config_path=session.config_path,
                env_path=session.env_path,
                include_tables=session.include,
                exclude_tables=session.exclude,
                port=INFERENCE_SERVER_PORT,
                host=INFERENCE_SERVER_URL
            )
            if status == False:
                return ChatMessageCreationResponse(
                    status="error",
                    status_code=500,
                    error_message="Inference server is not running. Try again"
                )
            print("Server started")
        print("Server running")

        try:
            response = query_inference_server(
                server_url=BASE_URL,
                question=request.query,
                additional_knowledge=request.additional_knowledge,
                few_shot_examples=request.few_shot_examples
            )
            # TODO: Need to check with main.py
            chat = ChatMessage.objects.create(
                session=session,
                query=request.query,
                additional_knowledge=request.additional_knowledge,
                few_shot_examples=request.few_shot_examples,
                sql_string=response.get('sql', ''),
                bot_message=response.get('bot_message', ''),
                dataframe=response["table"]["data"] or None,
                plot_image=response.get('plot', None),
                plot_dataframe=response.get('plot_dataframe', None),
                error_message=response.get('error', None)
            )
            return ChatMessageCreationResponse(
                status="success",
                status_code=200,
                message_id=chat.message_id,
                session_name=request.session_name,
                created_at=chat.created_at,
                additional_knowledge=chat.additional_knowledge,
                few_shot_examples=chat.few_shot_examples,
                sql_string=chat.sql_string,
                bot_message=chat.bot_message,
                dataframe=chat.dataframe,
                plot_image=chat.plot_image,
                plot_dataframe=chat.plot_dataframe
            )
        except Exception as e:
            return ChatMessageCreationResponse(
                status="error",
                status_code=500,
                error_message=f"An error occured: {str(e)}"
            )
            
             