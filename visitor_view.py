import streamlit as st
from datetime import date, timedelta
from streamlit_calendar import calendar as st_calendar
import database


def _build_calendar_events():
    """Build event list for the visitor calendar."""
    events = []
    availability = database.get_all_availability()
    accepted = database.get_accepted_requests()

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

    for req in accepted:
        end_exclusive = (
            date.fromisoformat(req["check_out_date"]) + timedelta(days=1)
        ).isoformat()
        events.append({
            "title": "Booked",
            "start": req["check_in_date"],
            "end": end_exclusive,
            "display": "background",
            "backgroundColor": "#9E9E9E",
        })

    return events


def render():
    st.session_state.setdefault("visitor_screen", "booking")
    st.session_state.setdefault("visitor_check_in", None)
    st.session_state.setdefault("visitor_check_out", None)
    st.session_state.setdefault("visitor_submission", None)

    if st.session_state["visitor_screen"] == "confirmation":
        _render_confirmation_screen()
    else:
        _render_booking_screen()


def _render_booking_screen():
    st.title("House Visit Scheduler")
    st.subheader("Book Your Visit")

    st.markdown(
        "Green = **available**. Gray = **booked**. Blue = **your selection**. "
        "Click a date to set check-in, then click another to set check-out."
    )

    # --- Selectable Calendar ---
    events = _build_calendar_events()

    # Add selected date range as a highlighted event
    check_in = st.session_state["visitor_check_in"]
    check_out = st.session_state["visitor_check_out"]
    if check_in:
        sel_end = check_out if check_out else check_in
        sel_end_exclusive = (
            date.fromisoformat(sel_end) + timedelta(days=1)
        ).isoformat()
        events.append({
            "title": "Your stay",
            "start": check_in,
            "end": sel_end_exclusive,
            "backgroundColor": "#1E88E5",
            "borderColor": "#1565C0",
            "textColor": "#FFFFFF",
        })

    calendar_options = {
        "editable": False,
        "selectable": True,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next",
            "center": "title",
            "right": "today",
        },
        "height": 450,
    }
    cal_result = st_calendar(events=events, options=calendar_options, key="visitor_cal")

    # Handle single-click (dateClick) — first click = check-in, second = check-out
    if cal_result and cal_result.get("callback") == "dateClick":
        clicked = cal_result["dateClick"]["date"][:10]
        if st.session_state["visitor_check_in"] is None:
            st.session_state["visitor_check_in"] = clicked
            st.session_state["visitor_check_out"] = None
        elif st.session_state["visitor_check_out"] is None:
            first = st.session_state["visitor_check_in"]
            if clicked < first:
                st.session_state["visitor_check_in"] = clicked
                st.session_state["visitor_check_out"] = first
            elif clicked == first:
                st.session_state["visitor_check_out"] = clicked
            else:
                st.session_state["visitor_check_out"] = clicked
        else:
            # Both already set — start over with new check-in
            st.session_state["visitor_check_in"] = clicked
            st.session_state["visitor_check_out"] = None

    # Handle click-and-drag (select) — sets both dates at once
    if cal_result and cal_result.get("callback") == "select":
        sel = cal_result["select"]
        start_str = sel["start"][:10]
        end_inclusive_str = (
            date.fromisoformat(sel["end"][:10]) - timedelta(days=1)
        ).isoformat()
        st.session_state["visitor_check_in"] = start_str
        st.session_state["visitor_check_out"] = end_inclusive_str

    st.divider()

    # --- Stay Summary ---
    check_in = st.session_state["visitor_check_in"]
    check_out = st.session_state["visitor_check_out"]

    if check_in and check_out:
        ci_date = date.fromisoformat(check_in)
        co_date = date.fromisoformat(check_out)
        nights = max((co_date - ci_date).days, 1)
        col_summary, col_clear = st.columns([5, 1])
        with col_summary:
            st.markdown(
                f"**Check-in:** {check_in} &nbsp;|&nbsp; "
                f"**Check-out:** {check_out} &nbsp;|&nbsp; "
                f"**{nights} night{'s' if nights != 1 else ''}**"
            )
        with col_clear:
            if st.button("Clear", key="clear_dates"):
                st.session_state["visitor_check_in"] = None
                st.session_state["visitor_check_out"] = None
                st.rerun()
    elif check_in:
        st.markdown(f"**Check-in:** {check_in} — now click your check-out date.")
    else:
        st.info("Click a date on the calendar above to set your check-in.")

    # --- Booking Form ---
    with st.form("visit_request_form", clear_on_submit=False):
        st.subheader("Your Details")
        name = st.text_input("Your Name *")
        email = st.text_input("Your Email *")
        notes = st.text_area(
            "Anything we should know?",
            placeholder="Number of guests, special requests, etc.",
        )
        submitted = st.form_submit_button(
            "Submit Request",
            type="primary",
            use_container_width=True,
            disabled=(check_in is None),
        )

    if submitted:
        _handle_submission(name, email, check_in, check_out, notes)

    st.divider()
    _render_status_lookup()


