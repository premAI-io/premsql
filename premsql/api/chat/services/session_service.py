from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from datetime import datetime

from chat.models import Session
from chat.serializers import *
from chat.constants import INFERENCE_SERVER_PORT, INFERENCE_SERVER_URL
from .server_operator import ServerManager

class SessionService:
    @staticmethod
    def create_session(request: SessionCreationRequest) -> SessionCreationResponse:
        pass 