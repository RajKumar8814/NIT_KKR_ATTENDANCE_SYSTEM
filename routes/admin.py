import os
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from utils.auth import role_required
from utils.db import get_db
from utils.face import extract_face_encodings
import uuid

admin_bp = Blueprint("admin", __name__)

@admin_bp.before_request
@role_required('admin')
def check_admin():
    pass

@admin_bp.route("/dashboard")
def dashboard():
    db = get_db()
    students_count = db.students.count_documents({})
    teachers_count = db.teachers.count_documents({})
    classes_count = db.classes.count_documents({})
    return render_template("admin/dashboard.html", sc=students_count, tc=teachers_count, cc=classes_count)

# --- Teacher Management ---
@admin_bp.route("/teachers", methods=["GET", "POST"])
def manage_teachers():
    db = get_db()
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        name = request.form.get("name").strip()
        
        if db.teachers.find_one({"email": email}):
            flash("Teacher email already exists", "error")
        else:
            db.teachers.insert_one({"email": email, "name": name, "subjects": []})
            flash("Teacher added successfully", "success")
        return redirect(url_for("admin.manage_teachers"))
        
    teachers = list(db.teachers.find())
    return render_template("admin/teachers.html", teachers=teachers)

# --- Class & Subject Management ---
@admin_bp.route("/classes", methods=["GET", "POST"])
def manage_classes():
    db = get_db()
    if request.method == "POST":
        class_name = request.form.get("class_name").strip() # e.g. CSE 2nd Year
        
        if db.classes.find_one({"name": class_name}):
            flash("Class already exists", "error")
        else:
            db.classes.insert_one({"_id": str(uuid.uuid4()), "name": class_name, "subjects": []})
            flash("Class added successfully", "success")
        return redirect(url_for("admin.manage_classes"))
        
    classes = list(db.classes.find())
    teachers = list(db.teachers.find())
    return render_template("admin/classes.html", classes=classes, teachers=teachers)

@admin_bp.route("/classes/<class_id>/subjects", methods=["POST"])
def add_subject(class_id):
    db = get_db()
    subject_name = request.form.get("subject_name").strip()
    teacher_email = request.form.get("teacher_email", "").strip()
    
    cls = db.classes.find_one({"_id": class_id})
    if not cls:
        return redirect(url_for("admin.manage_classes"))

    existing_subj = None
    for subj in cls.get("subjects", []):
        if subj.get("name").lower() == subject_name.lower():
            existing_subj = subj
            break

    if existing_subj:
        # UPSERT LOGIC
        subject_id = existing_subj.get("subject_id")
        old_teacher = existing_subj.get("teacher_email")
        
        if old_teacher and old_teacher != teacher_email:
            db.teachers.update_one(
                {"email": old_teacher},
                {"$pull": {"subjects": {"class_id": class_id, "subject_id": subject_id}}}
            )
            
        if teacher_email and old_teacher != teacher_email:
            db.teachers.update_one(
                {"email": teacher_email},
                {"$push": {"subjects": {"class_id": class_id, "subject_id": subject_id, "name": existing_subj.get("name")}}}
            )
            
        db.classes.update_one(
            {"_id": class_id, "subjects.subject_id": subject_id},
            {"$set": {"subjects.$.teacher_email": teacher_email}}
        )
        flash(f"Subject '{subject_name}' configuration updated.", "success")
        
    else:
        # INSERT LOGIC
        subject_id = str(uuid.uuid4())
        subject = {
            "subject_id": subject_id,
            "name": subject_name,
            "teacher_email": teacher_email,
            "total_lectures": 0
        }
        
        db.classes.update_one({"_id": class_id}, {"$push": {"subjects": subject}})
        
        if teacher_email:
            db.teachers.update_one(
                {"email": teacher_email}, 
                {"$push": {"subjects": {"class_id": class_id, "subject_id": subject_id, "name": subject_name}}}
            )
        
        flash("Subject added successfully", "success")
        
    return redirect(url_for("admin.manage_classes"))

