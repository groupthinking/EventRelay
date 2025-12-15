#!/usr/bin/env python3
"""
Alembic Environment Configuration for UVAI Platform
==================================================

Multi-tenant migration environment with comprehensive schema management.
"""

import asyncio
import logging
from logging.config import fileConfig
from typing import Optional

from sqlalchemy import pool, create_engine
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine
from alembic import context

# Path setup for imports
backend_path = Path(__file__).parent.parent

from backend.config.database import DatabaseSettings, Base
from backend.models import *  # Import all models to ensure they're registered

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Configure database settings
db_settings = DatabaseSettings()

# Set the database URL in the config
config.set_main_option("sqlalchemy.url", db_settings.database_url)

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema=None,  # Use default schema
        render_as_batch=False,  # PostgreSQL supports transactional DDL
        transaction_per_migration=True,
        # Custom migration options
        user_module_prefix="uvai_",
        include_name=include_name,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def include_name(name: Optional[str], type_: str, parent_names: dict) -> bool:
    """
    Determine whether to include a name in the migration.
    
    This function is used to filter out certain tables, indexes,
    or other database objects from being included in migrations.
    """
    if type_ == "schema":
        return name in [None, "public"]
    
    # Skip system tables and temp tables
    if name and (name.startswith("pg_") or name.startswith("information_schema") or name.startswith("temp_")):
        return False
    
    return True

def include_object(object, name: Optional[str], type_: str, reflected: bool, compare_to: Optional[object]) -> bool:
    """
    Determine whether to include an object in the migration.
    
    This provides fine-grained control over which objects
    are included in the migration generation.
    """
    # Include all objects by default
    return True

async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    
    # Create async engine
    connectable = create_async_engine(
        db_settings.database_url,
        poolclass=pool.NullPool,  # Don't use connection pooling for migrations
        echo=False,  # Set to True for SQL logging during migrations
        future=True
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()

def do_run_migrations(connection):
    """Run migrations with the provided connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema=None,
        render_as_batch=False,
        transaction_per_migration=True,
        # Custom migration options
        user_module_prefix="uvai_",
        include_name=include_name,
        include_object=include_object,
        # Add custom render functions for better migration generation
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()

def render_item(type_: str, obj, autogen_context):
    """Custom rendering for migration items"""
    
    # Custom rendering for JSONB columns
    if hasattr(obj, 'type') and 'JSONB' in str(obj.type):
        return f"sa.Column({obj.name!r}, postgresql.JSONB(), nullable={obj.nullable})"
    
    # Custom rendering for UUID columns with server defaults
    if hasattr(obj, 'type') and 'UUID' in str(obj.type):
        if hasattr(obj, 'server_default') and obj.server_default:
            return f"sa.Column({obj.name!r}, postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable={obj.nullable})"
    
    # Default rendering
    return False

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Use asyncio to run async migrations
    asyncio.run(run_async_migrations())

# Setup row-level security policies
def setup_rls_policies(connection):
    """
    Set up row-level security policies for multi-tenant architecture
    """
    
    # Enable RLS on tenant-aware tables
    tables_with_rls = [
        'users', 'user_profiles', 'user_sessions', 'user_activities',
        'videos', 'video_metadata', 'video_analyses', 'video_processing_jobs',
        'learning_outcomes', 'learning_paths', 'learning_progress',
        'cache_entries', 'audit_logs', 'security_events',
        'analytics_events', 'performance_metrics', 'usage_statistics'
    ]
    
    for table in tables_with_rls:
        try:
            connection.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            
            # Create policy for tenant isolation
            connection.execute(f"""
                CREATE POLICY {table}_tenant_isolation ON {table}
                USING (tenant_id = current_setting('uvai.tenant_id')::text);
            """)
            
            logging.info(f"Enabled RLS for table: {table}")
        except Exception as e:
            logging.warning(f"Could not enable RLS for {table}: {e}")

# Custom migration context setup
def setup_migration_context():
    """Setup custom migration context with UVAI-specific configurations"""
    
    # Set up custom comparison functions
    def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
        """Custom type comparison for better migration detection"""
        
        # Handle JSONB type comparisons
        if "JSONB" in str(metadata_type) and "json" in str(inspected_type).lower():
            return False  # These are equivalent
        
        # Handle UUID type comparisons
        if "UUID" in str(metadata_type) and "uuid" in str(inspected_type).lower():
            return False  # These are equivalent
        
        # Default comparison
        return None
    
    return {
        "compare_type": compare_type,
        "compare_server_default": True,
        "include_schemas": True,
    }

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()