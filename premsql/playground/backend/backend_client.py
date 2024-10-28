import requests
from premsql.logger import setup_console_logger
from premsql.playground.backend.api.pydantic_models import (
    SessionCreationResponse,
    SessionDeleteResponse,
    SessionListResponse,
    SessionCreationRequest,
    CompletionCreationRequest,
    CompletionCreationResponse,
    CompletionListResponse,
)

BASE_URL = "http://127.0.0.1:8000/api"

logger = setup_console_logger("BACKEND-API-CLIENT")


class BackendAPIClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def create_session(self, request: SessionCreationRequest) -> SessionCreationResponse:
        try:
            response = requests.post(
                f"{self.base_url}/session/create",
                json=request.model_dump(),
                headers=self.headers
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            return SessionCreationResponse(**response.json())
        except requests.RequestException as e:
            logger.error(f"Error creating session: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionCreationResponse(
                status="error",
                status_code=response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 500,
                error_message=f"Failed to create session: {str(e)}"
            )
        except ValueError as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionCreationResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}"
            )

        except requests.RequestException as e:
            logger.error(f"Error creating session: {str(e)}")
            logger.error(f"Response content: {response.text}")
            return SessionCreationResponse(
                status="error",
                status_code=response.status_code if hasattr(response, 'status_code') else 500,
                error_message=f"Failed to create session: {str(e)}"
            )
        except ValueError as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text}")
            return SessionCreationResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}"
            )

    def list_sessions(self, page: int = 1, page_size: int = 20) -> SessionListResponse:
        try:
            response = requests.get(
                f"{self.base_url}/session/list/",
                params={"page": page, "page_size": page_size},
                headers=self.headers
            )
            response.raise_for_status()
            return SessionListResponse(**response.json())
        except requests.RequestException as e:
            logger.error(f"Error listing sessions: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionListResponse(
                status="error",
                status_code=response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 500,
                error_message=f"Failed to list sessions: {str(e)}",
                sessions=[],
                total_count=0
            )
        except ValueError as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionListResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}",
                sessions=[],
                total_count=0
            )

    def get_session(self, session_name: str) -> SessionListResponse:
        try:
            response = requests.get(
                f"{self.base_url}/session/{session_name}/",
                headers=self.headers
            )
            response.raise_for_status()
            return SessionListResponse(**response.json())
        except requests.RequestException as e:
            logger.error(f"Error getting session: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionListResponse(
                status="error",
                status_code=response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 500,
                error_message=f"Failed to get session: {str(e)}",
                name="",
                created_at="",
                sessions=[]
            )
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionListResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}",
                name="",
                created_at="",
                sessions=[]
            )

    def delete_session(self, session_name: str) -> SessionDeleteResponse:
        try:
            response = requests.delete(
                f"{self.base_url}/session/{session_name}",
                headers=self.headers
            )
            response.raise_for_status()
            return SessionDeleteResponse(**response.json())
        except requests.RequestException as e:
            logger.error(f"Error deleting session: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionDeleteResponse(
                status="error",
                status_code=response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 500,
                error_message=f"Failed to delete session: {str(e)}"
            )
        except ValueError as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return SessionDeleteResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}"
            )

    # Chats
    def create_completion(self, request: CompletionCreationRequest) -> CompletionCreationResponse:
        try:
            response = requests.post(
                f"{self.base_url}/chat/completion",
                json=request.model_dump(),
                headers=self.headers
            )
            response.raise_for_status()
            return CompletionCreationResponse(**response.json())
        except requests.RequestException as e:
            logger.error(f"Error creating completion: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return CompletionCreationResponse(
                status="error",
                status_code=response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 500,
                error_message=f"Failed to create completion: {str(e)}",
                completion=""
            )
        except ValueError as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return CompletionCreationResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}",
                completion=""
            )
    
    def get_chat_history(self, session_name: str, page: int = 1, page_size: int = 20) -> CompletionListResponse:
        try:
            response = requests.get(
                f"{self.base_url}/chat/history/{session_name}/",
                params={"page": page, "page_size": page_size},
                headers=self.headers
            )
            response.raise_for_status()
            return CompletionListResponse(**response.json())
        except requests.RequestException as e:
            logger.error(f"Error getting chat history: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return CompletionListResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to get chat history: {str(e)}",
                completions=[],
                total_count=0
            )
        except ValueError as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            return CompletionListResponse(
                status="error",
                status_code=500,
                error_message=f"Failed to parse server response: {str(e)}",
                completions=[],
                total_count=0
            )
