import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date, timedelta
from uuid import uuid4


def _send(smtp_config: dict, msg: MIMEMultipart) -> None:
    """Send a MIMEMultipart message via SMTP. Raises on failure."""
    port = int(smtp_config["port"])
    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_config["server"], port, context=context, timeout=15) as server:
            server.login(smtp_config["username"], smtp_config["password"])
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_config["server"], port, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_config["username"], smtp_config["password"])
            server.send_message(msg)


def generate_ics(guest_name: str, check_in: str, check_out: str) -> str:
    """Generate an .ics calendar file for the visit as an all-day event."""
    ci = date.fromisoformat(check_in)
    co = date.fromisoformat(check_out)
    # DTEND for all-day VEVENT is exclusive (day after last night)
    co_exclusive = (co + timedelta(days=1)).strftime("%Y%m%d")
    ci_str = ci.strftime("%Y%m%d")
    uid = str(uuid4())

    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//HouseVisitScheduler//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTART;VALUE=DATE:{ci_str}\r\n"
        f"DTEND;VALUE=DATE:{co_exclusive}\r\n"
        f"SUMMARY:House Visit - {guest_name}\r\n"
        f"DESCRIPTION:Your stay from {check_in} to {check_out} has been confirmed.\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def send_acceptance_email(
    smtp_config: dict,
    guest_name: str,
    guest_email: str,
    check_in: str,
    check_out: str,
) -> None:
    """Send an acceptance email with an .ics calendar attachment.

    smtp_config keys: server, port, username, password, from_address
    Raises on failure so the caller can display the error.
    """
    ci = date.fromisoformat(check_in)
    co = date.fromisoformat(check_out)
    nights = max((co - ci).days, 1)

    msg = MIMEMultipart("mixed")
    msg["From"] = smtp_config["from_address"]
    msg["To"] = guest_email
    msg["Subject"] = f"Your visit is confirmed! ({check_in} to {check_out})"

    body = (
        f"Hi {guest_name},\n\n"
        f"Great news — your stay has been confirmed!\n\n"
        f"  Check-in:  {check_in}\n"
        f"  Check-out: {check_out}\n"
        f"  Nights:    {nights}\n\n"
        f"A calendar invite is attached. Add it to your calendar so you don't forget!\n\n"
        f"See you soon!"
    )
    msg.attach(MIMEText(body, "plain"))

    # Attach .ics
    ics_content = generate_ics(guest_name, check_in, check_out)
    ics_part = MIMEBase("text", "calendar", method="PUBLISH")
    ics_part.set_payload(ics_content.encode("utf-8"))
    encoders.encode_base64(ics_part)
    ics_part.add_header("Content-Disposition", "attachment", filename="visit.ics")
    msg.attach(ics_part)

    _send(smtp_config, msg)


def send_submission_confirmation(
    smtp_config: dict,
    guest_name: str,
    guest_email: str,
    check_in: str,
    check_out: str,
) -> None:
    """Send a confirmation email when a guest submits a visit request.

    No ICS attachment — the visit is not yet approved.
    Raises on failure.
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = smtp_config["from_address"]
    msg["To"] = guest_email
    msg["Subject"] = f"We received your visit request ({check_in} to {check_out})"

    body = (
        f"Hi {guest_name},\n\n"
        f"Your visit request has been received!\n\n"
        f"  Requested dates: {check_in} to {check_out}\n\n"
        f"The host will review your request and you will receive another email "
        f"once a decision has been made.\n\n"
        f"Thank you!"
    )
    msg.attach(MIMEText(body, "plain"))
    _send(smtp_config, msg)


def send_rejection_email(
    smtp_config: dict,
    guest_name: str,
    guest_email: str,
    check_in: str,
    check_out: str,
    admin_notes: str = "",
) -> None:
    """Send a notification email when a visit request is rejected.

    Raises on failure.
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = smtp_config["from_address"]
    msg["To"] = guest_email
    msg["Subject"] = f"Update on your visit request ({check_in} to {check_out})"

    body = (
        f"Hi {guest_name},\n\n"
        f"Unfortunately, your visit request for {check_in} to {check_out} "
        f"could not be accommodated at this time.\n\n"
    )
    if admin_notes:
        body += f"Note from host: {admin_notes}\n\n"
    body += "Feel free to request different dates.\n\nBest regards"
    msg.attach(MIMEText(body, "plain"))
    _send(smtp_config, msg)


def test_smtp_connection(smtp_config: dict) -> None:
    """Test SMTP connectivity without sending an email. Raises on failure."""
    port = int(smtp_config["port"])
    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_config["server"], port, context=context, timeout=10) as server:
            server.login(smtp_config["username"], smtp_config["password"])
    else:
        with smtplib.SMTP(smtp_config["server"], port, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_config["username"], smtp_config["password"])
