import smtplib
from email.message import EmailMessage
import requests
import json
from core.config import settings, GMAIL_USER, GMAIL_APP_PASSWORD

def send_email_alert(subject: str, body: str):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("Gmail credentials not set, skipping email alert.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = ", ".join(settings.alerts.email_recipients)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email alert sent: {subject}")
    except Exception as e:
        print(f"Failed to send email: {e}")

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

def trigger_alerts(location_id: int, location_name: str, district: str, score: float, top_features: list):
    subject = f"CRITICAL: Cold Chain Breach Predicted at {location_name} ({district})"
    body = (
        f"Alert: Risk Score {score:.1f} at {location_name}, District: {district}\n"
        f"Top contributing factors:\n"
    )
    for feat in top_features:
        body += f"- {feat}\n"
        
    body += "\nRecommended Action: Pre-position backup stock, arrange generator fuel, escalate to district manager."
    
    send_email_alert(subject, body)
    
    sms_body = f"ColdTrace ALERT: {location_name} risk {score:.1f}. Check dashboard."
    send_sms_alert(sms_body)

    from database.db import execute_query
    execute_query("INSERT INTO alerts (location_id, score, message) VALUES (?, ?, ?)",
                  (location_id, score, sms_body))
