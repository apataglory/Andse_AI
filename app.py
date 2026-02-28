# ==============================================================================
# ANDSE AI | NEURAL CORE ENGINE v4.2.0 (HYBRID STABLE)
# ==============================================================================

# --- GEVENT PATCH ---
try:
    from gevent import monkey
    monkey.patch_all()
except ImportError:
    print("Gevent not detected. Running standard threading.")

import os
import sys
import time
import logging
import threading
import signal
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, jsonify, request, g
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import text

sys.path.append(os.getcwd())

from extensions import db, socketio, mail
from database.models import User


# ==============================================================================
# GARBAGE COLLECTOR (SAFE BACKGROUND THREAD)
# ==============================================================================

def start_garbage_collector(app):
    def run_cleanup():
        while True:
            with app.app_context():
                try:
                    now = time.time()
                    for folder in ['VIDEO_CACHE', 'IMAGE_GEN_FOLDER', 'AUDIO_CACHE']:
                        path = app.config.get(folder)
                        if path and os.path.exists(path):
                            for f in os.listdir(path):
                                f_path = os.path.join(path, f)
                                if os.path.isfile(f_path):
                                    if os.stat(f_path).st_mtime < now - 7200:
                                        os.remove(f_path)
                                        app.logger.info(f"Cleanup removed: {f_path}")
                except Exception as e:
                    app.logger.error(f"Cleanup error: {e}")
            time.sleep(3600)

    thread = threading.Thread(target=run_cleanup, daemon=True)
    thread.start()


# ==============================================================================
# APP FACTORY
# ==============================================================================

def create_massive_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # ---------------- CONFIG ----------------
    load_dotenv()

    db_url = os.getenv('DATABASE_URL', 'sqlite:///andse_neural.db')
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'neural-gate-99-beta'),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},

        MAX_CONTENT_LENGTH=2 * 1024 * 1024 * 1024,

        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'),
        IMAGE_GEN_FOLDER=os.path.join(app.root_path, 'static', 'generated_images'),
        AUDIO_CACHE=os.path.join(app.root_path, 'static', 'audio_cache'),
        VIDEO_CACHE=os.path.join(app.root_path, 'static', 'video_cache'),

        GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID'),
        GOOGLE_CLIENT_SECRET=os.getenv('GOOGLE_CLIENT_SECRET'),

        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD')
    )

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    for key in ['UPLOAD_FOLDER', 'IMAGE_GEN_FOLDER', 'AUDIO_CACHE', 'VIDEO_CACHE']:
        os.makedirs(app.config[key], exist_ok=True)

    # ---------------- EXTENSIONS ----------------
    CORS(app)
    db.init_app(app)
    mail.init_app(app)
    Migrate(app, db)

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="gevent",
        manage_session=False
    )

    # ---------------- LOGIN ----------------
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # ---------------- PERFORMANCE LOGGING ----------------
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_response(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            app.logger.info(
                f"{request.method} {request.path} | {response.status_code} | {duration:.4f}s"
            )
        return response

    # ---------------- BLUEPRINTS ----------------
    from auth import configure_oauth, auth_bp
    configure_oauth(app)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from chat_manager import chat_bp
    app.register_blueprint(chat_bp, url_prefix="/chat")

    from settings import settings_bp
    app.register_blueprint(settings_bp, url_prefix="/settings")

    from file_handler import file_bp
    app.register_blueprint(file_bp, url_prefix="/files")

    # ---------------- ROOT ROUTES ----------------
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('chat.interface'))
        return render_template('login.html')

    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "engine": "v4.2.0-Hybrid"
        })

    # ---------------- DATABASE SYNC ----------------
    with app.app_context():
        try:
            db.create_all()
            db.session.execute(text("SELECT 1"))
            app.logger.info("Database online.")
        except Exception as e:
            app.logger.error(f"Database error: {e}")

    # ---------------- BACKGROUND TASK ----------------
    start_garbage_collector(app)

    return app


# ==============================================================================
# CREATE APP FOR GUNICORN
# ==============================================================================

app = create_massive_app()


# ==============================================================================
# LOCAL DEV ENTRY
# ==============================================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
