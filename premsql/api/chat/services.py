import json
from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from .models import Session, ChatMessage
from .serializers import * 
from datetime import datetime

# Right now it is a dummy service which just hits the Database

class SessionService:
    @staticmethod
    def create_session(request: SessionCreationRequest) -> SessionCreationResponse:
        try:
            session = Session.objects.create(
                session_name=request.session_name,
                engine=request.engine,
                agent=request.agent,
                model_name=request.model_name,
                db_type=request.db_type,
                db_connection_uri=request.db_connection_uri,
                include=request.include,
                exclude=request.exclude,
                temperature=request.temperature,
                max_new_tokens=request.max_new_tokens
            )
            return SessionCreationResponse(
                status="success",
                session_name=session.session_name,
                created_at=session.created_at
            )
        except Exception as e:
            return SessionCreationResponse(
                status="error",
                error_message=str(e)
            ) 
    
    @staticmethod
    def update_session(request: SessionUpdateRequest) -> SessionUpdateResponse:
        try:
            session = Session.objects.get(session_name=request.session_name)
            for field, value in request.model_dump(exclude_unset=True).items():
                setattr(session, field, value)
            session.save()
            return SessionUpdateResponse(
                status="success",
                session_name=session.session_name,
                updated_at=datetime.now()
            )
        except ObjectDoesNotExist:
            return SessionUpdateResponse(
                status="error",
                error_message=f"Session '{request.session_name}' not found"
            )
        except Exception as e:
            return SessionUpdateResponse(
                status="error",
                error_message=f"Internal Server Error: {e}"
            )
    
    @staticmethod
    def get_session(session_name: str) -> Optional[Session]:
        try:
            return Session.objects.get(session_name=session_name)
        except ObjectDoesNotExist:
            return None
        
    @staticmethod
    def list_session(page: int = 1, page_size: int = 20) -> SessionListResponse:
        try:
            sessions = Session.objects.all()
            paginator = Paginator(sessions, page_size)
            page_obj = paginator.get_page(page)
            
            session_summaries = [
                SessionSummary(
                    session_id=session.session_id,
                    session_name=session.session_name,
                    created_at=session.created_at,
                    engine=session.engine,
                    db_type=session.db_type
                )
                for session in page_obj
            ]
            return SessionListResponse(
                status="success",
                message="Sessions retrieved successfully",
                data=session_summaries,
                total_count=paginator.count,
                page=page,
                page_size=page_size
            )
        
        except Exception as e:
            return SessionListResponse(
                status="error",
                message="Failed to retrieve sessions",
                error_message=str(e)
            )