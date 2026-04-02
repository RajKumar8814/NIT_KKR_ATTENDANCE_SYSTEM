import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.auth import role_required
from utils.db import get_db
from utils.face import match_faces_in_group

teacher_bp = Blueprint("teacher", __name__)

@teacher_bp.before_request
@role_required('teacher')
def check_teacher():
    pass

@teacher_bp.route("/dashboard")
def dashboard():
    db = get_db()
    email = session.get("user")
    teacher = db.teachers.find_one({"email": email})
    
    # Load class info for these subjects
    assigned_subjects = []
    if teacher and "subjects" in teacher:
        for ds in teacher["subjects"]:
            cls_info = db.classes.find_one({"_id": ds["class_id"]})
            class_name = cls_info["name"] if cls_info else "Unknown Class"
            # Get total lectures for this subject in this class
            subj_info = next((s for s in cls_info.get("subjects", []) if s["subject_id"] == ds["subject_id"]), None)
            total_lec = subj_info.get("total_lectures", 0) if subj_info else 0
            
            assigned_subjects.append({
                "class_id": ds["class_id"],
                "subject_id": ds["subject_id"],
                "name": ds["name"],
                "class_name": class_name,
                "total_lectures": total_lec
            })
            
    return render_template("teacher/dashboard.html", teacher=teacher, subjects=assigned_subjects)

@teacher_bp.route("/update_lectures/<class_id>/<subject_id>", methods=["POST"])
def update_lectures(class_id, subject_id):
    db = get_db()
    action = request.form.get("action") # "add" or "cancel"
    amount = 1
    if action == "cancel":
        amount = -1
        
    db.classes.update_one(
        {"_id": class_id, "subjects.subject_id": subject_id},
        {"$inc": {"subjects.$.total_lectures": amount}}
    )
    flash(f"Total lectures updated successfully.", "success")
    return redirect(url_for("teacher.dashboard"))

@teacher_bp.route("/attendance", methods=["GET", "POST"])
def setup_attendance():
    db = get_db()
    email = session.get("user")
    teacher = db.teachers.find_one({"email": email})
    
    if request.method == "POST":
        class_id = request.form.get("class_id")
        subject_id = request.form.get("subject_id")
        date_str = request.form.get("date", datetime.date.today().isoformat())
        group_photo = request.files.get("group_photo")
        
        if not group_photo or group_photo.filename == "":
            flash("Please upload a group photo.", "error")
            return redirect(request.url)

        # Retrieve all students of this class using projection to save memory
        students = list(db.students.find({"class_id": class_id}, {"roll_no": 1, "name": 1, "encodings": 1}))
        if not students:
            flash("No students enrolled in this class.", "error")
            return redirect(request.url)
            
        # Structure DB encodings
        db_encodings = {}
        roll_to_name = {}
        for s in students:
            db_encodings[s["roll_no"]] = s.get("encodings", [])
            roll_to_name[s["roll_no"]] = s["name"]
            
        # ML Inference to parse group photo and match
        img_bytes = group_photo.read()
        identified_rolls = match_faces_in_group(img_bytes, db_encodings, tolerance=0.53)
        
        del img_bytes
        del students
        del db_encodings
        import gc
        gc.collect()
        
        # We don't save DB immediately. Push to review view.
        # Store intermediate in session (within 4KB limits)
        session["review_att"] = {
            "class_id": class_id,
            "subject_id": subject_id,
            "date": date_str,
            "present_rolls": identified_rolls
        }
        return redirect(url_for("teacher.review_attendance"))
        
    return render_template("teacher/setup_attendance.html", teacher=teacher)

@teacher_bp.route("/attendance/review", methods=["GET", "POST"])
def review_attendance():
    if "review_att" not in session:
        return redirect(url_for("teacher.dashboard"))
        
    att_data = session["review_att"]
    
    if request.method == "POST":
        # Save manual corrections
        db = get_db()
        
        # Roll nos returned in form checkbox array as present
        final_present = request.form.getlist("present_rolls")
        
        # Save payload
        payload = {
            "date": att_data["date"],
            "class_id": att_data["class_id"],
            "subject_id": att_data["subject_id"],
            "teacher_email": session.get("user"),
            "present_roll_nos": final_present,
            "created_at": datetime.datetime.utcnow()
        }
        db.attendance.insert_one(payload)
        
        # Increment total lectures since class actually happened
        db.classes.update_one(
            {"_id": att_data["class_id"], "subjects.subject_id": att_data["subject_id"]},
            {"$inc": {"subjects.$.total_lectures": 1}}
        )
        
        session.pop("review_att")
        flash("Attendance successfully recorded and total lectures incremented.", "success")
        return redirect(url_for("teacher.dashboard"))
        
    students = list(get_db().students.find({"class_id": att_data["class_id"]}, {"roll_no": 1, "name": 1}).sort("roll_no", 1))
    return render_template("teacher/review_attendance.html", data=att_data, students=students)

@teacher_bp.route("/reports")
def reports():
    db = get_db()
    email = session.get("user")
    
    # Get attendance history for the teacher
    logs = list(db.attendance.find({"teacher_email": email}).sort("date", -1))
    
    # Fetch all classes first to reduce DB calls (O(1) optimal lookup mapping)
    classes_dict = {str(c['_id']): c for c in db.classes.find()}
    
    # Augment logs with class and subject names for display
    for log in logs:
        cls_info = classes_dict.get(str(log["class_id"]))
        log["class_name"] = cls_info["name"] if cls_info else "Unknown"
        
        if cls_info:
            subj_info = next((s for s in cls_info.get("subjects", []) if str(s["subject_id"]) == str(log["subject_id"])), None)
            log["subject_name"] = subj_info["name"] if subj_info else "Unknown"
        else:
            log["subject_name"] = "Unknown"
            
        log["present_count"] = len(log.get("present_roll_nos", []))
        
    return render_template("teacher/reports.html", logs=logs)
