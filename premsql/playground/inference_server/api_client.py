import requests
from typing import Optional, Dict, Any
from urllib.parse import urljoin

class InferenceServerAPIError(Exception):
    pass

class InferenceServerAPIClient:
    def __init__(self, timeout: int = 600) -> None:
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        self.timeout = timeout
    
    def _make_request(
        self, base_url: str, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = urljoin(base_url.rstrip('/'), endpoint)
        try:
            response = requests.request(
                method, url, headers=self.headers, json=data, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise InferenceServerAPIError(f"API request failed: {str(e)}")

    def post_completion(self, base_url: str, question: str) -> Dict[str, Any]:
        if not question.strip():
            raise ValueError("Question cannot be empty")
        endpoint = "/completion"
        data = {"question": question}
        return self._make_request(base_url, "POST", endpoint, data)

    def get_session_info(self, base_url: str) -> Dict[str, Any]:
        endpoint = "/session_info"
        return self._make_request(base_url, "GET", endpoint)
