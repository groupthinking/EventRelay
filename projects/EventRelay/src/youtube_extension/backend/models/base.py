#!/usr/bin/env python3
"""
Base Database Models
===================

Base classes and mixins for all database models with multi-tenant support.
"""

import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

class Base(DeclarativeBase):
    """Base class for all database models"""
    type_annotation_map = {
        dict: JSONB,
        Dict[str, Any]: JSONB,
    }

class TimestampMixin:
    """Mixin for automatic timestamp management"""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        doc="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Record last update timestamp"
    )

class TenantMixin:
    """Mixin for multi-tenant row-level security"""
    
    tenant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Tenant identifier for multi-tenancy"
    )
    
    @hybrid_property
    def is_accessible(self):
        """Check if record is accessible to current tenant"""
        # This will be enhanced by RLS policies at database level
        return True
    
    @declared_attr
    def __table_args__(cls):
        """Add tenant-based indexes and constraints"""
        return (
            # Add tenant-based index for performance
            {'postgresql_with': {'tenant_id': 'btree'}},
        )

class UUIDMixin:
    """Mixin for UUID primary keys"""
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        doc="Unique identifier"
    )

class SoftDeleteMixin:
    """Mixin for soft deletion support"""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Soft deletion timestamp"
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Soft deletion flag"
    )
    
    def soft_delete(self) -> None:
        """Perform soft deletion"""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
    
    def restore(self) -> None:
        """Restore soft deleted record"""
        self.deleted_at = None
        self.is_deleted = False

class AuditMixin:
    """Mixin for audit trail tracking"""
    
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User who created this record"
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User who last updated this record"
    )
    
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Record version for optimistic locking"
    )

class MetadataMixin:
    """Mixin for flexible metadata storage"""
    
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Flexible metadata storage"
    )
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)

class SearchableMixin:
    """Mixin for full-text search capabilities"""
    
    search_vector: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Full-text search vector"
    )
    
    @declared_attr
    def __table_args__(cls):
        """Add full-text search index"""
        from sqlalchemy import Index
        return (
            Index(f'ix_{cls.__tablename__}_search_vector', 
                  'search_vector', 
                  postgresql_using='gin'),
        )

class BaseModel(Base, UUIDMixin, TimestampMixin, TenantMixin, SoftDeleteMixin, 
                AuditMixin, MetadataMixin):
    """
    Complete base model with all mixins for enterprise features
    """
    __abstract__ = True
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary representation"""
        result = {}
        
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle special types
            if isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            elif isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        
        if include_metadata and self.metadata:
            result['metadata'] = self.metadata
            
        return result
    
    def update_from_dict(self, data: Dict[str, Any], 
                        exclude_fields: set = None) -> None:
        """Update model from dictionary data"""
        if exclude_fields is None:
            exclude_fields = {
                'id', 'created_at', 'updated_at', 
                'tenant_id', 'deleted_at', 'is_deleted'
            }
        
        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model"""
        return f"<{self.__class__.__name__}(id={self.id}, tenant_id={self.tenant_id})>"