import streamlit as st
from datetime import date, timedelta
from streamlit_calendar import calendar as st_calendar
import database
import email_service
import styles


def _build_calendar_events():
    """Build event list for the admin calendar with availability and requests."""
    events = []
    availability = database.get_all_availability()
    all_requests = database.get_all_requests()

    for avail in availability:
        end_exclusive = (
            date.fromisoformat(avail["end_date"]) + timedelta(days=1)
        ).isoformat()
        events.append({
            "title": "Available",
            "start": avail["start_date"],
            "end": end_exclusive,
            "display": "background",
            "backgroundColor": "#4CAF50",
        })

    for req in all_requests:
        if req["status"] not in ("pending", "accepted"):
            continue
        end_exclusive = (
            date.fromisoformat(req["check_out_date"]) + timedelta(days=1)
        ).isoformat()
        color = "#FF9800" if req["status"] == "pending" else "#2196F3"
        events.append({
            "title": f"{req['visitor_name']} ({req['status']})",
            "start": req["check_in_date"],
            "end": end_exclusive,
            "backgroundColor": color,
            "borderColor": color,
        })

    return events


def render():
    styles.inject_admin_styles()

    st.title("House Visit Scheduler")
    st.caption("Admin Dashboard")

    # Email feedback banner
    if "email_feedback" in st.session_state:
        kind, msg = st.session_state.pop("email_feedback")
        if kind == "success":
            st.success(msg)
        elif kind == "error":
            st.error(msg)
        else:
            st.warning(msg)

    # Guest link -- prominent, with copy button
    _render_guest_link()

    st.divider()

    # Tabbed interface
    pending = database.get_pending_requests()
    pending_count = len(pending)
    tab_label = f"Requests ({pending_count})" if pending_count > 0 else "Requests"

    tab_requests, tab_availability, tab_history, tab_settings = st.tabs([
        tab_label,
        "Availability",
        "History",
        "Settings",
    ])

    with tab_requests:
        _render_requests_tab(pending)
    with tab_availability:
        _render_availability_tab()
    with tab_history:
        _render_history_tab()
    with tab_settings:
        _render_settings_tab()


def _render_guest_link():
    """Display the shareable guest booking link with a copy button."""
    st.markdown("**Share this link with your guests:**")
    st.caption(
        "Copy your app's root URL (e.g. `https://house-scheduler.streamlit.app`) "
        "and send it to guests. They'll see the booking page directly."
    )


def _render_requests_tab(pending):
    """Render pending requests as visible cards with accept/reject actions."""
    if not pending:
        st.info("No pending requests. You're all caught up!")
        return

    st.markdown(f"**{len(pending)} pending request{'s' if len(pending) != 1 else ''}**")

    for req in pending:
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"**{req['visitor_name']}**")
                st.markdown(f"{req['check_in_date']} to {req['check_out_date']}")
                st.caption(f"{req['visitor_email']}")
                if req["notes"]:
                    st.markdown(f"*\"{req['notes']}\"*")
                st.caption(f"Submitted {req['created_at']}")

            with col_actions:
                admin_notes = st.text_input(
                    "Note",
                    key=f"note_{req['id']}",
                    label_visibility="collapsed",
                    placeholder="Add a note...",
                )
                if st.button(
                    "Accept", type="primary", key=f"accept_{req['id']}",
                    use_container_width=True,
                ):
                    _accept_request(req, admin_notes)
                if st.button(
                    "Reject", key=f"reject_{req['id']}",
                    use_container_width=True,
                ):
                    _reject_request(req, admin_notes)


def _render_availability_tab():
    """Render availability management with date pickers as primary input."""
    col_add, col_cal = st.columns([2, 3])

    with col_add:
        st.markdown("#### Add Available Dates")
        start = st.date_input("From", value=date.today(), key="avail_start")
        end = st.date_input("To", value=date.today() + timedelta(days=7), key="avail_end")

        if st.button("Add Availability", type="primary", use_container_width=True):
            if end < start:
                st.error("End date must be on or after start date.")
            else:
                database.add_availability(start.isoformat(), end.isoformat())
                st.rerun()

        st.divider()
        st.markdown("#### Current Availability")
        availability = database.get_all_availability()
        if not availability:
            st.caption("No availability set yet.")
        for avail in availability:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"{avail['start_date']} to {avail['end_date']}")
            with col_b:
                if st.button("Remove", key=f"rm_{avail['id']}"):
                    database.remove_availability(avail["id"])
                    st.rerun()

    with col_cal:
        st.markdown("#### Calendar Overview")
        events = _build_calendar_events()
        calendar_options = {
            "editable": False,
            "selectable": False,
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "",
            },
            "height": 500,
        }
        st_calendar(events=events, options=calendar_options, key="admin_cal")
        st.caption("Green = available | Orange = pending | Blue = accepted")


