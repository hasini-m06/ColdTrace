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
def _smtp_send(to_address: str, subject: str, body: str, html_body: str = None) -> bool:
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
        if html_body:
            print(f" HTML Body (first 300 chars):\n{html_body[:300]}...")
        print("="*80 + "\n")
        return True
    try:
        msg = EmailMessage()
        msg.set_content(body)
        if html_body:
            msg.add_alternative(html_body, subtype='html')
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


def send_alerts_digest(triggered_alerts: list):
    """
    Send a single summary email digest of all critical alerts triggered in this cycle.
    Also inserts alert records into the database.
    """
    import os
    from database.db import execute_query, fetch_all
    from datetime import datetime

    if not triggered_alerts:
        return

    # 1. Insert alert records into DB so the dashboard alert table is populated
    for alert in triggered_alerts:
        sms_body = f"ColdTrace ALERT: {alert['location_name']} risk {alert['score']:.1f}. Check dashboard."
        try:
            execute_query(
                "INSERT INTO alerts (location_id, score, message) VALUES (?, ?, ?)",
                (alert['location_id'], alert['score'], sms_body)
            )
        except Exception as e:
            print(f"Error saving alert to DB: {e}")

    # 2. Build plain text email body (fallback)
    subject = f"ColdTrace Digest: {len(triggered_alerts)} Critical Cold Chain Alerts"
    plain_body = f"ColdTrace has predicted potential cold chain breaches at {len(triggered_alerts)} facility/facilities:\n\n"
    
    for idx, alert in enumerate(triggered_alerts, 1):
        ts = alert.get('timestamp') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        plain_body += f"{idx}. {alert['location_name']} ({alert['district']})\n"
        plain_body += f"   Timestamp: {ts}\n"
        plain_body += f"   Risk Score: {alert['score']:.1f}\n"
        plain_body += f"   Top Factors: {', '.join(alert['top_feats'])}\n\n"
        
    plain_body += "Recommended Action: Review these facilities on the Officials Dashboard and coordinate preventive maintenance."

    # 3. Build HTML tabular email body
    html_rows = ""
    for alert in triggered_alerts:
        ts = alert.get('timestamp') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Clean feature tags
        feat_tags = "".join(f"<span class='feature-tag'>{feat.replace('_', ' ')}</span>" for feat in alert['top_feats'])
        
        html_rows += f"""
        <tr>
          <td style="white-space: nowrap;">{ts}</td>
          <td><strong>{alert['location_name']}</strong></td>
          <td>{alert['district']}</td>
          <td><span class="badge-red">{alert['score']:.1f}</span></td>
          <td>{feat_tags}</td>
        </tr>
        """
        
    html_body = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #1e293b;
    background-color: #f8fafc;
    margin: 0;
    padding: 20px;
  }}
  .container {{
    max-width: 750px;
    background: #ffffff;
    border-radius: 8px;
    padding: 24px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
    margin: 0 auto;
    border-top: 4px solid #ef4444;
  }}
  h2 {{
    color: #ef4444;
    margin-top: 0;
    font-size: 20px;
  }}
  p {{
    font-size: 15px;
    line-height: 1.5;
    color: #475569;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 13px;
  }}
  th {{
    background-color: #0f172a;
    color: #ffffff;
    text-align: left;
    padding: 12px 10px;
    font-weight: 600;
  }}
  td {{
    padding: 12px 10px;
    border-bottom: 1px solid #e2e8f0;
    color: #334155;
  }}
  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}
  .badge-red {{
    background-color: #fee2e2;
    color: #ef4444;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
    border: 1px solid rgba(239, 68, 68, 0.2);
  }}
  .feature-tag {{
    background-color: #f1f5f9;
    color: #475569;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    margin-right: 4px;
    display: inline-block;
    border: 1px solid #e2e8f0;
  }}
  .footer {{
    font-size: 11px;
    color: #94a3b8;
    text-align: center;
    margin-top: 24px;
    border-top: 1px solid #e2e8f0;
    padding-top: 16px;
  }}
</style>
</head>
<body>
  <div class="container">
    <h2>ColdTrace Cold Chain Alerts Digest</h2>
    <p>ColdTrace has predicted potential cold chain breaches at <strong>{len(triggered_alerts)}</strong> facility/facilities during the latest run cycle:</p>
    
    <table>
      <thead>
        <tr>
          <th>Timestamp</th>
          <th>Facility</th>
          <th>District</th>
          <th>Risk Score</th>
          <th>Top Risk Factors</th>
        </tr>
      </thead>
      <tbody>
        {html_rows}
      </tbody>
    </table>
    
    <p><strong>Recommended Action:</strong> Pre-position backup stock, coordinate preventive maintenance, and escalate critical breaches to the district manager.</p>
    
    <div class="footer">
      This is an automated digest sent by the ColdTrace vaccine monitoring platform.
    </div>
  </div>
</body>
</html>
"""

    # 4. Find subscribers (send digest to all registered users automatically)
    # We will ALWAYS include GMAIL_USER if configured, so the primary operator gets the alert as requested.
    recipients = set()
    if GMAIL_USER:
        recipients.add(GMAIL_USER)

    try:
        # Automatically include all registered accounts in the email recipients list
        all_users = fetch_all("SELECT email FROM users")
        for row in all_users:
            recipients.add(row['email'])
    except Exception as e:
        print(f"Error fetching registered users from DB: {e}")

    # Also read any custom environment variable for static recipient list
    custom_emails = os.getenv("ALERT_RECIPIENT_EMAILS", "")
    if custom_emails:
        for email in custom_emails.split(","):
            email = email.strip()
            if email:
                recipients.add(email)

    if not recipients:
        print("[alerts] No verified subscribers or configured recipient emails — skipping email broadcast.")
        return

    sent = 0
    for email in recipients:
        if _smtp_send(email, subject, plain_body, html_body):
            sent += 1

    print(f"[alerts] Sent digest email to {sent} subscriber(s): {list(recipients)}")

    # 5. Send SMS (send 1 single digest alert to static list)
    sms_msg = f"ColdTrace Digest: {len(triggered_alerts)} facilities at risk. Check dashboard."
    send_sms_alert(sms_msg)

