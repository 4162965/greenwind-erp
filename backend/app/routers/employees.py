from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Employee, User
from ..schemas import EmployeeCreate, EmployeeRead, EmployeeUpdate
from ..security import hash_password


router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


def get_employee(employee_id: int, db: Session) -> Employee:
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    return employee


def sync_employee_login(employee: Employee, password: str | None, db: Session, old_phone: str | None = None):
    """员工登录账号统一使用手机号；员工角色固定为“员工”."""
    if not employee.phone:
        return
    user = db.scalar(select(User).where(User.username == employee.phone))
    if not user and old_phone:
        user = db.scalar(select(User).where(User.username == old_phone))

    if employee.login_enabled and employee.status != "离职":
        if not user:
            user = User(
                username=employee.phone,
                display_name=employee.name,
                role="员工",
                module_permissions=employee.module_permissions or "",
                product_category_permissions=employee.product_category_permissions or "",
                password_hash=hash_password(password or "123456"),
                is_active=True,
            )
            db.add(user)
        else:
            user.username = employee.phone
            user.display_name = employee.name
            user.role = "员工"
            user.module_permissions = employee.module_permissions or ""
            user.product_category_permissions = employee.product_category_permissions or ""
            user.is_active = True
            if password:
                user.password_hash = hash_password(password)
    elif user:
        user.is_active = False


@router.get("")
def list_employees(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Employee.name.like(pattern), Employee.phone.like(pattern), Employee.position.like(pattern), Employee.department.like(pattern)))
    items = db.scalars(select(Employee).where(*filters).order_by(Employee.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(Employee).where(*filters)) or 0
    return {"items": [EmployeeRead.model_validate(item) for item in items], "total": total}


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    values = payload.model_dump(exclude={"login_password"})
    values["role"] = "员工"
    values["business_roles"] = ""
    employee = Employee(**values)
    db.add(employee)
    db.flush()
    sync_employee_login(employee, payload.login_password, db)
    db.commit()
    db.refresh(employee)
    return employee


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    employee = get_employee(employee_id, db)
    old_phone = employee.phone
    values = payload.model_dump(exclude_unset=True)
    password = values.pop("login_password", None)
    values.pop("role", None)
    values.pop("business_roles", None)
    for key, value in values.items():
        setattr(employee, key, value)
    employee.role = "员工"
    employee.business_roles = ""
    sync_employee_login(employee, password, db, old_phone)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    db.delete(get_employee(employee_id, db))
    db.commit()
