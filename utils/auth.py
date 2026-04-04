import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from flask import session, redirect, url_for, flash

# Admin configuration explicitly decoupling arrays from raw code directly onto safe scalable Environmental blocks
def get_admins():
    """
    Returns the list of admin emails from the ENV variable.
    """
    raw_admins = os.getenv("ADMIN_EMAILS", "rk844304@gmail.com,raj05062005@gmail.com")
    return [email.strip().lower() for email in raw_admins.split(",") if email.strip()]

def get_user_role(email, db):
    """
    Determines user role based on email lookup.
    """
    email = email.lower()
    if email in get_admins():
        return "admin"
    if db.teachers.find_one({"email": email}):
        return "teacher"
    if db.students.find_one({"email": email}):
        return "student"
    return None

def send_otp_email(user_email, otp):
    """
    Sends 6-digit OTP using Gmail SMTP with strict TLS/SSL support.
    """
    mail_user = os.getenv("MAIL_USER")
    mail_pass = os.getenv("MAIL_PASS")

    # Deep clean formatting incase the App Password was copied with whitespace spaces
    if mail_pass:
        mail_pass = mail_pass.replace(" ", "").strip()
        
    if not mail_user or not mail_pass:
        print(f"========== DEBUG OTP: {otp} for {user_email} ==========")
        return True, "MAIL_PASS not configured"

    try:
        msg = MIMEMultipart()
        msg['From'] = mail_user
        msg['To'] = user_email
        msg['Subject'] = "Attendance System Login OTP"

        body = f"Your one-time password (OTP) is: {otp}\nIt is valid for 5 minutes."
        msg.attach(MIMEText(body, 'plain'))

        # Modern Gmail SMTP Port 587 with STARTTLS (Very stable for Railway/Cloud)
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.starttls()
        server.login(mail_user, mail_pass)
        server.send_message(msg)
        server.quit()
        return True, "Success"
    except Exception as e:
        print(f"FAILED TO SEND EMAIL: {e}")
        # Always print for logs in case of failure
        print(f"========== DEBUG OTP (Send Failure): {otp} for {user_email} ==========")
        return False, str(e)

# Flask Middleware Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Log in required to access this portal.", "info")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                flash("Log in required to access this portal.", "info")
                return redirect(url_for('auth.login'))
            if session.get("role") != role:
                flash(f"Access Denied. You require {role.capitalize()} privileges.", "error")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
