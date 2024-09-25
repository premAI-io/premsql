import json
from typing import Optional

from django.db import connections

from .models import ChatMessage, Session, TableFilter


class ChatService:
    @staticmethod
    def generate_sql(session, query, llm, temperature, max_new_tokens):
        table_filters = TableFilter.objects.filter(session=session)
        include_tables = [table.table_name for table in table_filters if table.include]
        exclude_tables = [
            table.table_name for table in table_filters if not table.include
        ]

        response_sql = "SELECT * from california_schools;"
        return response_sql

    @staticmethod
    def execute_sql(session: Session, sql):
        return {"data": "dummy"}

    @staticmethod
    def process_chat(
        session: Session,
        query: str,
        llm: Optional[str] = None,
        temperature: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
    ):
        sql = ChatService.generate_sql(session, query, llm, temperature, max_new_tokens)
        results = ChatService.execute_sql(session, sql)

        response = f"SQL Query: {sql}\n\nResults: {json.dumps(results, indent=2)}"
        table = ChatService.execute_sql(session, sql)

        chat_message = ChatMessage.objects.create(
            session=session,
            query=query,
            response=response,
            sql=sql,
            llm=llm,
            table=table,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
        )
        return chat_message
