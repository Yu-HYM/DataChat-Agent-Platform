#!/usr/bin/env python3
# app/auth.py —— JWT 鉴权
import time
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET = "change-me-in-prod"
bearer = HTTPBearer(auto_error=False)

def make_token(user: str) -> str:
    return jwt.encode({"sub": user, "exp": int(time.time()) + 7200},
                      SECRET, algorithm="HS256")

def verify(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    if cred is None:
        raise HTTPException(401, "缺少 token")
    try:
        return jwt.decode(cred.credentials, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token 过期")
    except jwt.PyJWTError:
        raise HTTPException(401, "token 无效")
