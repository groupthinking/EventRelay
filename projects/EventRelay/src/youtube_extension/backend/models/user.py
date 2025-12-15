#!/usr/bin/env python3
"""
User Management Models
=====================

Models for user authentication, profiles, sessions, and activity tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship, Mapped, mapped_column
from enum import Enum as PyEnum
from sqlalchemy import Enum

from .base import BaseModel, TimestampMixin, UUIDMixin

class UserStatus(PyEnum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class AuthProvider(PyEnum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    APPLE = "apple"

class User(BaseModel):
    """
    Core user model with authentication and profile information
    """
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address (unique identifier)"
    )
    
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        doc="Optional username"
    )
    
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Hashed password (null for OAuth users)"
    )
    
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider),
        default=AuthProvider.LOCAL,
        nullable=False,
        doc="Primary authentication provider"
    )
    
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="External provider user ID"
    )
    
    # Profile information
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="First name"
    )
    
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Last name"
    )
    
    full_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        doc="Full display name"
    )
    
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Profile picture URL"
    )
    
    # Account status
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.PENDING_VERIFICATION,
        nullable=False,
        index=True,
        doc="Account status"
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Email verification status"
    )
    
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Email verification timestamp"
    )
    
    # Two-factor authentication
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="2FA enabled status"
    )
    
    two_factor_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="2FA secret key (encrypted)"
    )
    
    backup_codes: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="2FA backup codes"
    )
    
    # Account activity
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Last login timestamp"
    )
    
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Last activity timestamp"
    )
    
    login_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Total login count"
    )
    
    # Preferences
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
        doc="User timezone"
    )
    
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
        doc="Preferred language"
    )
    
    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="User preferences and settings"
    )
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", lazy="dynamic")
    activities = relationship("UserActivity", back_populates="user", lazy="dynamic")
    
    def get_full_name(self) -> str:
        """Get formatted full name"""
        if self.full_name:
            return self.full_name
        
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        
        return " ".join(parts) if parts else self.email.split("@")[0]
    
    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE
    
    def can_login(self) -> bool:
        """Check if user can log in"""
        return self.status in [UserStatus.ACTIVE, UserStatus.PENDING_VERIFICATION]
    
    def update_last_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<User(email='{self.email}', status='{self.status}')>"

class UserProfile(BaseModel):
    """
    Extended user profile information
    """
    __tablename__ = "user_profiles"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Professional information
    job_title: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Job title or position"
    )
    
    company: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Company or organization"
    )
    
    industry: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Industry or field"
    )
    
    # Contact information
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Phone number"
    )
    
    website: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Personal/company website"
    )
    
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="LinkedIn profile URL"
    )
    
    # Bio and interests
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User biography/description"
    )
    
    interests: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="User interests and topics"
    )
    
    skills: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="User skills and expertise"
    )
    
    # Learning preferences
    learning_style: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Preferred learning style"
    )
    
    learning_goals: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Learning objectives and goals"
    )
    
    # Privacy settings
    profile_visibility: Mapped[str] = mapped_column(
        String(20),
        default="private",
        nullable=False,
        doc="Profile visibility (public, private, contacts)"
    )
    
    show_email: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether to show email in profile"
    )
    
    # Additional data
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Custom profile fields"
    )
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def get_skills_by_category(self) -> Dict[str, List[str]]:
        """Get skills organized by category"""
        # This could be enhanced with skill categorization
        return {"technical": self.skills or []}
    
    def add_interest(self, interest: str) -> None:
        """Add interest to user profile"""
        if self.interests is None:
            self.interests = []
        if interest.lower() not in [i.lower() for i in self.interests]:
            self.interests.append(interest)
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id='{self.user_id}')>"

class UserSession(BaseModel):
    """
    User session tracking for security and analytics
    """
    __tablename__ = "user_sessions"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Session information
    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique session token"
    )
    
    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Refresh token for session renewal"
    )
    
    # Session details
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        doc="Client IP address"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Client user agent string"
    )
    
    device_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Device type (desktop, mobile, tablet)"
    )
    
    os: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Operating system"
    )
    
    browser: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Browser name and version"
    )
    
    # Geographic information
    country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Country based on IP"
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="City based on IP"
    )
    
    # Session lifecycle
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        doc="Session expiration time"
    )
    
    last_activity_at: Mapped[datetime] = mapped_column(
        nullable=False,
        doc="Last activity in this session"
    )
    
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Session end time"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether session is active"
    )
    
    # Additional session data
    session_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Additional session information"
    )
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, minutes: int = 60) -> None:
        """Extend session expiration"""
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.last_activity_at = datetime.utcnow()
    
    def end_session(self) -> None:
        """End the session"""
        self.ended_at = datetime.utcnow()
        self.is_active = False
    
    def __repr__(self) -> str:
        return f"<UserSession(user_id='{self.user_id}', active={self.is_active})>"

class UserActivity(BaseModel):
    """
    User activity tracking for analytics and audit
    """
    __tablename__ = "user_activities"
    
    # Foreign key to user
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Activity information
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of activity (login, video_process, etc.)"
    )
    
    activity_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Specific activity name"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Activity description"
    )
    
    # Context information
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Type of resource affected"
    )
    
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="ID of resource affected"
    )
    
    # Request details
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
        doc="Client IP address"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Client user agent"
    )
    
    # Additional data
    activity_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Additional activity data"
    )
    
    # Performance metrics
    response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Response time in milliseconds"
    )
    
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether activity was successful"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if activity failed"
    )
    
    # Relationships
    user = relationship("User", back_populates="activities")
    
    def __repr__(self) -> str:
        return f"<UserActivity(user_id='{self.user_id}', type='{self.activity_type}')>"

# Create indexes for performance
Index("ix_users_email_status", User.email, User.status)
Index("ix_user_sessions_user_active", UserSession.user_id, UserSession.is_active)
Index("ix_user_activities_user_type_created", UserActivity.user_id, UserActivity.activity_type, UserActivity.created_at)