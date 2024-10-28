import streamlit as st
from premsql.playground.frontend.components.chat import ChatComponent 
from premsql.playground.frontend.components.session import SessionComponent
from premsql.playground.frontend.components.uploader import UploadComponent

st.set_page_config(page_title="PremSQL Playground", page_icon="🔍", layout="wide")

def render_main_view():
    session_component = SessionComponent()
    
    selected_session = session_component.render_list_sessions()
    session_creation = session_component.render_register_session()
    session_component.render_additional_links()

    if session_creation is not None:
        if session_creation.status_code == 200:
            new_session_name = session_creation.session_name 
            st.success(f"New session created: {new_session_name}")
            ChatComponent().render_chat_env(session_name=new_session_name)
    elif selected_session is not None:
        ChatComponent().render_chat_env(session_name=selected_session)
    
    session_component.render_delete_session_view()

def main():
    _, col2, _ = st.sidebar.columns([1, 2, 1])
    with col2:
        st.image(
            "https://static.premai.io/logo.svg",
            use_column_width=True,
            width=150,
            clamp=True,
        )
        st.header("PremSQL Playground")
    st.title("PremSQL Playground")
    
    # Add navigation
    selected_page = st.sidebar.selectbox("Navigation", ["Chat", "Upload csvs or use Kaggle"])
    
    if selected_page == "Chat":
        st.write("Welcome to the PremSQL Playground. Select or create a session to get started.")
        render_main_view()
    else:
        st.write(
            "You can either upload multiple csv files or enter a valid Kaggle ID. "
            "This will migrate all the csvs into a SQLite Database. You can then "
            "use them for natural language powered analysis using PremSQL."
        )
        UploadComponent.render_kaggle_view()
        UploadComponent.render_csv_upload_view()

if __name__ == "__main__":
    main()