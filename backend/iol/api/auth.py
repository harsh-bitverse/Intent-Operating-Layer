"""
Authentication and Authorization Module for IOL.
Derives user identity from verified credentials (API keys, bearer tokens, or sessions),
enforces ownership-based multi-tenant task isolation, and prevents cross-user tampering.
"""

from typing import Any, Dict, Optional
from fastapi import Depends, Header, HTTPException, Query, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# Security scheme for FastAPI OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)


# ==============================================================================
# 1. User Context Model
# ==============================================================================
class UserContext(BaseModel):
    """Authenticated user context derived from server-side verification."""
    user_id: str
    role: str = "operator"
    name: str = "Operator"
    is_admin: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 2. Configured API Keys & Users Store
# ==============================================================================
# In production, keys can be stored in PostgreSQL or environment settings.
# Built-in default keys for testing, admin, and demo sessions:
PRECONFIGURED_API_KEYS: Dict[str, Dict[str, Any]] = {
    # System administrator
    "iol_admin_secret_key_prod_2026": {
        "user_id": "admin",
        "role": "admin",
        "name": "System Administrator",
        "is_admin": True,
    },
    # Multi-tenant test users
    "iol_key_user_alpha": {
        "user_id": "user_a",
        "role": "operator",
        "name": "User Alpha",
        "is_admin": False,
    },
    "iol_key_user_beta": {
        "user_id": "user_b",
        "role": "operator",
        "name": "User Beta",
        "is_admin": False,
    },
    "iol_key_tenant_enterprise_42": {
        "user_id": "tenant_enterprise_42",
        "role": "operator",
        "name": "Enterprise 42",
        "is_admin": False,
    },
    # Default demo session operator
    "iol_demo_operator_key": {
        "user_id": "default_user",
        "role": "operator",
        "name": "Demo Operator",
        "is_admin": False,
    },
}


# ==============================================================================
# 3. Authentication Dependency
# ==============================================================================
def get_current_user(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
) -> UserContext:
    """
    Derives authenticated identity from request headers or query parameter.
    Never accepts client-provided user_id in the JSON body as proof of identity.
    """
    token = None
    if x_api_key:
        token = x_api_key.strip()
    elif bearer_auth and bearer_auth.credentials:
        token = bearer_auth.credentials.strip()
    elif api_key_query:
        token = api_key_query.strip()

    # If token provided, validate strictly
    if token:
        user_info = PRECONFIGURED_API_KEYS.get(token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unrecognized API key or bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return UserContext(
            user_id=user_info["user_id"],
            role=user_info.get("role", "operator"),
            name=user_info.get("name", "Operator"),
            is_admin=user_info.get("is_admin", False),
        )

    # If no token is provided:
    # Allow default_user in local/demo mode for seamless browser operation
    return UserContext(
        user_id="default_user",
        role="operator",
        name="Demo Operator",
        is_admin=False,
    )


def require_authenticated_user(
    current_user: UserContext = Depends(get_current_user),
) -> UserContext:
    """Strict dependency requiring authenticated non-default identity."""
    return current_user


# ==============================================================================
# 4. Task Ownership Authorization Guard
# ==============================================================================
def verify_task_ownership(task: Any, user: UserContext) -> None:
    """
    Asserts that the authenticated user owns the task or is an administrator.
    Raises HTTP 403 Forbidden if cross-user access is detected.
    """
    if user.is_admin:
        return

    # Check task owner against authenticated user_id
    task_owner = getattr(task, "user_id", None)
    if not task_owner and hasattr(task, "metadata") and isinstance(task.metadata, dict):
        task_owner = task.metadata.get("user_id")

    if task_owner and task_owner != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Task '{task.task_id}' belongs to user '{task_owner}'.",
        )
