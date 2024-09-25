from rest_framework import generics, status
from rest_framework.response import Response

from .models import ChatMessage, Session, TableFilter
from .serializers import ChatMessageSerializer, SessionSerializer
from .services import ChatService


class SessionCreateView(generics.CreateAPIView):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer


class ChatMessageCreateView(generics.CreateAPIView):
    query_set = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = serializer.validated_data["session"]
        query = serializer.validated_data["query"]
        llm = serializer.validated_data.get("llm")
        temperature = serializer.validated_data.get("temperature")
        max_new_tokens = serializer.validated_data.get("max_new_tokens")

        chat_message = ChatService.process_chat(
            session=session,
            query=query,
            llm=llm,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
        )
        return Response(
            ChatMessageSerializer(chat_message).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        table_filters = TableFilter.objects.filter(session=self.get_object())
        data["tables_to_include"] = [
            table.table_name for table in table_filters if table.include
        ]
        data["tables_to_exclude"] = [
            table.table_name for table in table_filters if not table.include
        ]
        return Response(data)
