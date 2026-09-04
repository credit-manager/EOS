"""Authentication adapter shared by test and production modes."""
import os
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


def _is_production(): return os.getenv("EOS_AUTH_MODE","test").lower()=="production"

async def get_current_user(request:Request,credentials:HTTPAuthorizationCredentials=Depends(HTTPBearer(auto_error=False)))->dict:
    if credentials is None:raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Authentication required",headers={"WWW-Authenticate":"Bearer"})
    if _is_production():
        from core.production_auth import _get_secret_key,verify_token
        try:_get_secret_key()
        except ValueError as exc:raise HTTPException(500,detail="Authentication configuration error") from exc
        payload=verify_token(credentials.credentials)
    else:
        from core.auth import verify_test_token
        payload=verify_test_token(credentials.credentials)
    if payload.get("type") not in (None,"access"):
        raise HTTPException(status_code=401,detail="Invalid access token type")
    user_id,tenant_id=payload.get("sub"),payload.get("tenant_id")
    if user_id is None:raise HTTPException(401,"Token missing user ID")
    if tenant_id is None:raise HTTPException(401,"Token missing tenant ID")
    tenant_id=str(tenant_id).lower()
    user={"id":str(user_id),"tenant_id":tenant_id,"email":payload.get("email"),"roles":payload.get("roles",[])}
    request.state.user=user;request.state.tenant_id=tenant_id
    from database import current_tenant_id
    current_tenant_id.set(tenant_id)
    return user

async def optional_get_current_user(request:Request,credentials:HTTPAuthorizationCredentials|None=Depends(HTTPBearer(auto_error=False)))->dict|None:
    if credentials is None:return None
    return await get_current_user(request,credentials)
