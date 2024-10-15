from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json
from datetime import datetime
from .services import SessionService
from .serializers import (
    SessionCreationRequest,
    SessionUpdateRequest, 
    SessionSummary, SessionListResponse,
)
from .drf_serializers import (
    SessionCreationRequestSerializer, SessionCreationResponseSerializer,
    SessionUpdateRequestSerializer, SessionUpdateResponseSerializer,
    SessionDeletionRequestSerializer, SessionDeletionResponseSerializer,
    SessionSummarySerializer, SessionListResponseSerializer,
)

@swagger_auto_schema(
    method='post',
    request_body=SessionCreationRequestSerializer,
    responses={200: SessionCreationResponseSerializer, 400: 'Bad Request', 500: 'Internal Server Error'}
)
@api_view(['POST'])
def create_session(request):
    try:
        session_request = SessionCreationRequest(**request.data)
        response = SessionService.create_session(session_request)
        return Response(response.dict())
    except json.JSONDecodeError:
        return Response({"status": "error", "error_message": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "error_message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='post',
    request_body=SessionUpdateRequestSerializer,
    responses={200: SessionUpdateResponseSerializer, 400: 'Bad Request', 500: 'Internal Server Error'}
)
@api_view(['POST'])
def update_session(request):
    try:
        session_request = SessionUpdateRequest(**request.data)
        response = SessionService.update_session(session_request)
        return Response(response.dict())
    except json.JSONDecodeError:
        return Response({"status": "error", "error_message": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "error_message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('session_name', openapi.IN_PATH, description="Name of the session", type=openapi.TYPE_STRING),
    ],
    responses={200: SessionSummarySerializer, 404: 'Not Found'}
)
@api_view(['GET'])
def get_session(request, session_name):
    session = SessionService.get_session(session_name)
    if session:
        session_summary = SessionSummary.from_orm(session)
        response = SessionListResponse(
            status="success",
            message="Session retrieved successfully",
            data=[session_summary.dict()],  # Convert to dict and wrap in a list
            total_count=1,
            page=1,
            page_size=1
        )
    else:
        response = SessionListResponse(
            status="error",
            message="Session not found",
            error_message="The requested session does not exist"
        )
    return Response(response.dict(exclude_none=True), status=status.HTTP_200_OK if session else status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER, default=1),
        openapi.Parameter('page_size', openapi.IN_QUERY, description="Number of items per page", type=openapi.TYPE_INTEGER, default=20),
    ],
    responses={200: SessionListResponseSerializer}
)
@api_view(['GET'])
def list_sessions(request):
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    response = SessionService.list_session(page, page_size)
    return Response(response.dict())


@swagger_auto_schema(
    method='post',
    request_body=SessionDeletionRequestSerializer,
    responses={200: SessionDeletionResponseSerializer, 400: 'Bad Request', 404: 'Not Found', 500: 'Internal Server Error'}
)
@api_view(['POST'])
def delete_session(request):
    try:
        session_name = request.data.get('session_name')
        if not session_name:
            return Response({"status": "error", "error_message": "session_name is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        session = SessionService.get_session(session_name)
        if not session:
            return Response({"status": "error", "error_message": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        
        session.delete()
        return Response({
            "status": "success",
            "message": f"Session '{session_name}' deleted successfully",
            "deleted_at": datetime.now().isoformat()
        })
    except Exception as e:
        return Response({"status": "error", "error_message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)