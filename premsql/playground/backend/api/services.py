import subprocess
from typing import Optional

import requests
from api.models import Completions, Session
from api.pydantic_models import (
    CompletionCreationRequest,
    CompletionCreationResponse,
    CompletionListResponse,
    CompletionSummary,
    SessionCreationRequest,
    SessionCreationResponse,
    SessionDeleteResponse,
    SessionListResponse,
    SessionSummary,
)
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import transaction

from premsql.logger import setup_console_logger
from premsql.agents.base import AgentOutput
from premsql.agents.memory import AgentInteractionMemory
from premsql.playground import InferenceServerAPIClient
from premsql.playground.backend.api.utils import stop_server_on_port

logger = setup_console_logger("[SESSION-MANAGER]")

# TODO: # When delete a session, then it should delete the memory of the session
# TODO: # when fetching the history it should just give out the message_id in the current django db
# and then using that we can iteratively request the history to give history chats one by one


class SessionManageService:
    def __init__(self) -> None:
        self.client = InferenceServerAPIClient()

    def create_session(
        self, request: SessionCreationRequest
    ) -> SessionCreationResponse:
        response = self.client.get_session_info(base_url=request.base_url)
        if response.get("status") == 500:
            return SessionCreationResponse(
                status_code=500,
                status="error",
                error_message="Can not start session, internal server error. Try Again!",
            )

        try:
            session = Session.objects.create(
                session_name=response["session_name"],
                db_connection_uri=response["db_connection_uri"],
                created_at=response["created_at"],
                base_url=response["base_url"],
                session_db_path=response["session_db_path"],
            )
            logger.info(f"Successfully created session: {response['session_name']}")
            return SessionCreationResponse(
                status_code=200,
                status="success",
                session_id=session.session_id,
                session_name=session.session_name,
                db_connection_uri=response["db_connection_uri"],
                session_db_path=response["session_db_path"],
                created_at=session.created_at,
                error_message=None,
            )
        except Exception as e:
            return SessionCreationResponse(
                status_code=500,
                status="error",
                error_message=f"Can not start session. {e}",
            )

    def get_session(self, session_name: str) -> Optional[Session]:
        try:
            return Session.objects.get(session_name=session_name)
        except ObjectDoesNotExist:
            return None

    def list_session(self, page: int, page_size: int = 20) -> SessionListResponse:
        try:
            sessions = Session.objects.all().order_by("-created_at")
            paginator = Paginator(sessions, page_size)
            page_obj = paginator.get_page(page)
            session_summaries = [
                SessionSummary(
                    session_id=session.session_id,
                    session_name=session.session_name,
                    created_at=session.created_at,
                    base_url=session.base_url,
                    db_connection_uri=session.db_connection_uri,
                    session_db_path=session.session_db_path,
                )
                for session in page_obj
            ]
            return SessionListResponse(
                status="success",
                status_code=200,
                sessions=session_summaries,
                total_count=len(session_summaries),
                page=page,
                page_size=page_size,
            )
        except Exception as e:
            return SessionListResponse(
                status="error",
                status_code=500,
                session_summaries=None,
                total_count=0,
                page=page,
                page_size=page_size,
                error_message=f"Error listing sessions: {e}",
            )

    def delete_session(self, session_name: str):
        try:
            with transaction.atomic():
                session = Session.objects.get(session_name=session_name)
                try:
                    running_port = int(session.base_url.split(":")[1])
                    stop_server_on_port(port=running_port)
                except Exception as e:
                    logger.info(
                        "process killing failed, please shut down inference server manually"
                    )
                    pass

                # Proceed with deletion
                Completions.objects.filter(session_name=session_name).delete()
                session.delete()
                logger.info("Deleted all the chats")
                agent_memory = AgentInteractionMemory(
                    session_name=session_name, db_path=session.session_db_path
                )
                logger.info("Deleted the session registered inside PremSQL Agent")
                agent_memory.delete_table()
                return SessionDeleteResponse(
                    session_name=session_name,
                    status_code=200,
                    status="success",
                    error_message=None,
                )
        except Session.DoesNotExist:
            return SessionDeleteResponse(
                session_name=session_name,
                status_code=404,
                status="error",
                error_message="Session does not exist",
            )
        except Exception as e:
            return SessionDeleteResponse(
                session_name=session_name,
                status_code=500,
                status="error",
                error_message=f"Session does not exist: {e}",
            )


class CompletionService:
    def __init__(self) -> None:
        self.client = InferenceServerAPIClient()

    def completion(
        self, request: CompletionCreationRequest
    ) -> CompletionCreationResponse:
        try:
            session = Session.objects.get(session_name=request.session_name)
        except ObjectDoesNotExist:
            return CompletionCreationResponse(
                status_code=404,
                status="error",
                session_name=request.session_name,
                error_message=f"Session '{request.session_name}' not found",
            )

        try:
            # Small Hack ;_)
            base_url = session.base_url
            base_url = f"http://{base_url}"
            session_inference_response = self.client.post_completion(
                base_url=base_url, question=request.question
            )
        except Exception as e:
            logger.error(f"Unexpected error during completion: {str(e)}")
            return CompletionCreationResponse(
                status_code=500,
                status="error",
                session_name=session.session_name,
                error_message="An unexpected error occurred",
            )

        try:
            chat = Completions.objects.create(
                session=session,
                session_name=session.session_name,
                question=request.question,
                message_id=session_inference_response.get("message_id"),
                created_at=session_inference_response.get("message").get("created_at"),
            )

            logger.info(
                f"Chat completion created successfully for session: {session.session_name}"
            )
            agent_output = AgentOutput(**session_inference_response.get("message"))
            return CompletionCreationResponse(
                status_code=200,
                status="success",
                message_id=chat.message_id,
                session_name=session.session_name,
                created_at=chat.created_at,
                question=chat.question,
                message=agent_output,
            )

        except Exception as e:
            logger.error(f"Error saving completion: {str(e)}")
            return CompletionCreationResponse(
                status_code=500,
                status="error",
                session_name=session.session_name,
                error_message=f"Completion successful, but failed to save: {e}",
            )

    def chat_history(
        self, session_name: str, page: int, page_size: int = 20
    ) -> CompletionListResponse:
        try:
            session = Session.objects.get(session_name=session_name)
        except ObjectDoesNotExist:
            return CompletionListResponse(
                status="error",
                status_code=404,
                completions=[],
                total_count=0,
                page=page,
                page_size=page_size,
                error_message=f"Session '{session_name}' not found",
            )

        try:
            completions = Completions.objects.filter(session=session).order_by(
                "created_at"
            )
            paginator = Paginator(completions, page_size)
            page_obj = paginator.get_page(page)

            completion_summaries = [
                CompletionSummary(
                    message_id=completion.message_id,
                    session_name=completion.session_name,
                    base_url=completion.session.base_url,
                    created_at=completion.created_at,
                    question=completion.question,
                )
                for completion in page_obj
            ]

            return CompletionListResponse(
                status="success",
                status_code=200,
                completions=completion_summaries,
                total_count=completions.count(),
                page=page,
                page_size=page_size,
            )
        except Exception as e:
            return CompletionListResponse(
                status="error",
                status_code=500,
                completions=[],
                total_count=0,
                page=page,
                page_size=page_size,
                error_message=f"Error fetching chat history: {str(e)}",
            )
