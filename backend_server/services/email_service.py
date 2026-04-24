import smtplib
from email.mime.text import MIMEText

SMTP_EMAIL = "baohoang.tonthat.5@gmail.com"
SMTP_PASSWORD = "jrexgnkfkymcnwgc"


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())


def send_otp_email(to_email, otp_code):
    subject = "Delta One - Registration Code"
    body = (
        f"Welcome to Delta One!\n\n"
        f"Your registration code is: {otp_code}\n\n"
        f"Staff will NEVER ask for this code.\n"
        f"Do not disclose it to anyone."
    )
    send_email(to_email, subject, body)


def send_pin_reset_otp_email(to_email, otp_code):
    subject = "Delta One - PIN Reset Code"
    body = (
        "Hello,\n\n"
        f"Your PIN reset code is: {otp_code}\n\n"
        "This code will expire in 5 minutes.\n"
        "If you did not request this, please ignore this email."
    )
    send_email(to_email, subject, body)


def send_approved_email(to_email, full_name, department, role):
    subject = "Delta One - Account Approved"
    body = (
        f"Hello {full_name},\n\n"
        f"Your account has been approved successfully.\n\n"
        f"Department: {department}\n"
        f"Role: {role}\n\n"
        f"You can now log in to Delta One."
    )
    send_email(to_email, subject, body)
