import os
import gc
from flask import Flask, redirect, url_for, session
from dotenv import load_dotenv
from utils.db import init_db, mongo # Import mongo directly here too

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)

    # 1. Security & Upload Constraints
    # 16MB is fine for the request, but remember face.py will resize it to < 1MB
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.secret_key = os.getenv('SECRET_KEY', 'nit-kkr-secure-999-alpha')
    
    # 2. Database Configuration
    # Ensure you set MONGO_URI in Render Dashboard!
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    
    # 3. Initialize DB with the Indexing logic I gave you
    init_db(app)

    # 4. Register Blueprints (Imported inside to prevent circular issues)
    with app.app_context():
        from routes.auth import auth_bp
        from routes.admin import admin_bp
        from routes.teacher import teacher_bp
        from routes.student import student_bp

        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(admin_bp, url_prefix="/admin")
        app.register_blueprint(teacher_bp, url_prefix="/teacher")
        app.register_blueprint(student_bp, url_prefix="/student")

    @app.route("/")
    def index():
        if "user" in session:
            role = session.get("role")
            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif role == "teacher":
                return redirect(url_for("teacher.dashboard"))
            elif role == "student":
                return redirect(url_for("student.dashboard"))
        return redirect(url_for("auth.login"))

    # Cleanup memory after initialization
    gc.collect()
    
    return app

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8501)) # Streamlit default port use karega
    app.run(host='0.0.0.0', port=port)