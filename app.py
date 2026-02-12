import streamlit as st
import database

st.set_page_config(
    page_title="House Visit Scheduler",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    database.init_db()
    admin_key = database.get_or_create_admin_key()

    # Print admin URL to server console on startup
    print(f"\n{'='*60}")
    print(f"  Admin URL: http://localhost:8501/?role=admin&key={admin_key}")
    print(f"  Guest URL: http://localhost:8501/?role=guest")
    print(f"{'='*60}\n")

    params = st.query_params
    role = params.get("role", "")
    key = params.get("key", "")

    if role == "admin":
        if key == admin_key:
            import admin_view
            admin_view.render()
        else:
            st.error("Invalid admin key. Access denied.")
            st.stop()
    else:
        # Default: show guest view directly (like Calendly's shareable link)
        import guest_view
        guest_view.render()


if __name__ == "__main__":
    main()
