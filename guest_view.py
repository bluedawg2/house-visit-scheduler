import streamlit as st
from datetime import date, timedelta
from streamlit_calendar import calendar as st_calendar
import database
import email_service
import styles


def _get_gmail_config() -> dict | None:
    """Read Gmail credentials from st.secrets. Returns smtp config dict or None."""
    try:
        gmail = st.secrets["gmail"]
        address = gmail["address"]
        app_password = gmail["app_password"]
        if address and app_password:
            return {
                "server": "smtp.gmail.com",
                "port": "587",
                "username": address,
                "password": app_password,
                "from_address": address,
            }
    except (KeyError, FileNotFoundError):
        pass
    return None


def _build_available_only_events():
    """Build calendar events showing ONLY available date ranges (green backgrounds).

    Calendly principle: show only what's bookable. No booked/pending noise.
    """
    events = []
    availability = database.get_all_availability()
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
    return events


def render():
    styles.inject_guest_styles()

    st.session_state.setdefault("booking_step", 1)
    st.session_state.setdefault("guest_check_in", None)
    st.session_state.setdefault("guest_check_out", None)
    st.session_state.setdefault("guest_submission", None)

    step = st.session_state["booking_step"]

    st.markdown("### Book Your Visit")
    styles.render_step_indicator(step, ["Select Dates", "Your Details", "Confirmed"])

    if step == 1:
        _render_step_dates()
    elif step == 2:
        _render_step_form()
    elif step == 3:
        _render_step_confirmation()

    st.divider()
    _render_status_lookup()


def _render_step_dates():
    """Step 1: Date selection with read-only calendar + date pickers."""

    # Read-only calendar as visual reference
    events = _build_available_only_events()
    calendar_options = {
        "editable": False,
        "selectable": False,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next",
            "center": "title",
            "right": "today",
        },
        "height": 400,
    }
    st_calendar(events=events, options=calendar_options, key="guest_cal")
    st.caption("Green dates are available for booking.")

    # Date pickers -- the actual input mechanism
    col1, col2 = st.columns(2)
    with col1:
        check_in = st.date_input(
            "Check-in",
            value=st.session_state.get("guest_check_in"),
            min_value=date.today(),
            key="ci_input",
        )
    with col2:
        min_co = check_in + timedelta(days=1) if check_in else date.today() + timedelta(days=1)
        default_co = st.session_state.get("guest_check_out") or min_co
        # Ensure default_co is not before min_co
        if isinstance(default_co, str):
            default_co = date.fromisoformat(default_co)
        if default_co < min_co:
            default_co = min_co
        check_out = st.date_input(
            "Check-out",
            value=default_co,
            min_value=min_co,
            key="co_input",
        )

    # Inline validation
    valid = True
    if check_in and check_out:
        check_in_str = check_in.isoformat()
        check_out_str = check_out.isoformat()

        if check_out <= check_in:
            st.error("Check-out must be after check-in.")
            valid = False
        elif not database.is_range_within_availability(check_in_str, check_out_str):
            st.warning("These dates are not within an available window. Please choose green dates.")
            valid = False
        elif database.has_overlap_conflict(check_in_str, check_out_str):
            st.warning("These dates overlap with an existing booking. Please choose different dates.")
            valid = False
        else:
            nights = (check_out - check_in).days
            # Enforce min/max stay
            min_stay, max_stay = database.get_stay_limits()
            if min_stay and nights < min_stay:
                st.warning(f"Minimum stay is {min_stay} night{'s' if min_stay != 1 else ''}.")
                valid = False
            elif max_stay and nights > max_stay:
                st.warning(f"Maximum stay is {max_stay} night{'s' if max_stay != 1 else ''}.")
                valid = False
            else:
                st.success(f"{nights} night{'s' if nights != 1 else ''}")
    else:
        valid = False

    # Navigation
    if st.button(
        "Next: Your Details",
        type="primary",
        use_container_width=True,
        disabled=not valid,
    ):
        st.session_state["guest_check_in"] = check_in.isoformat()
        st.session_state["guest_check_out"] = check_out.isoformat()
        st.session_state["booking_step"] = 2
        st.rerun()