def _render_confirmation_screen():
    st.title("House Visit Scheduler")

    submission = st.session_state.get("visitor_submission")
    if not submission:
        st.session_state["visitor_screen"] = "booking"
        st.rerun()
        return

    st.success("Request sent!")
    st.markdown(
        "Your visit request has been submitted. "
        "The host will review it and you can check the status below."
    )

    st.markdown("---")
    st.markdown(f"**Guest:** {submission['name']}")
    st.markdown(f"**Check-in:** {submission['check_in']}")
    st.markdown(f"**Check-out:** {submission['check_out']}")
    st.markdown(f"**Nights:** {submission['nights']}")
    if submission["notes"]:
        st.markdown(f"**Message:** {submission['notes']}")
    st.markdown("---")

    if st.button("Book another stay", type="primary"):
        st.session_state["visitor_screen"] = "booking"
        st.session_state["visitor_submission"] = None
        st.rerun()

    st.divider()
    _render_status_lookup()


def _render_status_lookup():
    with st.expander("Check Your Request Status"):
        lookup_email = st.text_input("Enter your email", key="lookup_email")
        if st.button("Look Up", key="lookup_btn"):
            if not lookup_email:
                st.warning("Please enter your email.")
            else:
                requests = database.get_requests_by_email(lookup_email.strip())
                if not requests:
                    st.info("No requests found for this email.")
                else:
                    for req in requests:
                        status_color = {
                            "pending": ":orange[Pending]",
                            "accepted": ":green[Accepted]",
                            "rejected": ":red[Rejected]",
                        }.get(req["status"], req["status"])

                        st.markdown(
                            f"**{req['check_in_date']}** to **{req['check_out_date']}** — {status_color}"
                        )
                        if req["admin_notes"]:
                            st.caption(f"Admin note: {req['admin_notes']}")


def _handle_submission(name, email, check_in_str, check_out_str, notes):
    """Validate and create a visit request, then transition to confirmation."""
    if not name or not name.strip():
        st.error("Please enter your name.")
        return
    if not email or not email.strip() or "@" not in email or "." not in email:
        st.error("Please enter a valid email address.")
        return
    if not check_in_str or not check_out_str:
        st.error("Please select dates on the calendar.")
        return
    if check_out_str < check_in_str:
        st.error("Check-out date must be on or after check-in date.")
        return

    if not database.is_range_within_availability(check_in_str, check_out_str):
        st.error(
            "The requested dates are not within an available window. "
            "Please choose dates that fall within the green available ranges."
        )
        return

    if database.has_overlap_conflict(check_in_str, check_out_str):
        st.error(
            "These dates overlap with an existing confirmed booking. "
            "Please choose different dates."
        )
        return

    database.create_visit_request(
        name.strip(), email.strip(), check_in_str, check_out_str, notes.strip()
    )

    ci = date.fromisoformat(check_in_str)
    co = date.fromisoformat(check_out_str)
    nights = max((co - ci).days, 1)

    st.session_state["visitor_submission"] = {
        "name": name.strip(),
        "email": email.strip(),
        "check_in": check_in_str,
        "check_out": check_out_str,
        "nights": nights,
        "notes": notes.strip(),
    }
    st.session_state["visitor_screen"] = "confirmation"
    st.session_state["visitor_check_in"] = None
    st.session_state["visitor_check_out"] = None
    st.rerun()
