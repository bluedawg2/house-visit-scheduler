import streamlit as st
from datetime import date, timedelta
from streamlit_calendar import calendar as st_calendar
import database


def _build_calendar_events():
    """Build event list for the visitor's read-only calendar."""
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
    st.title("House Visit Scheduler")
    st.subheader("Book Your Visit")

    st.markdown(
        "Green dates are **available**. Gray dates are already **booked**. "
        "Choose your dates below and submit a request."
    )

    # --- Calendar ---
    events = _build_calendar_events()
    calendar_options = {
        "editable": False,
        "selectable": False,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next",
            "center": "title",
            "right": "today",
        },
        "height": 450,
    }
    st_calendar(events=events, options=calendar_options, key="visitor_cal")

    st.divider()

    # --- Request Form ---
    with st.form("visit_request_form", clear_on_submit=True):
        st.subheader("Request a Visit")

        name = st.text_input("Your Name *")
        email = st.text_input("Your Email *")

        col1, col2 = st.columns(2)
        with col1:
            check_in = st.date_input(
                "Check-in Date *",
                value=date.today() + timedelta(days=1),
                min_value=date.today(),
                max_value=date.today() + timedelta(days=365),
            )
        with col2:
            check_out = st.date_input(
                "Check-out Date *",
                value=date.today() + timedelta(days=2),
                min_value=date.today(),
                max_value=date.today() + timedelta(days=365),
            )

        notes = st.text_area(
            "Notes (optional)",
            placeholder="Number of guests, special requests, etc.",
        )

        submitted = st.form_submit_button("Submit Request", type="primary", use_container_width=True)

    if submitted:
        _handle_submission(name, email, check_in, check_out, notes)

    st.divider()

    # --- Status Lookup ---
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


def _handle_submission(name, email, check_in, check_out, notes):
    """Validate and create a visit request."""
    # Validation
    if not name.strip():
        st.error("Please enter your name.")
        return
    if not email.strip() or "@" not in email or "." not in email:
        st.error("Please enter a valid email address.")
        return
    if check_out < check_in:
        st.error("Check-out date must be on or after check-in date.")
        return

    check_in_str = check_in.isoformat()
    check_out_str = check_out.isoformat()

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
    st.success(
        "Your request has been submitted! "
        "You can check the status below using your email."
    )
