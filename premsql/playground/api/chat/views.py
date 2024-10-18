import json
from datetime import datetime

from django.utils.dateparse import parse_datetime
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .drf_serializers import (
    ChatMessageCreationRequestSerializer,
    ChatMessageCreationResponseSerializer,
    ChatMessageListResponseSerializer,
    SessionCreationRequestSerializer,
    SessionCreationResponseSerializer,
    SessionDeletionRequestSerializer,
    SessionDeletionResponseSerializer,
    SessionListResponseSerializer,
    SessionSummarySerializer,
    SessionUpdateRequestSerializer,
    SessionUpdateResponseSerializer,
)
from .serializers import (
    ChatMessageCreationRequest,
    ChatMessageListRequest,
    SessionCreationRequest,
    SessionListResponse,
    SessionSummary,
    SessionUpdateRequest,
)
from .services.chat_service import ChatService
from .services.session_service import SessionService

# Session Management views


@swagger_auto_schema(
    method="post",
    request_body=SessionCreationRequestSerializer,
    responses={
        200: SessionCreationResponseSerializer,
        400: "Bad Request",
        500: SessionCreationResponseSerializer,
    },
)
@api_view(["POST"])
def create_session(request):
    try:
        session_request = SessionCreationRequest(**request.data)
        response = SessionService().create_session(session_request)
        return Response(response.dict())
    except json.JSONDecodeError:
        return Response(
            {"status": "error", "error_message": "Invalid JSON"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(
    method="post",
    request_body=SessionUpdateRequestSerializer,
    responses={
        200: SessionUpdateResponseSerializer,
        400: "Bad Request",
        500: "Internal Server Error",
    },
)
@api_view(["POST"])
def update_session(request):
    try:
        session_request = SessionUpdateRequest(**request.data)
        response = SessionService().update_session(session_request)
        return Response(response.model_dump())
    except json.JSONDecodeError:
        return Response(
            {"status": "error", "error_message": "Invalid JSON"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "session_name",
            openapi.IN_PATH,
            description="Name of the session",
            type=openapi.TYPE_STRING,
        ),
    ],
    responses={200: SessionSummarySerializer, 404: "Not Found"},
)
@api_view(["GET"])
def get_session(request, session_name):
    session = SessionService().get_session(session_name)
    if session:
        session_summary = SessionSummary.from_orm(session)
        response = SessionListResponse(
            status="success",
            status_code=200,
            message="Session retrieved successfully",
            data=[session_summary.dict()],  # Convert to dict and wrap in a list
            total_count=1,
            page=1,
            page_size=1,
        )
    else:
        response = SessionListResponse(
            status="error",
            status_code=500,
            message="Session not found",
            error_message="The requested session does not exist",
        )
    return Response(
        response.dict(exclude_none=True),
        status=status.HTTP_200_OK if session else status.HTTP_404_NOT_FOUND,
    )


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "page",
            openapi.IN_QUERY,
            description="Page number",
            type=openapi.TYPE_INTEGER,
            default=1,
        ),
        openapi.Parameter(
            "page_size",
            openapi.IN_QUERY,
            description="Number of items per page",
            type=openapi.TYPE_INTEGER,
            default=20,
        ),
    ],
    responses={200: SessionListResponseSerializer},
)
@api_view(["GET"])
def list_sessions(request):
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    response = SessionService().list_session(page, page_size)
    return Response(response.dict())


@swagger_auto_schema(
    method="post",
    request_body=SessionDeletionRequestSerializer,
    responses={
        200: SessionDeletionResponseSerializer,
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["POST"])
def delete_session(request):
    try:
        session_name = request.data.get("session_name")
        if not session_name:
            return Response(
                {"status": "error", "error_message": "session_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = SessionService().get_session(session_name)
        if not session:
            return Response(
                {"status": "error", "error_message": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        session.delete()
        return Response(
            {
                "status": "success",
                "message": f"Session '{session_name}' deleted successfully",
                "deleted_at": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Chat Management Views


@swagger_auto_schema(
    method="post",
    request_body=ChatMessageCreationRequestSerializer,
    responses={
        200: ChatMessageCreationResponseSerializer,
        400: "Bad Request",
        500: ChatMessageCreationResponseSerializer,
    },
)
@api_view(["POST"])
def create_chat_message(request):
    try:
        chat_creation_request = ChatMessageCreationRequest(**request.data)
        response = ChatService().single_chat_cycle(request=chat_creation_request)
        return Response(response.dict())
    except json.JSONDecodeError:
        return Response(
            {"status": "error", "error_message": "Invalid JSON"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(
    method="get",
    manual_parameters=[
        openapi.Parameter(
            "session_name",
            openapi.IN_QUERY,
            description="Session name",
            type=openapi.TYPE_STRING,
            required=True,
        ),
        openapi.Parameter(
            "page",
            openapi.IN_QUERY,
            description="Page number",
            type=openapi.TYPE_INTEGER,
            default=1,
        ),
        openapi.Parameter(
            "page_size",
            openapi.IN_QUERY,
            description="Number of items per page",
            type=openapi.TYPE_INTEGER,
            default=20,
        ),
        openapi.Parameter(
            "start_date",
            openapi.IN_QUERY,
            description="Start date for filtering (ISO format)",
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            "end_date",
            openapi.IN_QUERY,
            description="End date for filtering (ISO format)",
            type=openapi.TYPE_STRING,
        ),
    ],
    responses={
        200: ChatMessageListResponseSerializer,
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["GET"])
def history(request):
    try:
        session_name = request.query_params.get("session_name")
        if not session_name:
            return Response(
                {"status": "error", "error_message": "session_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if start_date:
            start_date = parse_datetime(start_date)
            if not start_date:
                raise ValidationError(
                    "Invalid start_date format. Use ISO format (e.g., '2023-04-21T10:00:00Z')."
                )

        if end_date:
            end_date = parse_datetime(end_date)
            if not end_date:
                raise ValidationError(
                    "Invalid end_date format. Use ISO format (e.g., '2023-04-21T10:00:00Z')."
                )

        chat_list_request = ChatMessageListRequest(
            session_name=session_name,
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
        )
        response = ChatService().history_from_session(request=chat_list_request)
        return Response(response.dict(), status=status.HTTP_200_OK)
    except ValueError:
        return Response(
            {"status": "error", "error_message": "Invalid page or page_size"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except ValidationError as ve:
        return Response(
            {"status": "error", "error_message": str(ve)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
