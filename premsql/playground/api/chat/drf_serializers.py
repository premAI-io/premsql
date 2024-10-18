from rest_framework import serializers


# Sessions
class SessionCreationRequestSerializer(serializers.Serializer):
    session_name = serializers.CharField(max_length=255)
    agent_name = serializers.CharField(max_length=255, default="simple_agent")

    db_type = serializers.CharField(max_length=255, default="sqlite")
    db_connection_uri = serializers.CharField(max_length=255)

    include = serializers.CharField(
        default="", allow_null=True, allow_blank=True, min_length=0
    )
    exclude = serializers.CharField(
        default="", allow_null=True, allow_blank=True, min_length=0
    )

    config_path = serializers.CharField(allow_null=True, allow_blank=True, default="")
    env_path = serializers.CharField(allow_null=True, allow_blank=True, default="")


class SessionCreationResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["success", "error"])
    status_code = serializers.ChoiceField(choices=[200, 500])
    session_id = serializers.IntegerField()
    session_name = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


class SessionDeletionRequestSerializer(serializers.Serializer):
    session_name = serializers.CharField()


class SessionDeletionResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["success", "error"])
    status_code = serializers.ChoiceField(choices=[200, 500])
    session_id = serializers.IntegerField()
    session_name = serializers.CharField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


class SessionUpdateRequestSerializer(serializers.Serializer):
    session_name = serializers.CharField(max_length=255)
    agent_name = serializers.CharField(max_length=255, default="simple_agent")

    db_type = serializers.CharField(max_length=255, default="sqlite")
    db_connection_uri = serializers.CharField(max_length=255)

    include = serializers.CharField(
        default="", allow_null=True, allow_blank=True, min_length=0
    )
    exclude = serializers.CharField(
        default="", allow_null=True, allow_blank=True, min_length=0
    )

    config_path = serializers.CharField(allow_null=True, allow_blank=True)
    env_path = serializers.CharField(allow_null=True, allow_blank=True)


class SessionUpdateResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["success", "error"])
    status_code = serializers.ChoiceField(choices=[200, 500])
    session_id = serializers.IntegerField()
    session_name = serializers.CharField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


class SessionSummarySerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    session_name = serializers.CharField(max_length=255)
    created_at = serializers.DateTimeField()
    engine = serializers.CharField(max_length=255)
    db_type = serializers.CharField(max_length=255)


class SessionListResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["success", "error"])
    status_code = serializers.ChoiceField(choices=[200, 500])
    message = serializers.CharField()
    data = SessionSummarySerializer(many=True, allow_null=True)
    total_count = serializers.IntegerField(allow_null=True)
    page = serializers.IntegerField(allow_null=True)
    page_size = serializers.IntegerField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


# Chats
class ChatMessageCreationRequestSerializer(serializers.Serializer):
    session_name = serializers.CharField()
    query = serializers.CharField()
    additional_knowledge = serializers.CharField(allow_null=True, default=None)
    few_shot_examples = serializers.JSONField(allow_null=True, default=None)


class ChatMessageCreationResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["success", "error"])
    status_code = serializers.ChoiceField(choices=[200, 500])
    message_id = serializers.IntegerField(allow_null=True)
    session_name = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField(allow_null=True)
    query = serializers.CharField(allow_null=True)
    additional_knowledge = serializers.CharField(allow_null=True)
    few_shot_examples = serializers.JSONField(allow_null=True)
    sql_string = serializers.CharField(allow_null=True)
    bot_message = serializers.CharField(allow_null=True)
    dataframe = serializers.JSONField(allow_null=True)
    plot_image = serializers.CharField(allow_null=True)
    plot_dataframe = serializers.JSONField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


class ChatMessageSummarySerializer(serializers.Serializer):
    message_id = serializers.IntegerField()
    session_name = serializers.CharField()
    created_at = serializers.DateTimeField()
    query = serializers.CharField()
    bot_message = serializers.CharField(allow_null=True)
    sql_string = serializers.CharField(allow_null=True)
    dataframe = serializers.JSONField(allow_null=True)
    plot_image = serializers.CharField(allow_null=True)
    plot_dataframe = serializers.JSONField(allow_null=True)


class ChatMessageListResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["success", "error"])
    status_code = serializers.ChoiceField(choices=[200, 500])
    data = ChatMessageSummarySerializer(many=True, allow_null=True)
    total_count = serializers.IntegerField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)


class ChatMessageListRequestSerializer(serializers.Serializer):
    session_name = serializers.CharField(allow_null=True)
    start_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)
    page = serializers.IntegerField(default=1)
    page_size = serializers.IntegerField(default=20)
