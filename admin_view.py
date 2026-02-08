import streamlit as st
from datetime import date, timedelta
from streamlit_calendar import calendar as st_calendar
import database
import email_service


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
    st.title("House Visit Scheduler")
    st.subheader("Admin Dashboard")

    # --- Email feedback banner ---
    if "email_feedback" in st.session_state:
        kind, msg = st.session_state.pop("email_feedback")
        if kind == "success":
            st.success(msg)
        else:
            st.warning(msg)

    # --- Guest Link ---
    base_url = st.query_params.get("_base_url", "http://localhost:8501")
    guest_url = f"{base_url}/?role=guest"
    st.text_input(
        "Share this link with guests:",
        value=guest_url,
        disabled=True,
        key="guest_link",
    )
    st.info("Copy the link above and send it to your guests.")

    st.divider()

    # --- Calendar + Availability Management ---
    col_cal, col_list = st.columns([3, 2])

    with col_cal:
        st.markdown("### Calendar")
        st.caption(
            "Drag to select dates and add availability. "
            "Green = available, Orange = pending, Blue = accepted."
        )

        events = _build_calendar_events()
        calendar_options = {
            "editable": False,
            "selectable": True,
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "",
            },
            "height": 500,
        }
        cal_result = st_calendar(
            events=events, options=calendar_options, key="admin_cal"
        )

        # Handle date range selection
        if cal_result and cal_result.get("callback") == "select":
            sel = cal_result["select"]
            start = sel["start"][:10]
            # FullCalendar select end is exclusive, convert to inclusive
            end_inclusive = (
                date.fromisoformat(sel["end"][:10]) - timedelta(days=1)
            ).isoformat()
            st.session_state["pending_avail_start"] = start
            st.session_state["pending_avail_end"] = end_inclusive

        if "pending_avail_start" in st.session_state:
            p_start = st.session_state["pending_avail_start"]
            p_end = st.session_state["pending_avail_end"]
            st.info(f"Add availability: **{p_start}** to **{p_end}**?")
            btn_col1, btn_col2, _ = st.columns([1, 1, 3])
            with btn_col1:
                if st.button("Confirm", type="primary", key="confirm_avail"):
                    database.add_availability(p_start, p_end)
                    del st.session_state["pending_avail_start"]
                    del st.session_state["pending_avail_end"]
                    st.rerun()
            with btn_col2:
                if st.button("Cancel", key="cancel_avail"):
                    del st.session_state["pending_avail_start"]
                    del st.session_state["pending_avail_end"]
                    st.rerun()

    with col_list:
        st.markdown("### Available Dates")
        availability = database.get_all_availability()
        if not availability:
            st.caption("No availability set. Use the calendar to add dates.")
        for avail in availability:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{avail['start_date']}** to **{avail['end_date']}**")
            with col_b:
                if st.button("Remove", key=f"rm_avail_{avail['id']}"):
                    database.remove_availability(avail["id"])
                    st.rerun()

        # --- Manual Add (fallback if drag doesn't work) ---
        with st.expander("Add availability manually"):
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                manual_start = st.date_input(
                    "Start", value=date.today(), key="manual_start"
                )
            with m_col2:
                manual_end = st.date_input(
                    "End", value=date.today() + timedelta(days=7), key="manual_end"
                )
            if st.button("Add", key="manual_add"):
                if manual_end < manual_start:
                    st.error("End date must be on or after start date.")
                else:
                    database.add_availability(
                        manual_start.isoformat(), manual_end.isoformat()
                    )
                    st.rerun()

    st.divider()

    # --- Pending Requests ---
    st.markdown("### Pending Requests")
    pending = database.get_pending_requests()
    if not pending:
        st.caption("No pending requests.")
    for req in pending:
        with st.expander(
            f"{req['visitor_name']} -- {req['check_in_date']} to {req['check_out_date']}"
        ):
            st.markdown(f"**Email:** {req['visitor_email']}")
            st.markdown(
                f"**Dates:** {req['check_in_date']} to {req['check_out_date']}"
            )
            if req["notes"]:
                st.markdown(f"**Notes:** {req['notes']}")
            st.caption(f"Submitted: {req['created_at']}")

            admin_notes = st.text_input(
                "Admin notes (optional)",
                key=f"admin_note_{req['id']}",
            )

            act_col1, act_col2, _ = st.columns([1, 1, 3])
            with act_col1:
                if st.button("Accept", type="primary", key=f"accept_{req['id']}"):
                    _accept_request(req, admin_notes)
            with act_col2:
                if st.button("Reject", key=f"reject_{req['id']}"):
                    database.update_request_status(
                        req["id"], "rejected", admin_notes=admin_notes
                    )
                    st.rerun()

    st.divider()

    # --- Request History ---
    with st.expander("View All Requests"):
        all_requests = database.get_all_requests()
        if not all_requests:
            st.caption("No requests yet.")
        else:
            for req in all_requests:
                status_icon = {
                    "pending": "🟠",
                    "accepted": "🟢",
                    "rejected": "🔴",
                }.get(req["status"], "⚪")
                st.markdown(
                    f"{status_icon} **{req['visitor_name']}** — "
                    f"{req['check_in_date']} to {req['check_out_date']} — "
                    f"*{req['status']}*"
                )
                if req["admin_notes"]:
                    st.caption(f"Admin note: {req['admin_notes']}")



    # --- Email Settings ---
    _render_smtp_settings()


