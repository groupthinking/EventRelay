#!/usr/bin/env python3
"""
Tenant Management Models
=======================

Models for multi-tenant architecture with enterprise features.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Boolean, Integer, Enum, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from enum import Enum as PyEnum

from .base import BaseModel, TimestampMixin, UUIDMixin

class TenantStatus(PyEnum):
    """Tenant account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended" 
    CANCELLED = "cancelled"
    TRIAL = "trial"
    PENDING = "pending"

class SubscriptionTier(PyEnum):
    """Subscription tier levels"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Tenant(BaseModel):
    """
    Tenant model for multi-tenant architecture
    """
    __tablename__ = "tenants"
    
    # Core tenant information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Tenant organization name"
    )
    
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="URL-friendly tenant identifier"
    )
    
    domain: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        doc="Custom domain for tenant"
    )
    
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus),
        default=TenantStatus.TRIAL,
        nullable=False,
        index=True,
        doc="Tenant account status"
    )
    
    # Contact information
    contact_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Primary contact name"
    )
    
    contact_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Primary contact email"
    )
    
    # Subscription management
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False,
        doc="Current subscription tier"
    )
    
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Subscription expiration date"
    )
    
    # Usage limits and quotas
    video_processing_quota: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        doc="Monthly video processing quota"
    )
    
    storage_quota_gb: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        doc="Storage quota in GB"
    )
    
    api_rate_limit: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
        doc="API requests per hour limit"
    )
    
    # Feature flags
    features_enabled: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Enabled features configuration"
    )
    
    # Security settings
    require_2fa: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Require two-factor authentication"
    )
    
    ip_whitelist: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Allowed IP addresses"
    )
    
    # Custom configuration
    custom_settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="Custom tenant settings"
    )
    
    # Relationships
    users = relationship("TenantUser", back_populates="tenant", lazy="dynamic")
    subscriptions = relationship("TenantSubscription", back_populates="tenant", lazy="dynamic")
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled for this tenant"""
        return self.features_enabled.get(feature, False)
    
    def enable_feature(self, feature: str, enabled: bool = True) -> None:
        """Enable or disable a feature"""
        if self.features_enabled is None:
            self.features_enabled = {}
        self.features_enabled[feature] = enabled
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get tenant usage statistics"""
        # This would be implemented with actual usage tracking
        return {
            "videos_processed_this_month": 0,
            "storage_used_gb": 0,
            "api_calls_this_hour": 0,
            "active_users": 0
        }
    
    def __repr__(self) -> str:
        return f"<Tenant(name='{self.name}', slug='{self.slug}', status='{self.status}')>"

class TenantUser(BaseModel):
    """
    Association between users and tenants with role-based access
    """
    __tablename__ = "tenant_users"
    
    # Foreign keys
    tenant_id_fk: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
        index=True
    )
    
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Role and permissions
    role: Mapped[str] = mapped_column(
        String(50),
        default="member",
        nullable=False,
        doc="User role within tenant (owner, admin, member, viewer)"
    )
    
    permissions: Mapped[List[str]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
        doc="Specific permissions granted"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether user is active in this tenant"
    )
    
    invited_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="When user was invited"
    )
    
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="When user joined tenant"
    )
    
    invited_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Who invited this user"
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User")
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in (self.permissions or [])
    
    def add_permission(self, permission: str) -> None:
        """Add permission to user"""
        if self.permissions is None:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission: str) -> None:
        """Remove permission from user"""
        if self.permissions and permission in self.permissions:
            self.permissions.remove(permission)
    
    def __repr__(self) -> str:
        return f"<TenantUser(tenant_id='{self.tenant_id}', user_id='{self.user_id}', role='{self.role}')>"

class TenantSubscription(BaseModel):
    """
    Tenant subscription management and billing
    """
    __tablename__ = "tenant_subscriptions"
    
    # Foreign key
    tenant_id_fk: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
        index=True
    )
    
    # Subscription details
    subscription_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="External subscription ID (Stripe, etc.)"
    )
    
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier),
        nullable=False,
        doc="Subscription tier"
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Subscription status (active, cancelled, etc.)"
    )
    
    # Billing information
    amount: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Subscription amount"
    )
    
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        doc="Currency code"
    )
    
    billing_interval: Mapped[str] = mapped_column(
        String(20),
        default="monthly",
        nullable=False,
        doc="Billing interval (monthly, yearly, etc.)"
    )
    
    # Subscription lifecycle
    starts_at: Mapped[datetime] = mapped_column(
        nullable=False,
        doc="Subscription start date"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Subscription expiration date"
    )
    
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Trial period end date"
    )
    
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Subscription cancellation date"
    )
    
    # Payment tracking
    last_payment_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Last successful payment date"
    )
    
    next_payment_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Next payment due date"
    )
    
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Payment method type"
    )
    
    # External references
    external_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
        doc="External billing system data"
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="subscriptions")
    
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.status != "active":
            return False
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
            
        return True
    
    def days_until_expiry(self) -> Optional[int]:
        """Get days until subscription expires"""
        if not self.expires_at:
            return None
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def __repr__(self) -> str:
        return f"<TenantSubscription(tenant_id='{self.tenant_id}', tier='{self.tier}', status='{self.status}')>"