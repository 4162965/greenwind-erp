from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import add_operation_log
from ..database import get_db
from ..deps import current_user
from ..models import User
from ..schemas import ChangePasswordRequest, LoginRequest, LoginResponse, UserInfo
from ..security import create_token, hash_password, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


def parse_permissions(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace("，", ",").split(",") if item.strip()]


def to_user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        module_permissions=parse_permissions(user.module_permissions),
        product_category_permissions=parse_permissions(user.product_category_permissions),
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用")
    ip_address = request.client.host if request.client else ""
    add_operation_log(db, user, "系统", "登录", "账号", user.id, user.username, "用户登录系统", ip_address)
    db.commit()
    return LoginResponse(access_token=create_token(user.id), user=to_user_info(user))


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(current_user)):
    return to_user_info(user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "密码修改成功"}
