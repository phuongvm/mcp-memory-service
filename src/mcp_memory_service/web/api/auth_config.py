# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Authentication Configuration API

Provides endpoint to check available authentication methods.
This allows the frontend to adapt based on server configuration.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from ...config import (
    OAUTH_ENABLED,
    OAUTH_ALLOW_CLIENT_REGISTRATION,
    OAUTH_ALLOW_AUTHORIZATION,
    API_KEY,
    ALLOW_ANONYMOUS_ACCESS
)

router = APIRouter()


class AuthMethod(BaseModel):
    """Authentication method information."""
    id: str
    name: str
    description: str
    enabled: bool
    recommended: bool


class AuthConfigResponse(BaseModel):
    """Authentication configuration response."""
    available_methods: List[AuthMethod]
    oauth_enabled: bool
    api_key_enabled: bool
    anonymous_access_allowed: bool
    
    
@router.get("/auth/config", response_model=AuthConfigResponse, tags=["auth-config"])
async def get_auth_config():
    """
    Get available authentication methods.
    
    Returns configuration that tells the frontend which authentication
    methods are enabled on the server. This allows the UI to show/hide
    options based on security settings.
    
    **Security Note:**
    - When `oauth_client_registration` is disabled, OAuth registration endpoints are not available
    - When `oauth_authorization` is disabled, OAuth authorization flow is not available
    - When both are disabled, only API key authentication is available
    
    Returns:
        AuthConfigResponse: Available authentication methods and configuration
    """
    methods = []
    
    # OAuth Auto Registration (option 1)
    if OAUTH_ENABLED and OAUTH_ALLOW_CLIENT_REGISTRATION and OAUTH_ALLOW_AUTHORIZATION:
        methods.append(AuthMethod(
            id="oauth_auto",
            name="Auto Register & Login",
            description="Automatically register OAuth client and get authorization in one step",
            enabled=True,
            recommended=True
        ))
    
    # OAuth Manual Flow (option 2)
    if OAUTH_ENABLED and OAUTH_ALLOW_CLIENT_REGISTRATION and OAUTH_ALLOW_AUTHORIZATION:
        methods.append(AuthMethod(
            id="oauth_manual",
            name="Manual OAuth Flow",
            description="Step-by-step OAuth client registration and authorization",
            enabled=True,
            recommended=False
        ))
    
    # API Key Authentication (option 3)
    if API_KEY:
        methods.append(AuthMethod(
            id="api_key",
            name="API Key Authentication",
            description="Login with pre-configured API key",
            enabled=True,
            # Recommended if OAuth is disabled, otherwise not recommended
            recommended=not (OAUTH_ENABLED and OAUTH_ALLOW_CLIENT_REGISTRATION and OAUTH_ALLOW_AUTHORIZATION)
        ))
    
    return AuthConfigResponse(
        available_methods=methods,
        oauth_enabled=OAUTH_ENABLED,
        api_key_enabled=bool(API_KEY),
        anonymous_access_allowed=ALLOW_ANONYMOUS_ACCESS
    )

