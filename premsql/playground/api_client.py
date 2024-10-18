from typing import Any, Dict, Optional

import requests


class APIClient:
    def __init__(self, base_url: str, csrf_token: str) -> None:
        self.base_url = base_url
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token,
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, params=params, json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            return {"error": str(e)}

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        return self._make_request("POST", endpoint, data=data)

    def delete(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self._make_request("DELETE", endpoint, data=data)

    def create_session(self, session_data: Dict) -> Dict[str, Any]:
        request_data = {
            "session_name": session_data.get("session_name", "default_session"),
            "agent_name": session_data.get("agent_name", "simple_agent"),
            "db_type": session_data.get("db_type", "sqlite"),
            "db_connection_uri": session_data.get("db_connection_uri", ""),
            "include": session_data.get("include", ""),
            "exclude": session_data.get("exclude", ""),
            "config_path": session_data.get("config_path", ""),
            "env_path": session_data.get("env_path", ""),
        }
        return self.post("/api/session/create/", data=request_data)

    def delete_session(self, session_name: str) -> Dict[str, Any]:
        return self.post("/api/session/delete/", data={"session_name": session_name})

    def list_sessions(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        return self.get(
            "/api/session/list/", params={"page": page, "page_size": page_size}
        )

    def get_session(self, session_name: str) -> Dict[str, Any]:
        return self.get(f"/api/session/{session_name}/")

    # Chats
    def get_message_history(self, session_name: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        return self.get(
            "/api/message/history/",
            params={"session_name": session_name, "page": page, "page_size": page_size}
        )

    def create_message(self, message_data: Dict) -> Dict[str, Any]:
        request_data = {
            "session_name": message_data["session_name"],
            "query": message_data["query"],
            "additional_knowledge": message_data.get("additional_knowledge", ""),
            "few_shot_examples": message_data.get("few_shot_examples", {})
        }
        return self.post("/api/message/create/", data=request_data)
    