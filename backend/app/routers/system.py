from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..audit import add_operation_log
from ..database import get_db
from ..deps import current_user
from ..models import OperationLog, User
from ..permissions import require_module
from ..schemas import OperationLogRead, UserAccountCreate, UserAccountRead, UserAccountUpdate
from ..security import hash_password


router = APIRouter(prefix="/api/v1/system", tags=["system"])


def client_ip(request: Request | None) -> str:
    if not request or not request.client:
        return ""
    return request.client.host or ""


def get_account(user_id: int, db: Session) -> User:
    account = db.get(User, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


@router.get("/users")
def list_users(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "system")
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(User.username.like(pattern), User.display_name.like(pattern), User.role.like(pattern)))
    items = db.scalars(select(User).where(*filters).order_by(User.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    return {"items": [UserAccountRead.model_validate(item) for item in items], "total": total}


@router.post("/users", response_model=UserAccountRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserAccountCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "system")
    username = payload.username.strip()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="账号已存在")
    account = User(
        username=username,
        display_name=payload.display_name.strip(),
        role=payload.role.strip() or "员工",
        module_permissions=payload.module_permissions.strip(),
        product_category_permissions=payload.product_category_permissions.strip(),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(account)
    db.flush()
    add_operation_log(
        db,
        user,
        "系统管理",
        "新增账号",
        "账号",
        account.id,
        account.username,
        f"新增账号 {account.username}（{account.display_name}）",
        client_ip(request),
    )
    db.commit()
    db.refresh(account)
    return account


@router.put("/users/{user_id}", response_model=UserAccountRead)
def update_user(
    user_id: int,
    payload: UserAccountUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "system")
    account = get_account(user_id, db)
    values = payload.model_dump(exclude_unset=True)
    password = values.pop("password", None)
    changed = []
    for key, value in values.items():
        setattr(account, key, value.strip() if isinstance(value, str) else value)
        changed.append(key)
    if password:
        account.password_hash = hash_password(password)
        changed.append("password")
    add_operation_log(
        db,
        user,
        "系统管理",
        "修改账号",
        "账号",
        account.id,
        account.username,
        f"修改账号 {account.username}；字段：{'、'.join(changed) if changed else '无'}",
        client_ip(request),
    )
    db.commit()
    db.refresh(account)
    return account


@router.get("/operation-logs")
def list_operation_logs(
    keyword: str = Query(default="", max_length=100),
    module: str = Query(default="", max_length=64),
    action: str = Query(default="", max_length=64),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "system")
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                OperationLog.username.like(pattern),
                OperationLog.display_name.like(pattern),
                OperationLog.target_name.like(pattern),
                OperationLog.detail.like(pattern),
            )
        )
    if module.strip():
        filters.append(OperationLog.module == module.strip())
    if action.strip():
        filters.append(OperationLog.action == action.strip())
    items = db.scalars(select(OperationLog).where(*filters).order_by(OperationLog.id.desc()).limit(limit)).all()
    total = db.scalar(select(func.count()).select_from(OperationLog).where(*filters)) or 0
    return {"items": [OperationLogRead.model_validate(item) for item in items], "total": total}
