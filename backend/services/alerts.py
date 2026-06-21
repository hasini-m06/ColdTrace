"""
services/alerts.py
------------------
Email/SMS alert delivery for ColdTrace.

send_email_alert(subject, body):
    Previously sent to a static config.yaml email_recipients list.
    NOW queries verified subscribers from the users/alert_preferences DB
    tables and sends to each matching recipient individually.
    SMS is still sent to the static sms_recipients list (not account-linked yet).

send_email_to(address, subject, body):
    Auth-flow emails (verification, password reset). Always sends to one address.
"""

import smtplib
from email.message import EmailMessage
import requests
from core.config import settings, GMAIL_USER, GMAIL_APP_PASSWORD


# ---------------------------------------------------------------------------
# Low-level SMTP helper (shared by both send_email_alert and send_email_to)
# ---------------------------------------------------------------------------
def _smtp_send(to_address: str, subject: str, body: str) -> bool:
    """
    Open one SMTP_SSL connection and send a single message.
    Returns True on success, False on failure.
    """
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("\n" + "="*80)
        print(" [DEVELOPMENT FALLBACK] SMTP Credentials not configured.")
        print(f" To: {to_address}")
        print(f" Subject: {subject}")
        print(f" Body:\n{body}")
        print("="*80 + "\n")
        return True
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From']    = GMAIL_USER
        msg['To']      = to_address

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email to {to_address}: {e}")
        return False


# ---------------------------------------------------------------------------
# Auth-flow emails (verification, password reset)
# ---------------------------------------------------------------------------
def send_email_to(to_address: str, subject: str, body: str):
    """
    Send a transactional auth email to a specific address.
    Used by routers/auth.py for account verification and password reset.
    """
    ok = _smtp_send(to_address, subject, body)
    if ok:
        print(f"Auth email sent to {to_address}: {subject}")


# ---------------------------------------------------------------------------
# Risk alert broadcast — now driven by DB subscriptions
# ---------------------------------------------------------------------------
def send_email_alert(subject: str, body: str, location_id: int = None):
    """
    Send a risk alert email to all verified subscribers for this location.

    Recipient query:
      SELECT u.email FROM users u
      JOIN alert_preferences ap ON ap.user_id = u.id
      WHERE u.is_verified = 1
        AND (ap.location_id = <location_id> OR ap.location_id IS NULL)

    If location_id is None (legacy call), falls back to all subscribers
    who have location_id IS NULL (i.e., "subscribe to everything" users).
    """
    from database.db import fetch_all

    if location_id is not None:
        recipients = fetch_all(
            """SELECT DISTINCT u.email FROM users u
               JOIN alert_preferences ap ON ap.user_id = u.id
               WHERE u.is_verified = 1
                 AND (ap.location_id = ? OR ap.location_id IS NULL)""",
            (location_id,)
        )
    else:
        # Legacy path: send to anyone who subscribed to all locations
        recipients = fetch_all(
            """SELECT DISTINCT u.email FROM users u
               JOIN alert_preferences ap ON ap.user_id = u.id
               WHERE u.is_verified = 1 AND ap.location_id IS NULL"""
        )

    if not recipients:
        print(f"[alerts] No verified subscribers for location_id={location_id} — skipping email.")
        return

    sent, failed = 0, 0
    for row in recipients:
        if _smtp_send(row['email'], subject, body):
            sent += 1
        else:
            failed += 1

    print(f"[alerts] Alert '{subject}' — sent to {sent} subscriber(s), {failed} failed.")


# ---------------------------------------------------------------------------
# SMS alert (still static, not account-linked in this version)
# ---------------------------------------------------------------------------
def send_sms_alert(message: str):
    for recipient in settings.alerts.sms_recipients:
        try:
            resp = requests.post('https://textbelt.com/text', {
                'phone': recipient,
                'message': message,
                'key': 'textbelt',
            })
            print(f"Textbelt SMS to {recipient}: {resp.json()}")
        except Exception as e:
            print(f"Failed to send SMS to {recipient}: {e}")


# ---------------------------------------------------------------------------
# Trigger — called from tasks/scheduler.py when score crosses threshold
# ---------------------------------------------------------------------------
def trigger_alerts(location_id: int, location_name: str, district: str,
                   score: float, top_features: list):
    subject = f"CRITICAL: Cold Chain Breach Predicted at {location_name} ({district})"
    body = (
        f"Alert: Risk Score {score:.1f} at {location_name}, District: {district}\n"
        f"Top contributing factors:\n"
    )
    for feat in top_features:
        body += f"- {feat}\n"
    body += "\nRecommended Action: Pre-position backup stock, arrange generator fuel, escalate to district manager."

    # Pass location_id so only relevant subscribers are notified
    send_email_alert(subject, body, location_id=location_id)

    sms_body = f"ColdTrace ALERT: {location_name} risk {score:.1f}. Check dashboard."
    send_sms_alert(sms_body)

    from database.db import execute_query
    execute_query(
        "INSERT INTO alerts (location_id, score, message) VALUES (?, ?, ?)",
        (location_id, score, sms_body)
    )
