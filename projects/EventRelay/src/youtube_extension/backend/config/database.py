#!/usr/bin/env python3
"""
Database Configuration for Thenile PostgreSQL Integration
========================================================

Complete PostgreSQL setup with Thenile, including:
- Multi-tenant architecture with row-level security
- Connection pooling optimization
- Performance monitoring and health checks
- Security and authentication
"""

import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, event, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import QueuePool
from pydantic import BaseSettings, Field
import asyncpg
import psutil
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    
    # Thenile PostgreSQL Configuration
    thenile_host: str = Field(..., env='THENILE_DB_HOST')
    thenile_port: int = Field(5432, env='THENILE_DB_PORT')
    thenile_database: str = Field(..., env='THENILE_DB_NAME')
    thenile_username: str = Field(..., env='THENILE_DB_USERNAME')
    thenile_password: str = Field(..., env='THENILE_DB_PASSWORD')
    thenile_ssl_mode: str = Field('require', env='THENILE_SSL_MODE')
    
    # Connection Pool Settings
    pool_size: int = Field(20, env='DB_POOL_SIZE')
    max_overflow: int = Field(30, env='DB_MAX_OVERFLOW')
    pool_timeout: int = Field(30, env='DB_POOL_TIMEOUT')
    pool_recycle: int = Field(3600, env='DB_POOL_RECYCLE')  # 1 hour
    pool_pre_ping: bool = Field(True, env='DB_POOL_PRE_PING')
    
    # Performance Settings
    statement_timeout: int = Field(30000, env='DB_STATEMENT_TIMEOUT')  # 30 seconds
    query_timeout: int = Field(120000, env='DB_QUERY_TIMEOUT')  # 2 minutes
    connection_timeout: int = Field(10, env='DB_CONNECTION_TIMEOUT')  # 10 seconds
    
    # Multi-tenant Settings
    default_tenant_id: str = Field('default', env='DEFAULT_TENANT_ID')
    enable_row_level_security: bool = Field(True, env='ENABLE_RLS')
    
    # Monitoring Settings
    enable_monitoring: bool = Field(True, env='DB_ENABLE_MONITORING')
    slow_query_threshold: float = Field(1.0, env='SLOW_QUERY_THRESHOLD')  # 1 second
    
    class Config:
        env_file = '.env'
        case_sensitive = False

    @property
    def database_url(self) -> str:
        """Construct database URL for SQLAlchemy"""
        # Allow direct override
        if os.getenv('DATABASE_URL'):
            return os.getenv('DATABASE_URL')
            
        # Handle Unix socket (Cloud SQL)
        if self.thenile_host.startswith('/'):
            return (
                f"postgresql+asyncpg://{self.thenile_username}:{self.thenile_password}"
                f"@/{self.thenile_database}"
                f"?host={self.thenile_host}"
            )
            
        return (
            f"postgresql+asyncpg://{self.thenile_username}:{self.thenile_password}"
            f"@{self.thenile_host}:{self.thenile_port}/{self.thenile_database}"
            f"?sslmode={self.thenile_ssl_mode}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """Construct synchronous database URL"""
        if os.getenv('DATABASE_URL'):
            # Convert asyncpg URL to sync psycopg2/default URL if needed
            url = os.getenv('DATABASE_URL')
            return url.replace('+asyncpg', '')

        if self.thenile_host.startswith('/'):
            return (
                f"postgresql://{self.thenile_username}:{self.thenile_password}"
                f"@/{self.thenile_database}"
                f"?host={self.thenile_host}"
            )

        return (
            f"postgresql://{self.thenile_username}:{self.thenile_password}"
            f"@{self.thenile_host}:{self.thenile_port}/{self.thenile_database}"
            f"?sslmode={self.thenile_ssl_mode}"
        )

# Global settings instance
db_settings = DatabaseSettings()

class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )

class DatabaseManager:
    """
    Comprehensive database manager for Thenile PostgreSQL integration
    """
    
    def __init__(self, settings: DatabaseSettings = db_settings):
        self.settings = settings
        self.async_engine: Optional[Any] = None
        self.sync_engine: Optional[Engine] = None
        self.async_session_maker: Optional[async_sessionmaker] = None
        self.sync_session_maker: Optional[sessionmaker] = None
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'slow_queries': 0,
            'query_count': 0,
            'last_health_check': None
        }
    
    async def initialize(self) -> None:
        """Initialize database connections and configuration"""
        try:
            logger.info("Initializing Thenile PostgreSQL database connection...")
            
            # Create async engine with optimized settings
            self.async_engine = create_async_engine(
                self.settings.database_url,
                poolclass=QueuePool,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_timeout=self.settings.pool_timeout,
                pool_recycle=self.settings.pool_recycle,
                pool_pre_ping=self.settings.pool_pre_ping,
                echo=False,  # Set to True for SQL logging in development
                future=True,
                connect_args={
                    "command_timeout": self.settings.connection_timeout,
                    "statement_timeout": self.settings.statement_timeout,
                    "server_settings": {
                        "jit": "off",  # Disable JIT for faster query starts
                        "application_name": "UVAI-Platform"
                    }
                }
            )
            
            # Create sync engine for migrations and admin tasks
            self.sync_engine = create_engine(
                self.settings.sync_database_url,
                poolclass=QueuePool,
                pool_size=5,  # Smaller pool for sync operations
                max_overflow=10,
                pool_timeout=self.settings.pool_timeout,
                pool_recycle=self.settings.pool_recycle,
                pool_pre_ping=self.settings.pool_pre_ping,
                echo=False,
                future=True,
                connect_args={
                    "sslmode": self.settings.thenile_ssl_mode,
                    "connect_timeout": self.settings.connection_timeout,
                    "application_name": "UVAI-Platform-Sync"
                }
            )
            
            # Create session makers
            self.async_session_maker = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            self.sync_session_maker = sessionmaker(
                self.sync_engine,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Set up monitoring
            if self.settings.enable_monitoring:
                self._setup_monitoring()
            
            # Test connection
            await self.health_check()
            
            logger.info("✅ Thenile PostgreSQL connection initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database connection: {e}")
            raise
    
    async def close(self) -> None:
        """Close all database connections"""
        try:
            if self.async_engine:
                await self.async_engine.dispose()
                logger.info("Closed async database connections")
            
            if self.sync_engine:
                self.sync_engine.dispose()
                logger.info("Closed sync database connections")
                
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    @asynccontextmanager
    async def get_session(self, tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic tenant context
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized")
        
        async with self.async_session_maker() as session:
            try:
                # Set tenant context for row-level security
                if tenant_id and self.settings.enable_row_level_security:
                    await session.execute(
                        text("SELECT set_config('uvai.tenant_id', :tenant_id, true)"),
                        {"tenant_id": tenant_id}
                    )
                
                self.connection_stats['active_connections'] += 1
                yield session
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                self.connection_stats['active_connections'] -= 1
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check"""
        health_status = {
            'status': 'unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'connection_pool': {},
            'performance': {},
            'tenant_isolation': {},
            'errors': []
        }
        
        try:
            # Basic connectivity test
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1 as test, NOW() as server_time"))
                test_result = result.fetchone()
                
                if test_result and test_result[0] == 1:
                    health_status['status'] = 'healthy'
                    health_status['server_time'] = str(test_result[1])
            
            # Connection pool statistics
            if self.async_engine:
                pool = self.async_engine.pool
                health_status['connection_pool'] = {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'total_connections': self.connection_stats['total_connections'],
                    'active_connections': self.connection_stats['active_connections'],
                    'failed_connections': self.connection_stats['failed_connections']
                }
            
            # Performance metrics
            health_status['performance'] = {
                'slow_queries': self.connection_stats['slow_queries'],
                'total_queries': self.connection_stats['query_count'],
                'slow_query_threshold': self.settings.slow_query_threshold
            }
            
            # Row-level security test
            if self.settings.enable_row_level_security:
                try:
                    async with self.get_session(tenant_id='health-check') as session:
                        result = await session.execute(
                            text("SELECT current_setting('uvai.tenant_id', true) as tenant_id")
                        )
                        tenant_result = result.fetchone()
                        health_status['tenant_isolation'] = {
                            'enabled': True,
                            'test_tenant_id': tenant_result[0] if tenant_result else None
                        }
                except Exception as e:
                    health_status['tenant_isolation'] = {
                        'enabled': False,
                        'error': str(e)
                    }
                    health_status['errors'].append(f"Tenant isolation test failed: {e}")
            
            self.connection_stats['last_health_check'] = datetime.utcnow()
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['errors'].append(str(e))
            logger.error(f"Database health check failed: {e}")
        
        return health_status
    
    def _setup_monitoring(self) -> None:
        """Set up database monitoring and event listeners"""
        if not self.async_engine:
            return
        
        @event.listens_for(self.async_engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self.connection_stats['total_connections'] += 1
            logger.debug("New database connection established")
        
        @event.listens_for(self.async_engine.sync_engine, "close")
        def on_close(dbapi_connection, connection_record):
            logger.debug("Database connection closed")
        
        @event.listens_for(self.async_engine.sync_engine, "handle_error")
        def on_error(exception_context):
            self.connection_stats['failed_connections'] += 1
            logger.error(f"Database connection error: {exception_context.original_exception}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics"""
        try:
            stats = {}
            
            async with self.get_session() as session:
                # Database size and table statistics
                size_result = await session.execute(text("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        count(*) as table_count
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                size_data = size_result.fetchone()
                
                # Active connections
                conn_result = await session.execute(text("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """))
                conn_data = conn_result.fetchone()
                
                # Query performance
                query_result = await session.execute(text("""
                    SELECT 
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE query LIKE '%uvai%' 
                    ORDER BY total_time DESC 
                    LIMIT 5
                """))
                
                stats = {
                    'database_size': size_data[0] if size_data else 'unknown',
                    'table_count': size_data[1] if size_data else 0,
                    'connections': {
                        'total': conn_data[0] if conn_data else 0,
                        'active': conn_data[1] if conn_data else 0,
                        'idle': conn_data[2] if conn_data else 0
                    },
                    'application_stats': dict(self.connection_stats),
                    'top_queries': [dict(row._mapping) for row in query_result] if query_result else []
                }
                
        except Exception as e:
            logger.warning(f"Could not retrieve performance stats: {e}")
            stats = {'error': str(e)}
        
        return stats

# Global database manager instance
db_manager = DatabaseManager()

async def get_database_session(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """Convenience function to get database session"""
    async with db_manager.get_session(tenant_id=tenant_id) as session:
        yield session

async def init_database() -> None:
    """Initialize database connection"""
    await db_manager.initialize()

async def close_database() -> None:
    """Close database connection"""
    await db_manager.close()

def get_sync_session():
    """Get synchronous session for migrations and admin tasks"""
    if not db_manager.sync_session_maker:
        raise RuntimeError("Database not initialized")
    return db_manager.sync_session_maker()