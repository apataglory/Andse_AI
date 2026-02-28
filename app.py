# ==============================================================================
# ANDSE AI | NEURAL CORE ENGINE v4.0.0 (MASSIVE)
# ==============================================================================
# CRITICAL: GEVENT MONKEY PATCH (Must be first to avoid recursion errors)
try:
    from gevent import monkey
    monkey.patch_all()
except ImportError:
    print("⚠️ Gevent not detected. Running on standard threading.")

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

# --- SYSTEM PATH INJECTION ---
sys.path.append(os.getcwd())

# --- CORE EXTENSIONS & MODELS ---
from extensions import db, socketio, mail
from database.models import User, Message as ChatMessage, FileMetadata, UserSettings

# ==============================================================================
# ADVANCED FEATURE LOADING ENGINE (STRICT PRESERVATION)
# ==============================================================================
def advanced_feature_loader(app):
    """Dynamically initializes all neural modules without removing functionality."""
    modules = [
        ('auth', 'auth_bp', '/auth'),
        ('chat_manager', 'chat_bp', '/chat'),
        ('settings', 'settings_bp', '/settings'),
        ('video_editor', 'video_bp', '/video'),
        ('image_generator', 'image_bp', '/generate'),
        ('file_handler', 'file_bp', '/files'),
        ('webscraper', 'scraper_bp', '/scrape'),
        ('voice_engine', 'voice_bp', '/voice')
    ]
    
    loaded_count = 0
    for mod_path, bp_name, url_prefix in modules:
        try:
            # Multi-strategy import attempt
            module = None
            try:
                module = __import__(mod_path, fromlist=[bp_name])
            except ImportError:
                # Fallback for nested structures
                if mod_path == 'chat_manager':
                    from chat import chat_manager as module
                elif mod_path == 'webscraper':
                    import webscraper as module
            
            if module and hasattr(module, bp_name):
                bp = getattr(module, bp_name)
                app.register_blueprint(bp, url_prefix=url_prefix)
                app.logger.info(f"🟢 [MODULE LOADED] {mod_path} at {url_prefix}")
                loaded_count += 1
            else:
                app.logger.warning(f"🟡 [MODULE SKIPPED] {mod_path}: Blueprint '{bp_name}' not found.")
        except Exception as e:
            app.logger.error(f"🔴 [CRITICAL ERROR] Failed to load {mod_path}: {str(e)}")
    
    return loaded_count

# ==============================================================================
# SYSTEM TELEMETRY & GARBAGE COLLECTION
# ==============================================================================
def start_garbage_collector(app):
    """Background thread to clean up temporary video/image/audio files."""
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
                                # Delete files older than 2 hours
                                if os.stat(f_path).st_mtime < now - 7200:
                                    os.remove(f_path)
                except Exception as e:
                    print(f"Cleanup Error: {e}")
            time.sleep(3600) # Run every hour

    thread = threading.Thread(target=run_cleanup, daemon=True)
    thread.start()

# ==============================================================================
# APP FACTORY
# ==============================================================================
def create_massive_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # 1. LOAD CONFIGURATION
    load_dotenv()
    db_url = os.getenv('DATABASE_URL', 'sqlite:///andse_neural.db')
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'neural-gate-99-beta'),
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 300},
        MAX_CONTENT_LENGTH=2 * 1024 * 1024 * 1024, # 2GB limit for video processing
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'),
        IMAGE_GEN_FOLDER=os.path.join(app.root_path, 'static', 'generated_images'),
        AUDIO_CACHE=os.path.join(app.root_path, 'static', 'audio_cache'),
        VIDEO_CACHE=os.path.join(app.root_path, 'static', 'video_cache'),
        GOOGLE_CLIENT_ID=os.getenv('GOOGLE_CLIENT_ID'),
        GOOGLE_CLIENT_SECRET=os.getenv('GOOGLE_CLIENT_SECRET'),
        GEMINI_API_KEY=os.getenv('GEMINI_API_KEY'),
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD')
    )

    # 2. PROXY & HTTPS HANDLING (FOR RENDER/DOCKER)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    # 3. DIRECTORY PROVISIONING
    for key in ['UPLOAD_FOLDER', 'IMAGE_GEN_FOLDER', 'AUDIO_CACHE', 'VIDEO_CACHE']:
        os.makedirs(app.config[key], exist_ok=True)

    # 4. INITIALIZE EXTENSIONS
    CORS(app, resources={r"/*": {"origins": "*"}})
    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)
    socketio.init_app(app, 
        cors_allowed_origins="*", 
        async_mode='gevent', 
        ping_timeout=60, 
        manage_session=True
    )

    # 5. AUTHENTICATION ENGINE
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 6. MIDDLEWARE: PERFORMANCE MONITORING
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_response(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            app.logger.info(f"Path: {request.path} | Time: {duration:.4f}s | Status: {response.status_code}")
        return response

    # 7. FEATURE LOADING & OAUTH CONFIG
    from auth import configure_oauth
    configure_oauth(app)
    loaded_count = advanced_feature_loader(app)
    app.logger.info(f"🧠 Total Neural Modules Active: {loaded_count}")

    # 8. BACKGROUND TASKS
    start_garbage_collector(app)

    # 9. GLOBAL HANDLERS
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('chat.interface'))
        return render_template('login.html')

    @app.errorhandler(404)
    def not_found(e):
        return render_template('login.html'), 404

    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "modules_loaded": loaded_count,
            "engine": "v4.0.0-Massive"
        })

    # 10. DATABASE AUTO-REPAIR & SYNC
    with app.app_context():
        try:
            db.create_all()
            # Verify connection
            db.session.execute(text("SELECT 1"))
            app.logger.info("⚡ Neural Database is online and synchronized.")
        except Exception as e:
            app.logger.error(f"💥 Database Sync Error: {e}")

    return app

# ==============================================================================
# EXECUTION ENTRY POINT
# ==============================================================================
app = create_massive_app()

def handle_shutdown(signum, frame):
    """Ensures clean shutdown for background threads."""
    print(f"\n🛑 Received signal {signum}. Shutting down Neural Core...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    # Using socketio.run for real-time capabilities across all features
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        debug=os.getenv('DEBUG', 'False') == 'True',
        use_reloader=False # Reloader can interfere with Gevent monkey patching
    )


