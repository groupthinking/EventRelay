import os
import time
import json
import base64
import hmac
import hashlib
import binascii
from typing import Dict, Any, Optional
import urllib.parse

class LookerEmbedService:
    """
    Service for generating Secure SSO URLs for Google Cloud Looker.
    This provides multi-tenant, self-service reporting capabilities equivalent 
    to Amazon QuickSight Embedded Dashboards.
    """
    def __init__(self, host: Optional[str] = None, secret: Optional[str] = None):
        # Looker instance host (e.g., 'looker.yourdomain.com')
        self.host = host or os.getenv("LOOKER_HOST", "looker.example.com")
        # Embed secret from Looker Admin panel
        self.secret = secret or os.getenv("LOOKER_EMBED_SECRET", "dummy_secret_for_dev")

    def generate_sso_url(self, target_url: str, user_id: str,
                         first_name: str, last_name: str,
                         group_ids: list, external_group_id: str,
                         permissions: list, models: list,
                         user_attributes: Dict[str, Any],
                         session_length: int = 900) -> str:
        """
        Generate a signed URL for Looker Embed SSO.
        """
        path = f"/login/embed/{urllib.parse.quote_plus(target_url)}"
        
        # Prepare parameters
        nonce = binascii.hexlify(os.urandom(16)).decode('utf-8')
        time_str = str(int(time.time()))
        
        json_permissions = json.dumps(permissions)
        json_models = json.dumps(models)
        json_group_ids = json.dumps(group_ids)
        json_user_attributes = json.dumps(user_attributes)

        # Looker Signature Generation
        string_to_sign = "
".join([
            self.host,
            path,
            nonce,
            time_str,
            session_length,
            user_id,
            external_group_id,
            json_permissions,
            json_models,
            json_group_ids,
            json_user_attributes
        ])

        signer = hmac.new(
            bytearray(self.secret, "UTF-8"),
            string_to_sign.encode("UTF-8"),
            hashlib.sha1
        )
        signature = base64.b64encode(signer.digest()).decode("utf-8")

        # Construct final query parameters
        query_params = {
            "nonce": nonce,
            "time": time_str,
            "session_length": session_length,
            "external_user_id": user_id,
            "permissions": json_permissions,
            "models": json_models,
            "access_filters": "{}",
            "first_name": first_name,
            "last_name": last_name,
            "group_ids": json_group_ids,
            "external_group_id": external_group_id,
            "user_attributes": json_user_attributes,
            "force_logout_login": "true",
            "signature": signature
        }

        query_string = urllib.parse.urlencode(query_params)
        return f"https://{self.host}{path}?{query_string}"

# Example Usage Endpoint Handler
def get_tenant_dashboard_url(tenant_id: str, user_email: str) -> str:
    """
    Generates a secure multi-tenant Looker dashboard embed URL.
    Tenant isolation is enforced via user_attributes.
    """
    service = LookerEmbedService()
    # Assume dashboard 123 is the main analytics dashboard
    target_dashboard = "/embed/dashboards/123"
    
    # Enforce multi-tenant data access by injecting tenant_id into user attributes
    # The Looker model (SQL/AlloyDB) will filter all queries where tenant_id matches.
    user_attrs = {
        "tenant_id": tenant_id
    }
    
    return service.generate_sso_url(
        target_url=target_dashboard,
        user_id=user_email,
        first_name="App",
        last_name="User",
        group_ids=[1], # Default 'Viewer' group in Looker
        external_group_id=f"tenant_{tenant_id}",
        permissions=["access_data", "see_looks", "see_user_dashboards", "explore"],
        models=["uvai_analytics"], # The Looker project model
        user_attributes=user_attrs
    )
