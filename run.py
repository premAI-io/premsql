from operate import ServerManager

manager = ServerManager()

if manager.is_running(8500):
    print("running")
    manager.stop(8500)

# manager.start(
#     dsn_or_db_path="sqlite:////Users/anindya/personal/PremSQL/premsql/dataset/spider/database/coffee_shop/coffee_shop.sqlite",
#     agent_name="simple_agent"
# )

# from premsql.playground.api_client import APIClient
# from premsql.playground.constants import BASE_URL, CSRF_TOKEN

# client = APIClient(
#     base_url=BASE_URL, csrf_token=CSRF_TOKEN
# )
# db_uri = "sqlite:////Users/anindya/personal/PremSQL/premsql/dataset/spider/database/coffee_shop/coffee_shop.sqlite"

# response = client.create_session(
#     session_data=dict(
#         session_name="agent3_session",
#         agent_name="simple_agent",
#         db_connection_uri=db_uri,
#         db_type="sqlite"
#     )
# )

# print(response)


from openai import OpenAI
import streamlit as st

st.title("ChatGPT-like clone")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})