def _render_step_form():
    """Step 2: Guest details form."""
    check_in = st.session_state["guest_check_in"]
    check_out = st.session_state["guest_check_out"]

    if not check_in or not check_out:
        st.session_state["booking_step"] = 1
        st.rerun()
        return

    ci = date.fromisoformat(check_in)
    co = date.fromisoformat(check_out)
    nights = (co - ci).days

    # Date summary
    st.info(
        f"**Check-in:** {check_in}  |  **Check-out:** {check_out}  |  **{nights} night{'s' if nights != 1 else ''}**"
    )

    # Back button outside the form
    if st.button("Back to dates"):
        st.session_state["booking_step"] = 1
        st.rerun()

    # Booking form
    with st.form("booking_form", clear_on_submit=False):
        name = st.text_input("Your Name *")
        email = st.text_input("Your Email *")
        notes = st.text_area(
            "Anything we should know? (optional)",
            placeholder="Number of guests, arrival time, special requests, etc.",
        )
        submitted = st.form_submit_button(
            "Submit Request", type="primary", use_container_width=True
        )

    if submitted:
        _handle_submission(name, email, check_in, check_out, notes)


def _render_step_confirmation():
    """Step 3: Confirmation screen."""
    submission = st.session_state.get("guest_submission")
    if not submission:
        st.session_state["booking_step"] = 1
        st.rerun()
        return

    st.markdown("#### Your request has been submitted!")
    st.markdown(
        "The host will review your request and you will receive an email "
        "when it is accepted or declined."
    )

    # Details cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Check-in", submission["check_in"])
    with col2:
        st.metric("Check-out", submission["check_out"])
    with col3:
        st.metric("Nights", submission["nights"])

    st.markdown(f"**Guest:** {submission['name']}")
    if submission["notes"]:
        st.markdown(f"**Notes:** {submission['notes']}")

    if submission.get("email_sent"):
        st.success("A confirmation email has been sent to your inbox.")

    if st.button("Book another stay", type="primary"):
        st.session_state["booking_step"] = 1
        st.session_state["guest_submission"] = None
        st.session_state["guest_check_in"] = None
        st.session_state["guest_check_out"] = None
        st.rerun()


def _render_status_lookup():
    """Status lookup section -- visible, not hidden in an expander."""
    st.markdown("#### Check Your Request Status")
    lookup_email = st.text_input("Enter the email you used to book", key="lookup_email")
    if st.button("Look Up", key="lookup_btn"):
        if not lookup_email:
            st.warning("Please enter your email.")
        else:
            requests = database.get_requests_by_email(lookup_email.strip())
            if not requests:
                st.info("No requests found for this email.")
            else:
                for req in requests:
                    badge = styles.render_status_badge(req["status"])
                    st.markdown(
                        f"**{req['check_in_date']}** to **{req['check_out_date']}** -- "
                        f"{badge}",
                        unsafe_allow_html=True,
                    )
                    if req["admin_notes"]:
                        st.caption(f"Host note: {req['admin_notes']}")


def _handle_submission(name, email, check_in_str, check_out_str, notes):
    """Validate and create a visit request, then transition to confirmation."""
    if not name or not name.strip():
        st.error("Please enter your name.")
        return
    if not email or not email.strip() or "@" not in email or "." not in email:
        st.error("Please enter a valid email address.")
        return
    if not check_in_str or not check_out_str:
        st.error("Please select dates.")
        return
    if check_out_str < check_in_str:
        st.error("Check-out date must be after check-in date.")
        return

    if not database.is_range_within_availability(check_in_str, check_out_str):
        st.error(
            "The requested dates are not within an available window. "
            "Please go back and choose dates that fall within the green available ranges."
        )
        return

    if database.has_overlap_conflict(check_in_str, check_out_str):
        st.error(
            "These dates overlap with an existing confirmed booking. "
            "Please go back and choose different dates."
        )
        return

    database.create_visit_request(
        name.strip(), email.strip(), check_in_str, check_out_str, notes.strip()
    )

    ci = date.fromisoformat(check_in_str)
    co = date.fromisoformat(check_out_str)
    nights = max((co - ci).days, 1)

    # Send submission confirmation email to guest + notify admin
    email_sent = False
    smtp_cfg = _get_gmail_config()
    if smtp_cfg:
        try:
            # Confirm to guest
            email_service.send_submission_confirmation(
                smtp_cfg, name.strip(), email.strip(), check_in_str, check_out_str
            )
            email_sent = True
            # Notify admin
            admin_email = database.get_config("admin_email")
            if admin_email:
                email_service.send_admin_notification(
                    smtp_cfg, admin_email, name.strip(), email.strip(),
                    check_in_str, check_out_str, notes.strip()
                )
        except Exception:
            pass  # Fail silently -- guest sees on-screen confirmation

    st.session_state["guest_submission"] = {
        "name": name.strip(),
        "email": email.strip(),
        "check_in": check_in_str,
        "check_out": check_out_str,
        "nights": nights,
        "notes": notes.strip(),
        "email_sent": email_sent,
    }
    st.session_state["booking_step"] = 3
    st.session_state["guest_check_in"] = None
    st.session_state["guest_check_out"] = None
    st.rerun()


# Entry point when used as a st.Page file
render()