@admin_bp.route("/classes/<class_id>/subjects/<subject_id>/remove_teacher", methods=["POST"])
def remove_teacher_from_subject(class_id, subject_id):
    db = get_db()
    
    # Find the class and the subject to know which teacher to remove it from
    cls = db.classes.find_one({"_id": class_id})
    if not cls: 
        return redirect(url_for("admin.manage_classes"))
    
    target_teacher = None
    for subj in cls.get("subjects", []):
        if subj.get("subject_id") == subject_id:
            target_teacher = subj.get("teacher_email")
            break
            
    if target_teacher:
        # Remove from teacher's array
        db.teachers.update_one(
            {"email": target_teacher},
            {"$pull": {"subjects": {"class_id": class_id, "subject_id": subject_id}}}
        )
        
    # Update the class subject to unassigned (empty string)
    db.classes.update_one(
        {"_id": class_id, "subjects.subject_id": subject_id},
        {"$set": {"subjects.$.teacher_email": ""}}
    )
    
    flash("Teacher unassigned successfully", "success")
    return redirect(url_for("admin.manage_classes"))

@admin_bp.route("/classes/<class_id>/subjects/<subject_id>/delete", methods=["POST"])
def delete_subject_from_class(class_id, subject_id):
    db = get_db()
    
    cls = db.classes.find_one({"_id": class_id})
    if not cls: return redirect(url_for("admin.manage_classes"))
        
    for subj in cls.get("subjects", []):
        if subj.get("subject_id") == subject_id:
            teacher_email = subj.get("teacher_email")
            if teacher_email:
                db.teachers.update_one(
                    {"email": teacher_email},
                    {"$pull": {"subjects": {"subject_id": subject_id, "class_id": class_id}}}
                )
            break
            
    db.classes.update_one(
        {"_id": class_id},
        {"$pull": {"subjects": {"subject_id": subject_id}}}
    )
    
    flash("Subject permanently removed from class schedule.", "success")
    return redirect(url_for("admin.manage_classes"))

# --- Student Management ---
@admin_bp.route("/students", methods=["GET", "POST"])
def manage_students():
    db = get_db()
    if request.method == "POST":
        roll_no = request.form.get("roll_no").strip()
        name = request.form.get("name").strip()
        email = request.form.get("email").strip().lower()
        branch = request.form.get("branch").strip()
        year = request.form.get("year").strip()
        class_id = request.form.get("class_id").strip()
        
        photos = request.files.getlist("photos") # 1-5 photos
        
        if db.students.find_one({"roll_no": roll_no}):
            flash("Student roll no already exists", "error")
            return redirect(url_for("admin.manage_students"))
            
        encodings = []
        for file in photos[:5]: # Ensure absolute max 5 photos
            if file and file.filename != '':
                image_bytes = file.read()
                try:
                    encs = extract_face_encodings(image_bytes)
                    if encs:
                        # Append the first face found in the image. encs[0] is already a Python list.
                        encodings.append(encs[0])
                except Exception as e:
                    print("Error extracting encoding:", e)
                finally:
                    # Memory Purge
                    del image_bytes
                    import gc
                    gc.collect()
        
        if not encodings:
            flash("Could not detect any faces in uploaded photos. Please try better images.", "error")
            return redirect(url_for("admin.manage_students"))
            
        db.students.insert_one({
            "roll_no": roll_no,
            "name": name,
            "email": email,
            "branch": branch,
            "year": year,
            "class_id": class_id,
            "encodings": encodings
        })
        flash(f"Student added successfully with {len(encodings)} encodings", "success")
        return redirect(url_for("admin.manage_students"))
        
    students = list(db.students.find())
    classes = list(db.classes.find())
    return render_template("admin/students.html", students=students, classes=classes)

@admin_bp.route("/students/delete/<roll_no>", methods=["POST"])
def delete_student(roll_no):
    db = get_db()
    db.students.delete_one({"roll_no": roll_no})
    flash("Student deleted successfully", "success")
    return redirect(url_for("admin.manage_students"))
