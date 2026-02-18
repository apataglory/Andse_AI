from extensions import db
from flask_login import UserMixin
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """
    MASTER USER IDENTITY: 
    Supports Secure Password Auth, Google OAuth, and Multi-Factor Verification.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # Advanced Verification System
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10), nullable=True) 
    account_status = db.Column(db.String(20), default='active') 
    
    # Neural Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade="all, delete-orphan")
    sessions = db.relationship('ChatSession', backref='user', lazy=True, cascade="all, delete-orphan")
    files = db.relationship('FileMetadata', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    theme = db.Column(db.String(20), default='dark')
    accent_color = db.Column(db.String(20), default='#3b82f6')
    preferred_model = db.Column(db.String(50), default='gemini-2.0-flash')
    system_prompt = db.Column(db.Text, default="You are ANDSE, a highly advanced AI.")
    voice_enabled = db.Column(db.Boolean, default=True)
    search_enabled = db.Column(db.Boolean, default=True)
    vision_enabled = db.Column(db.Boolean, default=True)

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), default='New Neural Link')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('Message', backref='session', lazy='dynamic', cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    content = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), nullable=True)
    tokens_count = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class FileMetadata(db.Model):
    """
    NEURAL ASSETS:
    Tracks files uploaded for analysis or storage.
    """
    __tablename__ = 'file_metadata'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer) # In bytes
    storage_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
