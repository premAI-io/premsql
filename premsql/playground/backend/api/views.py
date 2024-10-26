import json

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from premsql.logger import setup_console_logger
from premsql.playground.backend.api.pydantic_models import (
    CompletionCreationRequest,
    SessionCreationRequest,
    SessionListResponse,
    SessionSummary,
)
from premsql.playground.backend.api.serializers import (
    CompletionCreationRequestSerializer,
    CompletionCreationResponseSerializer,
    CompletionListResponseSerializer,
    SessionCreationRequestSerializer,
    SessionCreationResponseSerializer,
    SessionListResponseSerializer,
    SessionSummarySerializer,
)

from .services import CompletionService, SessionManageService

logger = setup_console_logger("[VIEWS]")


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
        response = SessionManageService().create_session(request=session_request)
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
    responses={
        200: SessionSummarySerializer,
        400: "Bad Request",
        500: SessionSummarySerializer,
    },
)
@api_view(["GET"])
def get_session(request, session_name):
    session = SessionManageService().get_session(session_name=session_name)
    if session:
        session_summary = SessionSummary.model_validate(session)
        response = SessionListResponse(
            status="success",
            status_code=200,
            sessions=[session_summary.model_dump()],
            total_count=1,
            page=1,
            page_size=1,
        )
    else:
        response = SessionListResponse(
            status="error",
            status_code=500,
            error_message="The requested session does not exist.",
        )
    return Response(
        response.model_dump(),
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
    responses={
        200: SessionListResponseSerializer,
        400: "Bad Request",
        500: SessionListResponseSerializer,
    },
)
@api_view(["GET"])
def list_sessions(request):
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    response = SessionManageService().list_session(page=page, page_size=page_size)
    return Response(response.model_dump())


@swagger_auto_schema(
    method="delete",
    manual_parameters=[
        openapi.Parameter(
            "session_name",
            openapi.IN_PATH,
            description="Name of the session to delete",
            type=openapi.TYPE_STRING,
            required=True,
        ),
    ],
    responses={
        200: openapi.Response(
            "Session deleted successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "status": openapi.Schema(
                        type=openapi.TYPE_STRING, example="success"
                    ),
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
        404: "Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["DELETE"])
def delete_session(request, session_name):
    try:
        result = SessionManageService().delete_session(session_name=session_name)
        return Response(result.model_dump(), status=result.status_code)
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Completion Views


@swagger_auto_schema(
    method="post",
    request_body=CompletionCreationRequestSerializer,
    responses={
        200: CompletionCreationResponseSerializer,
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["POST"])
def create_completion(request):
    try:
        completion_request = CompletionCreationRequest(**request.data)
        response = CompletionService().completion(request=completion_request)
        return Response(
            response.model_dump(),
            status=(
                status.HTTP_200_OK
                if response.status == "success"
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
        )
    except ValidationError as e:
        return Response(
            {"status": "error", "error_message": str(e)},
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
    ],
    responses={
        200: CompletionListResponseSerializer,
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["GET"])
def get_chat_history(request, session_name):
    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        response = CompletionService().chat_history(
            session_name=session_name, page=page, page_size=page_size
        )

        return Response(
            response.model_dump(),
            status=(
                status.HTTP_200_OK
                if response.status == "success"
                else status.HTTP_404_NOT_FOUND
            ),
        )
    except ValueError:
        return Response(
            {"status": "error", "error_message": "Invalid page or page_size parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"status": "error", "error_message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
