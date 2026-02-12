import streamlit as st
import database

st.set_page_config(
    page_title="House Visit Scheduler",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

database.init_db()

# Define pages
guest_page = st.Page("guest_view.py", title="Book a Visit", url_path="", default=True)
admin_page = st.Page("admin_view.py", title="Admin", url_path="admin")

# Hidden navigation -- guests see no sidebar, admin bookmarks /admin
pg = st.navigation([guest_page, admin_page], position="hidden")
pg.run()
