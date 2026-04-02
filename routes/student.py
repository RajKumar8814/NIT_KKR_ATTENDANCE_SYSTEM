from flask import Blueprint, render_template, session, redirect, url_for, flash
from utils.auth import role_required
from utils.db import get_db
import math

student_bp = Blueprint("student", __name__)

@student_bp.before_request
@role_required('student')
def check_student():
    pass

@student_bp.route("/dashboard")
def dashboard():
    db = get_db()
    email = session.get("user")
    student = db.students.find_one({"email": email}, {"roll_no": 1, "class_id": 1, "name": 1})
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for("auth.login"))
        
    roll_no = student["roll_no"]
    class_id = student.get("class_id")
    
    # Get subjects for the student's class
    cls_info = db.classes.find_one({"_id": class_id})
    subjects = cls_info.get("subjects", []) if cls_info else []
    
    stats = []
    overall_present = 0
    overall_total = 0
    
    for subj in subjects:
        subj_id = subj["subject_id"]
        total_lec = subj.get("total_lectures", 0)
        
        # Count how many times this roll_no appears in present list for this subject
        present_count = db.attendance.count_documents({
            "class_id": class_id,
            "subject_id": subj_id,
            "present_roll_nos": {"$in": [roll_no]}
        })
        
        att_percentage = (present_count / total_lec * 100) if total_lec > 0 else 0
        
        if att_percentage < 75:
            classes_needed = math.ceil((0.75 * total_lec - present_count) / 0.25)
            goal_msg = f"Attend {classes_needed} more consecutive classes"
        else:
            goal_msg = "Goal Achieved."
            
        stats.append({
            "subject_name": subj["name"],
            "present": present_count,
            "total": total_lec,
            "percentage": att_percentage,
            "msg": goal_msg
        })
        
        overall_present += present_count
        overall_total += total_lec

    overall_percentage = (overall_present / overall_total * 100) if overall_total > 0 else 0
    
    return render_template("student/dashboard.html", student=student, stats=stats, overall_percentage=overall_percentage)

@student_bp.route("/history")
def history():
    db = get_db()
    student = db.students.find_one({"email": session.get("user")})
    roll_no = student["roll_no"]
    
    # Get all attendance records for this student's class
    logs = list(db.attendance.find({"class_id": student.get("class_id")}).sort("date", -1))
    
    history_logs = []
    cls_info = db.classes.find_one({"_id": student.get("class_id")})

    for log in logs:
        subj_name = "Unknown"
        if cls_info:
            subj_info = next((s for s in cls_info.get("subjects", []) if s["subject_id"] == log["subject_id"]), None)
            if subj_info:
                subj_name = subj_info["name"]
                
        status = "Present" if roll_no in log.get("present_roll_nos", []) else "Absent"
        history_logs.append({
            "date": log["date"],
            "subject_name": subj_name,
            "status": status
        })
        
    return render_template("student/history.html", history=history_logs)