def _render_smtp_settings():
    """Render the SMTP configuration expander."""
    with st.expander("Email Settings (SMTP)"):
        st.caption("Configure SMTP to auto-send confirmation emails with calendar invites when you accept a request.")
        existing = database.get_smtp_config() or {}
        server = st.text_input("SMTP Server", value=existing.get("server", ""), key="smtp_server")
        port = st.text_input("Port", value=existing.get("port", "587"), key="smtp_port")
        username = st.text_input("Username", value=existing.get("username", ""), key="smtp_username")
        password = st.text_input("Password", value=existing.get("password", ""), type="password", key="smtp_password")
        from_addr = st.text_input("From Address", value=existing.get("from_address", ""), key="smtp_from")

        btn_col1, btn_col2, _ = st.columns([1, 1, 3])
        with btn_col1:
            if st.button("Save", key="smtp_save"):
                database.save_smtp_config(server, port, username, password, from_addr)
                st.success("SMTP settings saved.")
        with btn_col2:
            if st.button("Test Connection", key="smtp_test"):
                cfg = database.get_smtp_config()
                if not cfg:
                    st.error("Please save SMTP settings first.")
                else:
                    try:
                        email_service.test_smtp_connection(cfg)
                        st.success("Connection successful!")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")


def _accept_request(req: dict, admin_notes: str):
    """Accept a visit request and attempt to send confirmation email."""
    if database.has_overlap_conflict(req["check_in_date"], req["check_out_date"]):
        st.error("Cannot accept: these dates overlap with another accepted booking.")
        return

    database.update_request_status(req["id"], "accepted", admin_notes=admin_notes)

    # Attempt to send confirmation email
    smtp_cfg = database.get_smtp_config()
    if smtp_cfg:
        try:
            email_service.send_confirmation_email(
                smtp_cfg,
                req["visitor_name"],
                req["visitor_email"],
                req["check_in_date"],
                req["check_out_date"],
            )
            st.session_state["email_feedback"] = (
                "success",
                f"Request accepted and confirmation email sent to {req['visitor_email']}.",
            )
        except Exception as e:
            st.session_state["email_feedback"] = (
                "warning",
                f"Request accepted but email failed: {e}",
            )
    else:
        st.session_state["email_feedback"] = (
            "success",
            "Request accepted. (No SMTP configured — no email sent.)",
        )

    st.rerun()
