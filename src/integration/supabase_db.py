"""
Supabase - Database & Auth for Generated Apps
-----------------------------------------------
PostgreSQL database, authentication, and realtime subscriptions.
"""

import os
import asyncio
import httpx
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class QueryResult:
    """Result from a Supabase query."""
    data: list[dict]
    count: Optional[int] = None
    error: Optional[str] = None


@dataclass
class AuthUser:
    """Supabase auth user."""
    id: str
    email: str
    created_at: str
    email_confirmed: bool


class SupabaseDBService:
    """Supabase database and auth service."""
    
    def __init__(
        self,
        project_url: Optional[str] = None,
        service_key: Optional[str] = None,
        anon_key: Optional[str] = None
    ):
        self.project_url = project_url or os.environ.get("SUPABASE_URL")
        self.service_key = service_key or os.environ.get("SUPABASE_SERVICE_KEY")
        self.anon_key = anon_key or os.environ.get("SUPABASE_ANON_KEY")
        
        if not self.project_url:
            raise ValueError("SUPABASE_URL required")
        
        # Use service key for admin ops, anon key for client ops
        self.key = self.service_key or self.anon_key
        if not self.key:
            raise ValueError("SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY required")
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
        )
    
    # ============ Database Operations ============
    
    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[dict] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None
    ) -> QueryResult:
        """Select data from a table."""
        
        url = f"{self.project_url}/rest/v1/{table}"
        params = {"select": columns}
        
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        
        response = await self.client.get(url, params=params)
        
        if response.status_code >= 400:
            return QueryResult(data=[], error=response.text)
        
        return QueryResult(data=response.json())
    
    async def insert(
        self,
        table: str,
        data: dict | list[dict]
    ) -> QueryResult:
        """Insert data into a table."""
        
        url = f"{self.project_url}/rest/v1/{table}"
        payload = data if isinstance(data, list) else [data]
        
        response = await self.client.post(url, json=payload)
        
        if response.status_code >= 400:
            return QueryResult(data=[], error=response.text)
        
        return QueryResult(data=response.json())
    
    async def update(
        self,
        table: str,
        data: dict,
        filters: dict
    ) -> QueryResult:
        """Update data in a table."""
        
        url = f"{self.project_url}/rest/v1/{table}"
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        
        response = await self.client.patch(url, params=params, json=data)
        
        if response.status_code >= 400:
            return QueryResult(data=[], error=response.text)
        
        return QueryResult(data=response.json())
    
    async def delete(
        self,
        table: str,
        filters: dict
    ) -> QueryResult:
        """Delete data from a table."""
        
        url = f"{self.project_url}/rest/v1/{table}"
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        
        response = await self.client.delete(url, params=params)
        
        if response.status_code >= 400:
            return QueryResult(data=[], error=response.text)
        
        return QueryResult(data=response.json() if response.text else [])
    
    async def rpc(
        self,
        function_name: str,
        params: Optional[dict] = None
    ) -> Any:
        """Call a Postgres function."""
        
        url = f"{self.project_url}/rest/v1/rpc/{function_name}"
        response = await self.client.post(url, json=params or {})
        response.raise_for_status()
        return response.json()
    
    # ============ Auth Operations ============
    
    async def sign_up(
        self,
        email: str,
        password: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """Sign up a new user."""
        
        url = f"{self.project_url}/auth/v1/signup"
        payload = {"email": email, "password": password}
        if metadata:
            payload["data"] = metadata
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def sign_in(
        self,
        email: str,
        password: str
    ) -> dict:
        """Sign in a user."""
        
        url = f"{self.project_url}/auth/v1/token"
        params = {"grant_type": "password"}
        payload = {"email": email, "password": password}
        
        response = await self.client.post(url, params=params, json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_user(self, access_token: str) -> AuthUser:
        """Get user details from access token."""
        
        url = f"{self.project_url}/auth/v1/user"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        return AuthUser(
            id=data["id"],
            email=data["email"],
            created_at=data["created_at"],
            email_confirmed=data.get("email_confirmed_at") is not None
        )
    
    async def sign_out(self, access_token: str) -> bool:
        """Sign out a user."""
        
        url = f"{self.project_url}/auth/v1/logout"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await self.client.post(url, headers=headers)
        return response.status_code == 204
    
    # ============ Storage Operations ============
    
    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_content: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """Upload a file to storage."""
        
        url = f"{self.project_url}/storage/v1/object/{bucket}/{path}"
        headers = {"Content-Type": content_type}
        
        response = await self.client.post(
            url,
            headers=headers,
            content=file_content
        )
        response.raise_for_status()
        return f"{self.project_url}/storage/v1/object/public/{bucket}/{path}"
    
    async def get_public_url(self, bucket: str, path: str) -> str:
        """Get public URL for a file."""
        return f"{self.project_url}/storage/v1/object/public/{bucket}/{path}"
    
    # ============ Schema Generation ============
    
    @staticmethod
    def generate_schema_sql(app_type: str = "saas") -> str:
        """Generate SQL schema for generated apps."""
        
        base_schema = '''
-- Users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can read/update their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);
'''
        
        if app_type == "saas":
            base_schema += '''
-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) NOT NULL,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT DEFAULT 'inactive',
    plan TEXT DEFAULT 'free',
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own subscription" ON subscriptions
    FOR SELECT USING (auth.uid() = user_id);
'''
        
        return base_schema
    
    async def close(self):
        await self.client.aclose()
