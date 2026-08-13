from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token


bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials) if credentials else None
    user = db.get(User, payload.get("sub")) if payload else None
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="登录状态无效或已过期")
    return user