def _render_history_tab():
    """Render request history with filters and search."""
    all_requests = database.get_all_requests()

    if not all_requests:
        st.info("No requests yet.")
        return

    # Filters
    col_status, col_search = st.columns(2)
    with col_status:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Pending", "Accepted", "Rejected"],
            key="history_status_filter",
        )
    with col_search:
        search = st.text_input("Search by name or email", key="history_search")

    # Apply filters
    filtered = all_requests
    if status_filter != "All":
        filtered = [r for r in filtered if r["status"] == status_filter.lower()]
    if search:
        q = search.lower()
        filtered = [
            r for r in filtered
            if q in r["visitor_name"].lower() or q in r["visitor_email"].lower()
        ]

    st.caption(f"Showing {len(filtered)} of {len(all_requests)} requests")

    for req in filtered:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{req['visitor_name']}** ({req['visitor_email']})")
            with col2:
                st.markdown(f"{req['check_in_date']} to {req['check_out_date']}")
            with col3:
                badge = styles.render_status_badge(req["status"])
                st.markdown(badge, unsafe_allow_html=True)
            if req["admin_notes"]:
                st.caption(f"Note: {req['admin_notes']}")


def _render_settings_tab():
    """Render SMTP configuration and booking rules."""

    # --- Gmail Integration ---
    st.markdown("#### Gmail Integration")
    st.caption(
        "Connect your Gmail account to send guests automatic emails "
        "when requests are submitted, accepted, or rejected. "
        "Accepted visits also get a Google Calendar invite."
    )

    existing = database.get_smtp_config() or {}

    # Status indicator
    if existing.get("username") and existing.get("password"):
        st.success(f"Connected to **{existing['username']}**")
    else:
        st.info("Not connected yet. Enter your Gmail details below.")

    gmail_address = st.text_input(
        "Gmail address",
        value=existing.get("username", ""),
        placeholder="you@gmail.com",
        key="gmail_address",
    )
    app_password = st.text_input(
        "App Password",
        value=existing.get("password", ""),
        type="password",
        key="gmail_app_password",
    )

    st.caption(
        "You need a Google App Password (not your regular password). "
        "To create one: [myaccount.google.com](https://myaccount.google.com) "
        "> Security > 2-Step Verification > App passwords."
    )

    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("Save", type="primary", key="smtp_save"):
            database.save_smtp_config(
                "smtp.gmail.com", "587", gmail_address, app_password, gmail_address
            )
            st.success("Gmail connected!")
            st.rerun()
    with col2:
        if st.button("Test Connection", key="smtp_test"):
            cfg = database.get_smtp_config()
            if not cfg:
                st.error("Please save your Gmail details first.")
            else:
                try:
                    email_service.test_smtp_connection(cfg)
                    st.success("Connection successful!")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

    st.divider()

    # --- Booking Rules Section ---
    st.markdown("#### Booking Rules")
    min_stay, max_stay = database.get_stay_limits()

    col_min, col_max = st.columns(2)
    with col_min:
        new_min = st.number_input(
            "Minimum nights",
            min_value=0,
            value=min_stay or 1,
            key="min_stay",
        )
    with col_max:
        new_max = st.number_input(
            "Maximum nights (0 = no limit)",
            min_value=0,
            value=max_stay or 0,
            key="max_stay",
        )
    if st.button("Save Rules", key="save_rules"):
        database.save_stay_limits(new_min, new_max)
        st.success("Booking rules saved.")


def _accept_request(req: dict, admin_notes: str):
    """Accept a visit request and send acceptance email."""
    if database.has_overlap_conflict(req["check_in_date"], req["check_out_date"]):
        st.error("Cannot accept: these dates overlap with another accepted booking.")
        return

    database.update_request_status(req["id"], "accepted", admin_notes=admin_notes)

    smtp_cfg = database.get_smtp_config()
    if smtp_cfg:
        try:
            email_service.send_acceptance_email(
                smtp_cfg,
                req["visitor_name"],
                req["visitor_email"],
                req["check_in_date"],
                req["check_out_date"],
            )
            st.session_state["email_feedback"] = (
                "success",
                f"Accepted! Confirmation email sent to {req['visitor_email']}.",
            )
        except Exception as e:
            st.session_state["email_feedback"] = (
                "warning",
                f"Accepted, but email failed: {e}",
            )
    else:
        st.session_state["email_feedback"] = (
            "success",
            "Accepted. (Gmail not configured -- no email sent.)",
        )
    st.rerun()


def _reject_request(req: dict, admin_notes: str):
    """Reject a visit request and send rejection email."""
    database.update_request_status(req["id"], "rejected", admin_notes=admin_notes)

    smtp_cfg = database.get_smtp_config()
    if smtp_cfg:
        try:
            email_service.send_rejection_email(
                smtp_cfg,
                req["visitor_name"],
                req["visitor_email"],
                req["check_in_date"],
                req["check_out_date"],
                admin_notes,
            )
            st.session_state["email_feedback"] = (
                "success",
                f"Rejected. Notification sent to {req['visitor_email']}.",
            )
        except Exception as e:
            st.session_state["email_feedback"] = (
                "warning",
                f"Rejected, but email failed: {e}",
            )
    else:
        st.session_state["email_feedback"] = (
            "success",
            "Rejected. (No email sent.)",
        )
    st.rerun()


# Entry point when used as a st.Page file
render()
