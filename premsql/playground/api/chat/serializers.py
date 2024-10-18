from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

#                                Session Schemas                                #


# Session Creation (POST)
class SessionCreationRequest(BaseModel):
    session_name: str = Field(..., max_length=255)

    agent_name: str = Field(max_length=255, default="simple_agent")
    db_type: str = Field(default="sqlite", max_length=255)
    db_connection_uri: Optional[str] = Field(default=None, max_length=255)

    include: Optional[str] = Field(default=None)
    exclude: Optional[str] = Field(default=None)

    config_path: Optional[str] = Field(default=None)
    env_path: Optional[str] = Field(default=None)

    class Config:
        extra = "forbid"


class SessionCreationResponse(BaseModel):
    status: Literal["success", "error"] = Field(
        ..., description="The status of the response"
    )
    status_code: Literal[200, 500] = Field(...)
    session_id: Optional[int] = Field(None)
    session_name: Optional[str] = Field(None, description="The name of the session")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp of session creation"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the request failed"
    )


# Session Deletion (POST)
class SessionDeletionRequest(BaseModel):
    session_name: str = Field(...)


class SessionDeletionResponse(BaseModel):
    status: Literal["success", "error"] = Field(
        ..., description="The status of the response"
    )
    status_code: Literal[200, 500] = Field(...)
    session_id: Optional[int] = Field(None)
    session_name: Optional[str] = Field(
        None, description="The name of the deleted session"
    )
    deleted_at: Optional[datetime] = Field(
        None, description="Timestamp of session deletion"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the request failed"
    )


# Session Update (POST)
class SessionUpdateRequest(BaseModel):
    session_name: str = Field(..., max_length=255)

    agent_name: str = Field(max_length=255, default="simple_agent")
    db_type: str = Field(default="sqlite", max_length=255)
    db_connection_uri: Optional[str] = Field(default=None, max_length=255)

    include: Optional[str] = Field(default=None)
    exclude: Optional[str] = Field(default=None)

    config_path: Optional[str] = Field(default=None)
    env_path: Optional[str] = Field(default=None)


class SessionUpdateResponse(BaseModel):
    status: Literal["success", "error"] = Field(
        ..., description="The status of the response"
    )
    status_code: Literal[200, 500] = Field(...)
    session_id: Optional[int] = Field(None)
    session_name: Optional[str] = Field(None, description="The name of the session")
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp of session update"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the request failed"
    )


# Session List (GET)
class SessionSummary(BaseModel):
    session_id: int = Field(..., description="The unique identifier for the session")
    session_name: str = Field(..., max_length=255)
    created_at: datetime = Field(..., description="Timestamp of session creation")
    agent_name: str = Field(..., max_length=255)
    db_type: str = Field(..., max_length=255)
    db_connection_uri: str = Field(...)

    config_path: Optional[str] = Field(...)
    has_env: Optional[bool] = Field(default=False)

    class Config:
        orm_mode = True
        from_attributes = True


class SessionListResponse(BaseModel):
    status: Literal["success", "error"] = Field(
        ..., description="The status of the response"
    )
    status_code: Literal[200, 500] = Field(...)
    message: str = Field(
        ..., description="A message describing the result of the operation"
    )
    data: Optional[List[SessionSummary]] = Field(
        None, description="List of session summaries"
    )
    total_count: Optional[int] = Field(None, description="Total number of sessions")
    page: Optional[int] = Field(None, description="Current page number")
    page_size: Optional[int] = Field(None, description="Number of items per page")
    error_message: Optional[str] = Field(
        None, description="Error message if the request failed"
    )


#                                ChatMessage Schemas                                #


class ChatMessageCreationRequest(BaseModel):
    session_name: str = Field(...)
    query: str = Field(...)
    additional_knowledge: Optional[str] = Field(default=None)
    few_shot_examples: Optional[dict] = Field(default=None)


class ChatMessageCreationResponse(BaseModel):
    status: Literal["success", "error"] = Field(
        ..., description="The status of the response"
    )
    status_code: Literal[200, 500] = Field(...)
    message_id: Optional[int] = Field(...)
    session_name: Optional[str] = Field(None, description="The name of the session")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp of message creation"
    )

    # User parameters
    query: Optional[str] = Field(None, description="User's input query")
    additional_knowledge: Optional[str] = Field(
        None, description="Additional knowledge provided by the user"
    )
    few_shot_examples: Optional[dict] = Field(
        None, description="Few-shot examples provided by the user"
    )

    # Bot parameters
    sql_string: Optional[str] = Field(None, description="Generated SQL string")
    bot_message: Optional[str] = Field(None, description="Bot's response message")
    dataframe: Optional[dict] = Field(
        None, description="Dataframe representation of the response"
    )
    plot_image: Optional[str] = Field(None, description="Plot image URL if available")
    plot_dataframe: Optional[dict] = Field(
        None, description="Plot dataframe for frontend rendering"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the request failed"
    )


class ChatMessageSummary(BaseModel):
    message_id: int = Field(..., description="Unique identifier for the chat message")
    session_name: str = Field(
        ..., description="Name of the session this message belongs to"
    )
    created_at: datetime = Field(..., description="Timestamp of message creation")
    query: str = Field(..., description="User's input query")
    bot_message: Optional[str] = Field(default=None)
    sql_string: str = Field(..., description="Generated SQL string")
    dataframe: Optional[dict] = Field(default=None)
    plot_image: Optional[str] = Field(default=None)
    plot_dataframe: Optional[dict] = Field(default=None)

    class Config:
        orm_mode = True


class ChatMessageListResponse(BaseModel):
    status: Literal["success", "error"] = Field(
        ..., description="The status of the response"
    )
    status_code: Literal[200, 500] = Field(...)

    data: Optional[List[ChatMessageSummary]] = Field(
        None, description="List of chat message summaries"
    )
    total_count: Optional[int] = Field(
        None, description="Total number of chat messages"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if the request failed"
    )


# Chat Message List Request for Filtering and Pagination
class ChatMessageListRequest(BaseModel):
    session_name: Optional[str] = Field(
        None, description="Filter messages by session name"
    )
    start_date: Optional[datetime] = Field(
        None, description="Filter messages created on or after this date"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter messages created on or before this date"
    )
    page: int = Field(1, description="Page number for pagination")
    page_size: int = Field(20, description="Number of items per page")

    class Config:
        extra = "forbid"
