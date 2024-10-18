import random
import time

import streamlit as st
from components.chat import ChatComponent
from components.session import SessionComponent

from premsql.playground.constants import BASE_URL, CSRF_TOKEN

# Configure the page
st.set_page_config(page_title="PremSQL Playground", page_icon="🔍", layout="wide")


# Streamed response emulator
def response_generator():
    response = random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi, human! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )
    for word in response.split():
        yield word + " "
        time.sleep(0.05)


# Initialize session state for chat histories
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {
        "session with id": [
            {"role": "user", "content": "Hello, can you help me with SQL?"},
            {
                "role": "assistant",
                "content": "Of course! I'd be happy to help you with SQL. What specific question or topic do you have in mind?",
            },
            {"role": "user", "content": "How do I join two tables?"},
            {
                "role": "assistant",
                "content": "Joining two tables in SQL is a common operation. The basic syntax for an INNER JOIN is: SELECT * FROM table1 INNER JOIN table2 ON table1.column = table2.column. Would you like me to explain more about different types of joins?",
            },
            {"role": "user", "content": "I need to analyze my coffee shop sales data."},
            {
                "role": "assistant",
                "content": "Great! I can help you analyze your coffee shop sales data. What kind of information are you looking to extract from your data?",
            },
        ],
        "coffee shop analysis": [
            {"role": "user", "content": "I need to analyze my coffee shop sales data."},
            {
                "role": "assistant",
                "content": "Great! I can help you analyze your coffee shop sales data. What kind of information are you looking to extract from your data?",
            },
        ],
        "some session": [
            {"role": "user", "content": "How do I join two tables?"},
            {
                "role": "assistant",
                "content": "Joining two tables in SQL is a common operation. The basic syntax for an INNER JOIN is: SELECT * FROM table1 INNER JOIN table2 ON table1.column = table2.column. Would you like me to explain more about different types of joins?",
            },
        ],
        "test_session": [
            {"role": "user", "content": "How do I join two tables?"},
            {
                "role": "assistant",
                "content": "Joining two tables in SQL is a common operation. The basic syntax for an INNER JOIN is: SELECT * FROM table1 INNER JOIN table2 ON table1.column = table2.column. Would you like me to explain more about different types of joins?",
            },
            {"role": "user", "content": "I need to analyze my coffee shop sales data."},
            {
                "role": "assistant",
                "content": "Great! I can help you analyze your coffee shop sales data. What kind of information are you looking to extract from your data?",
            },
        ],
    }


def main():
    st.sidebar.image(
        "https://static.premai.io/logo.svg",
        use_column_width=False,
        width=150,
        clamp=True,
    )

    # Main content area
    st.title("PremSQL Playground")

    # Add your main content here
    st.write(
        "Welcome to the PremSQL Playground. Select or create a session to get started."
    )
    with st.expander(label="Add few shot examples"):
        st.text_area(label="Add few shot examples if any")

    session_component = SessionComponent(base_url=BASE_URL, csrf_token=CSRF_TOKEN)

    selected_session = session_component.render_list_sessions()
    session_creation = session_component.render_create_session()

    if session_creation is not None:
        if session_creation.get("status") == "success":
            new_session_name = session_creation.get("session_name")
            st.success(f"New session created: {new_session_name}")
            if new_session_name not in st.session_state.chat_histories:
                st.session_state.chat_histories[new_session_name] = []
            render_chat_view(new_session_name)
    elif selected_session is not None:
        render_chat_view(selected_session)


def render_chat_view(session_name):
    st.subheader(f"Chat Session: {session_name}")

    chat_component = ChatComponent(base_url=BASE_URL, csrf_token=CSRF_TOKEN)
    chat_component.render_chat_env(session_name)


if __name__ == "__main__":
    main()
