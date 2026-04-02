import random
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.auth import is_valid_domain, get_user_role, send_otp_email
from utils.db import get_db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        if not is_valid_domain(email):
            flash("Invalid domain. Must use @nitkkr.ac.in", "error")
            return redirect(url_for("auth.login"))

        db = get_db()
        role = get_user_role(email, db)
        if not role:
            flash("User not found in system or unauthorized.", "error")
            return redirect(url_for("auth.login"))

        otp = str(random.randint(100000, 999999))
        session["pending_email"] = email
        session["pending_otp"] = otp
        session["pending_role"] = role

        send_otp_email(email, otp)
        flash("OTP sent to your email (check console if MAIL_PASS is unset).", "info")
        return redirect(url_for("auth.verify_otp"))

    return render_template("login.html")

@auth_bp.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if "pending_email" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        user_otp = request.form.get("otp").strip()
        if user_otp == session.get("pending_otp"):
            # Success
            session["user"] = session.pop("pending_email")
            session["role"] = session.pop("pending_role")
            session.pop("pending_otp")
            flash("Login successful!", "success")

            if session["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            elif session["role"] == "teacher":
                return redirect(url_for("teacher.dashboard"))
            elif session["role"] == "student":
                return redirect(url_for("student.dashboard"))
        else:
            flash("Invalid OTP. Try again.", "error")

    return render_template("verify_otp.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
