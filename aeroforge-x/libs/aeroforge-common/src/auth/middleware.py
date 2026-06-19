from __future__ import annotations

from jose import JWTError, jwt

from fastapi import HTTPException, Request

from .models import AeroForgeRole, ROLE_PERMISSIONS, AuthUser, KeycloakSettings

_settings = KeycloakSettings()


async def decode_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            key=_settings.keycloak_client_secret,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def auth_middleware(request: Request, call_next):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        request.state.user = None
        response = await call_next(request)
        return response

    token = auth_header.split(" ", 1)[1]
    try:
        payload = await decode_jwt(token)
    except HTTPException:
        request.state.user = None
        response = await call_next(request)
        return response

    realm_roles = payload.get("realm_access", {}).get("roles", [])
    aero_roles = [r for r in realm_roles if r in [e.value for e in AeroForgeRole]]

    permissions: list[str] = []
    for role in aero_roles:
        permissions.extend(ROLE_PERMISSIONS.get(role, []))

    tenant_id = payload.get("tenant_id", "")
    tenant_code = payload.get("tenant_code", "")

    request.state.user = AuthUser(
        user_id=payload.get("sub", ""),
        username=payload.get("preferred_username", ""),
        roles=aero_roles,
        permissions=list(set(permissions)),
        tenant_id=tenant_id,
        tenant_code=tenant_code,
    )

    response = await call_next(request)
    return response