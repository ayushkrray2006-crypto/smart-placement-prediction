"""Email helper.

Set SMTP_USER and SMTP_PASS (a Gmail App Password) in the terminal before starting
the backend to send real emails. Without them, emails are printed in the backend
terminal ("dev mode"), so everything still works for testing.
"""
import html as htmllib
import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "").replace(" ", "")
APP_NAME = "Smart Placement System"


def send_email(to, subject, body, html=None):
    if not (SMTP_USER and SMTP_PASS):
        print(f"\n===== DEV MODE: email not sent =====\nTo: {to}\nSubject: {subject}\n\n{body}\n"
              "====================================\n")
        return
    msg = EmailMessage()
    msg["From"] = f"{APP_NAME} <{SMTP_USER}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except Exception as exc:  # never crash the API because of email
        print("Email failed:", exc)


def otp_mail(to, name, code):
    send_email(to, f"{code} is your verification code",
               f"Hi {name},\n\nYour verification code is {code}.\n"
               "It expires in 10 minutes. If you did not create an account, ignore this email.\n\n"
               f"{APP_NAME}")


def welcome_mail(to, name):
    send_email(to, f"Welcome to {APP_NAME}",
               f"Hi {name},\n\nYour email is verified. Next steps:\n"
               "1. Complete your profile\n2. Enter your test scores\n"
               "3. Check your placement readiness and preparation plan\n\n"
               f"{APP_NAME}")


def company_alert(to, name, company):
    send_email(to, f"New opportunity: {company}",
               f"Hi {name},\n\n{company} has been added and you meet its eligibility criteria.\n"
               "Log in to review the details and prepare.\n\n"
               f"{APP_NAME}\n(You can turn off these emails in your profile.)")


def reminder_mail(to, name, recs):
    lines = "\n".join(f"- {r['skill']}: {r['advice']}" for r in recs)
    send_email(to, "Your placement preparation reminder",
               f"Hi {name},\n\nFocus on these areas this week:\n\n{lines}\n\n"
               f"Retake your tests after practising to update your readiness.\n\n{APP_NAME}")


def report_mail(to, name, sections):
    text = "\n\n".join(f"{title.upper()}\n" + "\n".join(f"- {x}" for x in items) for title, items in sections)
    body = "".join(
        f"<h3 style='color:#0f766e;margin:18px 0 6px'>{htmllib.escape(t)}</h3><ul style='margin:0;padding-left:18px'>"
        + "".join(f"<li>{htmllib.escape(str(x))}</li>" for x in items) + "</ul>" for t, items in sections)
    page = (f"<div style='font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#14211f'>"
            f"<h2>Placement readiness report</h2><p>Hi {htmllib.escape(name)}, here is your latest report.</p>{body}"
            f"<p style='color:#666;font-size:12px;margin-top:20px'>Predictions are estimates, not guarantees. {APP_NAME}</p></div>")
    send_email(to, "Your placement readiness report", f"Hi {name},\n\n{text}\n\n{APP_NAME}", page)
