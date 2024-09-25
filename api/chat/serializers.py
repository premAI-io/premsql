from rest_framework import serializers

from .models import ChatMessage, Session, TableFilter


class SessionSerializer(serializers.ModelSerializer):
    tables_to_include = serializers.ListField(
        child=serializers.CharField(max_length=255), write_only=True, required=False
    )
    tables_to_exclude = serializers.ListField(
        child=serializers.CharField(max_length=255), write_only=True, required=False
    )

    class Meta:
        model = Session
        fields = [
            "name",
            "db_type",
            "llm",
            "db_connection_uri",
            "tables_to_include",
            "tables_to_exclude",
        ]

    def create(self, validated_data):
        tables_to_include = validated_data.pop("tables_to_include", [])
        tables_to_exclude = validated_data.pop("tables_to_exclude", [])
        session = Session.objects.create(**validated_data)

        for table in tables_to_include:
            TableFilter.objects.create(session=session, table_name=table, include=True)

        for table in tables_to_exclude:
            TableFilter.objects.create(session=session, table_name=table, include=False)

        return session


class ChatMessageSerializer(serializers.ModelSerializer):
    tables_to_include = serializers.ListField(
        child=serializers.CharField(max_length=255), write_only=True, required=False
    )
    tables_to_exclude = serializers.ListField(
        child=serializers.CharField(max_length=255), write_only=True, required=False
    )
    table = serializers.JSONField(read_only=True)
    sql = serializers.CharField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "session",
            "query",
            "response",
            "llm",
            "temperature",
            "max_new_tokens",
            "tables_to_include",
            "tables_to_exclude",
            "sql",
            "table",  # Ensure 'table' is listed here
        ]
        read_only_fields = ["id", "response", "sql", "created_at", "table"]

    def create(self, validated_data: dict):
        session = validated_data["session"]
        tables_to_include = validated_data.pop("tables_to_include", [])
        tables_to_exclude = validated_data.pop("tables_to_exclude", [])

        if tables_to_include is not None:
            # remove the existing filters from the session and add new filters
            TableFilter.objects.filter(session=session).delete()
            for table in tables_to_include:
                TableFilter.objects.create(
                    session=session, table_name=table, include=True
                )

        if tables_to_exclude is not None:
            # remove the existing filters from the session and add new filters
            TableFilter.objects.filter(session=session).delete()
            for table in tables_to_exclude:
                TableFilter.objects.create(
                    session=session, table_name=table, include=False
                )

        response = "Dummy response"
        table = {"dummy": "data"}
        sql = "SELECT * FROM dummy_table"
