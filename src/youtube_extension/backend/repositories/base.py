#!/usr/bin/env python3
"""
Base Repository Pattern Implementation
=====================================

Abstract base repository with common CRUD operations and tenant-aware queries.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any, Type, Union
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.exc import NoResultFound, IntegrityError

from models.base import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository with common operations
    """
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
    
    async def create(self, **kwargs) -> T:
        """Create a new entity"""
        try:
            entity = self.model(**kwargs)
            self.session.add(entity)
            await self.session.flush()  # Get the ID without committing
            await self.session.refresh(entity)
            return entity
        except IntegrityError as e:
            await self.session.rollback()
            raise ValueError(f"Entity creation failed: {str(e)}")
    
    async def get_by_id(self, entity_id: Union[str, UUID], tenant_id: Optional[str] = None) -> Optional[T]:
        """Get entity by ID with optional tenant filtering"""
        query = select(self.model).where(self.model.id == entity_id)
        
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        # Exclude soft-deleted records
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_field(self, field: str, value: Any, tenant_id: Optional[str] = None) -> Optional[T]:
        """Get entity by specific field"""
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} does not have field '{field}'")
        
        query = select(self.model).where(getattr(self.model, field) == value)
        
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list_all(
        self, 
        tenant_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """List all entities with optional filtering, pagination, and sorting"""
        
        query = select(self.model)
        
        # Apply tenant filtering
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        # Exclude soft-deleted records
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                field = order_by[1:]
                if hasattr(self.model, field):
                    query = query.order_by(desc(getattr(self.model, field)))
            else:
                if hasattr(self.model, order_by):
                    query = query.order_by(asc(getattr(self.model, order_by)))
        else:
            # Default ordering by created_at desc
            if hasattr(self.model, 'created_at'):
                query = query.order_by(desc(self.model.created_at))
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, entity_id: Union[str, UUID], **kwargs) -> Optional[T]:
        """Update entity by ID"""
        # Remove fields that shouldn't be updated
        update_data = {k: v for k, v in kwargs.items() 
                      if k not in ['id', 'created_at', 'tenant_id']}
        
        # Add updated_at timestamp
        if hasattr(self.model, 'updated_at'):
            update_data['updated_at'] = datetime.utcnow()
        
        query = (
            update(self.model)
            .where(self.model.id == entity_id)
            .values(**update_data)
            .returning(self.model)
        )
        
        result = await self.session.execute(query)
        updated_entity = result.scalar_one_or_none()
        
        if updated_entity:
            await self.session.refresh(updated_entity)
        
        return updated_entity
    
    async def delete(self, entity_id: Union[str, UUID], soft_delete: bool = True) -> bool:
        """Delete entity (soft delete by default)"""
        if soft_delete and hasattr(self.model, 'is_deleted'):
            # Soft delete
            result = await self.update(
                entity_id,
                is_deleted=True,
                deleted_at=datetime.utcnow()
            )
            return result is not None
        else:
            # Hard delete
            query = delete(self.model).where(self.model.id == entity_id)
            result = await self.session.execute(query)
            return result.rowcount > 0
    
    async def count(
        self, 
        tenant_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count entities with optional filtering"""
        query = select(func.count(self.model.id))
        
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def exists(
        self, 
        entity_id: Union[str, UUID],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if entity exists"""
        query = select(func.count(self.model.id)).where(self.model.id == entity_id)
        
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        result = await self.session.execute(query)
        count = result.scalar() or 0
        return count > 0
    
    async def bulk_create(self, entities_data: List[Dict[str, Any]]) -> List[T]:
        """Bulk create entities"""
        entities = [self.model(**data) for data in entities_data]
        self.session.add_all(entities)
        await self.session.flush()
        
        # Refresh all entities to get generated IDs
        for entity in entities:
            await self.session.refresh(entity)
        
        return entities
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update entities"""
        if not updates:
            return 0
        
        # Group updates by entity ID
        for update_data in updates:
            entity_id = update_data.pop('id', None)
            if entity_id:
                query = (
                    update(self.model)
                    .where(self.model.id == entity_id)
                    .values(**update_data)
                )
                await self.session.execute(query)
        
        return len(updates)
    
    async def search(
        self, 
        search_term: str,
        search_fields: List[str],
        tenant_id: Optional[str] = None,
        limit: Optional[int] = 50
    ) -> List[T]:
        """Full-text search across specified fields"""
        if not search_term.strip():
            return []
        
        query = select(self.model)
        
        # Build search conditions
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                search_conditions.append(
                    field_attr.ilike(f"%{search_term}%")
                )
        
        if search_conditions:
            query = query.where(or_(*search_conditions))
        
        if tenant_id and hasattr(self.model, 'tenant_id'):
            query = query.where(self.model.tenant_id == tenant_id)
        
        if hasattr(self.model, 'is_deleted'):
            query = query.where(self.model.is_deleted == False)
        
        if limit:
            query = query.limit(limit)
        
        # Order by relevance (simplified - could use PostgreSQL text search)
        if hasattr(self.model, 'created_at'):
            query = query.order_by(desc(self.model.created_at))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    def with_relationships(self, *relationships):
        """Add eager loading for relationships"""
        # This would be implemented by subclasses to add specific relationships
        return self
    
    def with_options(self, *options):
        """Add query options like selectinload, joinedload"""
        # This would be implemented by subclasses for specific loading strategies
        return self

class TenantAwareRepository(BaseRepository[T]):
    """
    Repository with automatic tenant isolation
    """
    
    def __init__(self, session: AsyncSession, model: Type[T], tenant_id: str):
        super().__init__(session, model)
        self.tenant_id = tenant_id
    
    async def create(self, **kwargs) -> T:
        """Create with automatic tenant assignment"""
        kwargs['tenant_id'] = self.tenant_id
        return await super().create(**kwargs)
    
    async def get_by_id(self, entity_id: Union[str, UUID]) -> Optional[T]:
        """Get by ID with automatic tenant filtering"""
        return await super().get_by_id(entity_id, self.tenant_id)
    
    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get by field with automatic tenant filtering"""
        return await super().get_by_field(field, value, self.tenant_id)
    
    async def list_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """List with automatic tenant filtering"""
        return await super().list_all(
            tenant_id=self.tenant_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            filters=filters
        )
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count with automatic tenant filtering"""
        return await super().count(self.tenant_id, filters)
    
    async def exists(self, entity_id: Union[str, UUID]) -> bool:
        """Check existence with automatic tenant filtering"""
        return await super().exists(entity_id, self.tenant_id)
    
    async def search(
        self,
        search_term: str,
        search_fields: List[str],
        limit: Optional[int] = 50
    ) -> List[T]:
        """Search with automatic tenant filtering"""
        return await super().search(
            search_term,
            search_fields,
            tenant_id=self.tenant_id,
            limit=limit
        )