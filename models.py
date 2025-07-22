"""
Database models for RabbitMQ LLM Chat Platform.
Separated from Flask application code for better organization.
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
import secrets
import time
from datetime import datetime

from logger import get_logger

logger = get_logger(__name__)

db = SQLAlchemy()


class User(db.Model):
    """User model with improved security and validation."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    llms = db.relationship('LLM', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password: str) -> None:
        """
        Set user password with secure hashing.
        
        Args:
            password: Plain text password
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        self.password_hash = generate_password_hash(password)
        logger.debug(f"Password set for user {self.email}")
    
    def check_password(self, password: str) -> bool:
        """
        Check if provided password matches stored hash.
        
        Args:
            password: Plain text password to check
            
        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def generate_confirmation_token(self) -> str:
        """
        Generate email confirmation token.
        
        Returns:
            Confirmation token string
        """
        return secrets.token_urlsafe(32)
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
        logger.debug(f"Updated last login for user {self.email}")
    
    def to_dict(self) -> dict:
        """
        Convert user to dictionary (excluding sensitive data).
        
        Returns:
            Dictionary representation of user
        """
        return {
            'id': self.id,
            'email': self.email,
            'confirmed': self.confirmed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'llm_count': len(self.llms)
        }
    
    def __repr__(self) -> str:
        return f'<User {self.email}>'


class LLM(db.Model):
    """LLM model with improved fields and validation."""
    
    __tablename__ = 'llms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    api_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    endpoint = db.Column(db.String(255))
    provider = db.Column(db.String(50))  # 'openai', 'anthropic', 'local', etc.
    model_type = db.Column(db.String(100))  # 'gpt-4', 'claude-3-sonnet', etc.
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    
    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    @classmethod
    def generate_api_key(cls) -> str:
        """
        Generate secure API key for LLM.
        
        Returns:
            Generated API key
        """
        return secrets.token_hex(32)
    
    def update_usage(self) -> None:
        """Update usage statistics."""
        self.last_used = datetime.utcnow()
        self.usage_count += 1
        db.session.commit()
        logger.debug(f"Updated usage for LLM {self.name} (count: {self.usage_count})")
    
    def deactivate(self) -> None:
        """Deactivate LLM."""
        self.is_active = False
        db.session.commit()
        logger.info(f"Deactivated LLM {self.name}")
    
    def activate(self) -> None:
        """Activate LLM."""
        self.is_active = True
        db.session.commit()
        logger.info(f"Activated LLM {self.name}")
    
    def to_dict(self) -> dict:
        """
        Convert LLM to dictionary (excluding sensitive data).
        
        Returns:
            Dictionary representation of LLM
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'endpoint': self.endpoint,
            'provider': self.provider,
            'model_type': self.model_type,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count,
            'user_id': self.user_id
        }
    
    def __repr__(self) -> str:
        return f'<LLM {self.name} ({self.provider})>'


class ChatroomParticipant(db.Model):
    """Many-to-many relationship table for chatroom participants."""
    
    __tablename__ = 'chatroom_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    chatroom_name = db.Column(db.String(100), nullable=False)
    participant_id = db.Column(db.String(100), nullable=False)
    participant_type = db.Column(db.String(20), nullable=False)  # 'user' or 'llm'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('chatroom_name', 'participant_id', 'participant_type'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'chatroom_name': self.chatroom_name,
            'participant_id': self.participant_id,
            'participant_type': self.participant_type,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'is_active': self.is_active
        }


class ChatMessage(db.Model):
    """Model for storing chat messages persistently."""
    
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    chatroom_name = db.Column(db.String(100), nullable=False, index=True)
    sender_id = db.Column(db.String(100), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'user' or 'llm'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    message_metadata = db.Column(db.JSON)  # Store additional message metadata as JSON
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'chatroom_name': self.chatroom_name,
            'sender_id': self.sender_id,
            'sender_type': self.sender_type,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.message_metadata
        }
    
    def __repr__(self) -> str:
        return f'<ChatMessage {self.id} in {self.chatroom_name}>'


def init_db(app) -> None:
    """
    Initialize database with Flask app.
    
    Args:
        app: Flask application instance
    """
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        logger.info("Database tables created successfully")


def create_admin_user(email: str, password: str) -> Optional[User]:
    """
    Create an admin user if it doesn't exist.
    
    Args:
        email: Admin email
        password: Admin password
        
    Returns:
        User object if created, None if already exists
    """
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        logger.info(f"Admin user {email} already exists")
        return None
    
    admin_user = User(email=email, confirmed=True)
    admin_user.set_password(password)
    
    db.session.add(admin_user)
    db.session.commit()
    
    logger.info(f"Created admin user: {email}")
    return admin_user