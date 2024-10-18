from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from datetime import datetime

from chat.models import Session
from chat.serializers import (
    SessionCreationRequest,
    SessionCreationResponse,
    SessionListResponse,
    SessionSummary,
    SessionUpdateRequest,
    SessionUpdateResponse
)

from chat.constants import INFERENCE_SERVER_PORT, INFERENCE_SERVER_URL
from .server_operator import ServerManager

class SessionService:
    def __init__(self) -> None:
        self.manager = ServerManager()

    def create_session(
            self, request: SessionCreationRequest
        ) -> SessionCreationResponse:
        try:
            if self.manager.is_running(port=INFERENCE_SERVER_PORT):
                print(f"Stopping the server: {INFERENCE_SERVER_PORT}")
                self.manager.stop(port=INFERENCE_SERVER_PORT)
            
            config_path = request.config_path or None
            env_path = request.env_path or None
            
            include = request.include if request.include else None
            exclude = request.exclude if request.exclude else None

            if include is not None and exclude is not None:
                return SessionCreationResponse(
                    status="error",
                    status_code=500,
                    error_message="Can not include and exclude tables at the same time."
                )

            # Start the manager
            status = self.manager.start(
                dsn_or_db_path=request.db_connection_uri,
                agent_name=request.agent_name,
                config_path=config_path,
                env_path=env_path,
                include_tables=include,
                exclude_tables=exclude,
                port=INFERENCE_SERVER_PORT,
                host=INFERENCE_SERVER_URL
            )
        except Exception as e:
            return SessionCreationResponse(
                status="error",
                status_code=500,
                error_message=str(e)
            )      

        # If successful then log to the database 
        if status == False:
            return SessionCreationResponse(
                status="error",
                status_code=500,
                error_message="Server starting error, Try again"
            )
        
        try:
            session = Session.objects.create(
                session_name=request.session_name,
                agent_name=request.agent_name,
                db_type=request.db_type,
                db_connection_uri=request.db_connection_uri,
                include=request.include,
                exclude=request.exclude,
                config_path=request.config_path,
                env_path=request.env_path
            )
            return SessionCreationResponse(
                status="success",
                status_code=200,
                session_id=session.session_id,
                session_name=session.session_name,
                created_at=session.created_at
            )
        except Exception as e:
            return SessionCreationResponse(
                status="error",
                status_code=500,
                error_message=str(e)
            ) 
    
    def update_session(self, request: SessionUpdateRequest) -> SessionUpdateResponse:
        try:
            session = Session.objects.get(session_name=request.session_name)

            # Stop the current server if it's running
            if self.manager.is_running(port=INFERENCE_SERVER_PORT):
                print(f"Stopping the server: {INFERENCE_SERVER_PORT}")
                self.manager.stop(port=INFERENCE_SERVER_PORT)

            config_path = request.config_path or None
            env_path = request.env_path or None
            
            include = request.include if request.include else None
            exclude = request.exclude if request.exclude else None

            if include is not None and exclude is not None:
                return SessionUpdateResponse(
                    status="error",
                    status_code=500,
                    error_message="Can not include and exclude tables at the same time."
                )

            # Start the manager with updated parameters
            status = self.manager.start(
                dsn_or_db_path=request.db_connection_uri or session.db_connection_uri,
                agent_name=request.agent_name or session.agent_name,
                config_path=config_path,
                env_path=env_path,
                include_tables=include,
                exclude_tables=exclude,
                port=INFERENCE_SERVER_PORT,
                host=INFERENCE_SERVER_URL
            )
            # If successful then update the database
            if status:
                return SessionUpdateResponse(
                    status="error",
                    status_code=500,
                    error_message="Server starting error, Try again"
                )

            # Update session attributes
            for field, value in request.model_dump(exclude_unset=True).items():
                setattr(session, field, value)
            session.save()
            return SessionUpdateResponse(
                status="success",
                status_code=200,
                session_id=session.session_id,
                session_name=session.session_name,
                updated_at=datetime.now()
            )
        except ObjectDoesNotExist:
            return SessionUpdateResponse(
                status="error",
                status_code=500,
                error_message=f"Session '{request.session_name}' not found"
            )
        except Exception as e:
            return SessionUpdateResponse(
                status="error",
                status_code=500,
                error_message=f"Internal Server Error: {e}"
            )
    
    def get_session(self, session_name: str) -> Optional[Session]:
        try:
            return Session.objects.get(session_name=session_name)
        except ObjectDoesNotExist:
            return None
        
    def list_session(self, page: int = 1, page_size: int = 20) -> SessionListResponse:
        try:
            sessions = Session.objects.all().order_by(
                "-created_at"
            )
            paginator = Paginator(sessions, page_size)
            page_obj = paginator.get_page(page)
            
            session_summaries = [
                SessionSummary(
                    session_id=session.session_id,
                    session_name=session.session_name,
                    created_at=session.created_at,
                    agent_name=session.agent_name,
                    config_path=session.config_path,
                    db_type=session.db_type,
                    db_connection_uri=session.db_connection_uri,
                    has_env=session.env_path is not None 
                )
                for session in page_obj
            ]
            return SessionListResponse(
                status="success",
                status_code=200,
                message="Sessions retrieved successfully",
                data=session_summaries,
                total_count=paginator.count,
                page=page,
                page_size=page_size,
            )
        
        except Exception as e:
            return SessionListResponse(
                status="error",
                status_code=500,
                message="Failed to retrieve sessions",
                error_message=str(e)
            )