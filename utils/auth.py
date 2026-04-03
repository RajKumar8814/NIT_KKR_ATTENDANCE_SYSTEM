import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from flask import session, redirect, url_for, flash

ADMIN_EMAILS = ["124102058@nitkkr.ac.in", "124102062@nitkkr.ac.in"]
DOMAIN = "@nitkkr.ac.in"

def is_valid_domain(email):
    return email.endswith(DOMAIN)

def get_user_role(email, db):
    if email in ADMIN_EMAILS:
        return "admin"
    admin_user = db.users.find_one({"email": email, "role": "admin"})
    if admin_user:
        return "admin"
    if db.teachers.find_one({"email": email}):
        return "teacher"
    if db.students.find_one({"email": email}):
        return "student"
    return None

def send_otp_email(user_email, otp):
    mail_user = os.getenv("MAIL_USER")
    mail_pass = os.getenv("MAIL_PASS")

    if not mail_user or not mail_pass:
        print(f"========== DEBUG OTP: {otp} for {user_email} ==========")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = mail_user
        msg['To'] = user_email
        msg['Subject'] = "Smart Attendance OTP Login"

        body = f"Your one-time password (OTP) is: {otp}\nIt is valid for 5 minutes."
        msg.attach(MIMEText(body, 'plain'))

        # Railway environments can sometimes hang on strict outbound SMTP limits
        # Setting a 10-second timeout completely prevents the Gunicorn worker from crashing (Internal Server Error)
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(mail_user, mail_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Even if sending fails, print it out so debugging is easy
        print(f"========== DEBUG OTP (Send Failed): {otp} for {user_email} ==========")
        return False

# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for('auth.login'))
            if session.get("role") != role:
                flash(f"Unauthorized. Requires {role} privileges.", "error")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
