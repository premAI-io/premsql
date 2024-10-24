from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from api.models import Session, Completions
from api.pydantic_models import (
    SessionCreationRequest,
    SessionCreationResponse,
    SessionListResponse,
    SessionSummary,
    CompletionCreationRequest,
    CompletionCreationResponse,
    CompletionListResponse
)
from premsql.playground import InferenceServerAPIClient
from premsql.logger import setup_console_logger
from premsql.pipelines.base import AgentOutput

logger = setup_console_logger("[SESSION-MANAGER]")

# TODO: From the client side while:
# - creating session: only provider base url | response (all details)
# - listing session: only provide the session name (if one specific) else no need
# -  deleting session: only session name 

class SessionManageService:
    def __init__(self) -> None:
        self.client = InferenceServerAPIClient()
    
    def create_session(self, request: SessionCreationRequest) -> SessionCreationResponse:
        response = self.client.get_session_info(base_url=request.base_url)
        if response.get("status") == 500:
            return SessionCreationResponse(
                status_code=500,
                status="error",
                error_message="Can not start session, internal server error. Try Again!"
            )

        try:
            session = Session.objects.create(
                session_name=response['session_name'],
                db_connection_uri=response['db_connection_uri'],
                created_at=response['created_at'],
                base_url=response['base_url'],
                session_db_path=response['session_db_path']
            )
            logger.info(f"Successfully created session: {response['session_name']}")
            return SessionCreationResponse(
                status_code=200,
                status="success",
                session_id=session.session_id,
                session_name=session.session_name,
                db_connection_uri=response['db_connection_uri'],
                session_db_path=response['session_db_path'],
                created_at=session.created_at,
                error_message=None
            )
        except Exception as e:
            return SessionCreationResponse(
                status_code=500,
                status="error",
                error_message=f"Can not start session. {e}"
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
                    session_db_path=session.session_db_path
                ) for session in page_obj
            ]
            return SessionListResponse(
                status="success",
                status_code=200,
                sessions=session_summaries,
                total_count=len(session_summaries),
                page=page,
                page_size=page_size
            ) 
        except Exception as e:
            return SessionListResponse(
                status="error",
                status_code=500,
                session_summaries=None,
                total_count=0,
                page=page,
                page_size=page_size,
                error_message=f"Error listing sessions: {e}"
            )
        

class CompletionService:
    def  __init__(self) -> None:
        self.client = InferenceServerAPIClient()
    
    def completion(self, request: CompletionCreationRequest) -> CompletionCreationResponse:
        try:
            session = Session.objects.get(session_name=request.session_name)
        except ObjectDoesNotExist:
            return CompletionCreationResponse(
                status_code=404,
                status="error",
                session_name=request.session_name,
                error_message=f"Session '{request.session_name}' not found"
            )
        
        try:
            base_url = session.base_url
            base_url = f"http://{base_url}"
            session_inference_response = self.client.post_completion(
                base_url=base_url,
                question=request.question
            )
        except Exception as e:
            logger.error(f"Unexpected error during completion: {str(e)}")
            return CompletionCreationResponse(
                status_code=500,
                status="error",
                session_name=session.session_name,
                error_message="An unexpected error occurred"
            )

        try:
            chat = Completions.objects.create(session=session)
            logger.info(f"Chat completion created successfully for session: {session.session_name}")
            return CompletionCreationResponse(
                status_code=200,
                status="success",
                message_id=chat.message_id,
                session_name=session.session_name,
                created_at=chat.created_at,
                message=AgentOutput(**session_inference_response)
            )
        except Exception as e:
            logger.error(f"Error saving completion: {str(e)}")
            return CompletionCreationResponse(
                status_code=500,
                status="error",
                session_name=session.session_name,
                error_message="Completion successful, but failed to save"
            )
         

    def chat_history(self):
        pass 