import os
import time
import base64
import hmac
import binascii
import json
import hashlib
import urllib.parse
from typing import Dict, List, Optional
from pydantic import BaseModel

class LookerEmbedUser(BaseModel):
    """Configuration for a multi-tenant Looker user"""
    external_user_id: str
    first_name: str
    last_name: str
    permissions: List[str] = ["access_data", "see_looks", "see_user_dashboards", "explore"]
    models: List[str] = ["uvai_event_models"]
    group_ids: List[int] = []
    external_group_id: str = ""
    user_attributes: Dict[str, str] = {}
    access_filters: Dict[str, Dict[str, str]] = {}

class LookerEmbeddedService:
    """
    Service for generating secure, multi-tenant Looker Embedded URLs.
    This is the Google Cloud equivalent to Amazon QuickSight Embedded.
    It uses SSO Embedding to enforce Row-Level Security (RLS) per tenant.
    """
    
    def __init__(self):
        # In a real environment, these come from Secret Manager / environment vars
        self.looker_host = os.getenv("LOOKER_HOST", "looker.example.com")
        self.looker_secret = os.getenv("LOOKER_EMBED_SECRET", "super_secret_embed_key")

    def _sign_embed_url(self, url: str) -> str:
        """Sign the URL using HMAC-SHA1"""
        secret_bytes = self.looker_secret.encode('utf-8')
        url_bytes = url.encode('utf-8')
        signature = hmac.new(secret_bytes, url_bytes, hashlib.sha1).digest()
        return base64.b64encode(signature).decode('utf-8').strip()

    def generate_sso_url(
        self, 
        target_url: str, 
        user: LookerEmbedUser, 
        session_length: int = 3600
    ) -> str:
        """
        Generate a signed URL for a specific tenant user.
        
        Args:
            target_url: The path to the dashboard (e.g., /embed/dashboards/1)
            user: LookerEmbedUser configuration containing tenant IDs in user_attributes
            session_length: Duration in seconds for the session
            
        Returns:
            str: Fully signed URL ready for an iframe
        """
        # 1. Prepare base elements
        nonce = os.urandom(16).hex()
        current_time = int(time.time())
        
        # 2. Convert lists/dicts to JSON strings
        models_json = json.dumps(user.models)
        permissions_json = json.dumps(user.permissions)
        group_ids_json = json.dumps(user.group_ids)
        user_attributes_json = json.dumps(user.user_attributes)
        access_filters_json = json.dumps(user.access_filters)

        # 3. Construct signature payload
        signature_payload = [
            self.looker_host,
            target_url,
            nonce,
            str(current_time),
            str(session_length),
            user.external_user_id,
            permissions_json,
            models_json,
            group_ids_json,
            user.external_group_id,
            user_attributes_json,
            access_filters_json
        ]
        
        string_to_sign = "\n".join(signature_payload)
        signature = self._sign_embed_url(string_to_sign)

        # 4. Construct URL parameters
        query_params = {
            "nonce": nonce,
            "time": current_time,
            "session_length": session_length,
            "external_user_id": user.external_user_id,
            "permissions": permissions_json,
            "models": models_json,
            "access_filters": access_filters_json,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "group_ids": group_ids_json,
            "external_group_id": user.external_group_id,
            "user_attributes": user_attributes_json,
            "force_logout_login": "true",
            "signature": signature
        }

        # 5. Build final URL
        query_string = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
        return f"https://{self.looker_host}{target_url}?{query_string}"

    def get_tenant_dashboard_url(
        self, 
        dashboard_id: str, 
        tenant_id: str, 
        user_id: str,
        user_email: str
    ) -> str:
        """
        High-level wrapper to generate a dashboard URL strictly filtered to a single tenant.
        This enforces the multi-tenant Row-Level Security architecture.
        """
        # Split email for dummy name generation if needed
        name_parts = user_email.split('@')[0].split('.')
        first_name = name_parts[0].capitalize()
        last_name = name_parts[1].capitalize() if len(name_parts) > 1 else "User"

        user_config = LookerEmbedUser(
            external_user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            # Core mechanism for Multi-tenancy: passing tenant_id to user_attributes
            # Looker models will use {{ _user_attributes['tenant_id'] }} in the SQL WHERE clause
            user_attributes={"tenant_id": tenant_id},
            models=["uvai_multi_tenant_model"],
            permissions=["access_data", "see_looks", "see_user_dashboards", "explore"]
        )

        return self.generate_sso_url(
            target_url=f"/embed/dashboards/{dashboard_id}",
            user=user_config
        )
