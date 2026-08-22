from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .models import Employee, Project, ProjectMaintainer, User


FULL_ACCESS_ROLES = {"admin", "管理员", "经理", "老板", "客服", "财务"}
SUPERVISOR_ROLES = {"主管", "经理"}
MAINTAINER_ROLES = {"养护员"}


def role_names(user: User) -> set[str]:
    return {part.strip() for part in (user.role or "").replace("，", ",").split(",") if part.strip()}


def has_full_access(user: User) -> bool:
    roles = role_names(user)
    return bool(roles & FULL_ACCESS_ROLES)


def module_permissions(user: User) -> set[str]:
    return {part.strip() for part in (user.module_permissions or "").replace("，", ",").split(",") if part.strip()}


def product_category_permissions(user: User) -> set[str]:
    return {part.strip() for part in (user.product_category_permissions or "").replace("，", ",").split(",") if part.strip()}


def can_access_product_category(user: User, category: str) -> bool:
    if has_full_access(user):
        return True
    permissions = product_category_permissions(user)
    return (category or "").strip() in permissions


def can_access_module(user: User, permission: str) -> bool:
    if has_full_access(user):
        return True
    permissions = module_permissions(user)
    return not permissions or permission in permissions


def require_module(user: User, permission: str):
    if not can_access_module(user, permission):
        raise HTTPException(status_code=403, detail="无权访问该功能模块")


def is_supervisor(user: User) -> bool:
    roles = role_names(user)
    return bool(roles & SUPERVISOR_ROLES)


def is_maintainer(user: User) -> bool:
    roles = role_names(user)
    return bool(roles & MAINTAINER_ROLES)


def employee_for_user(user: User, db: Session) -> Employee | None:
    return db.scalar(
        select(Employee).where(
            or_(
                Employee.phone == user.username,
                Employee.name == user.display_name,
                Employee.name == user.username,
            )
        )
    )


def accessible_project_ids(user: User, db: Session) -> set[int] | None:
    """Return None for full access; otherwise return the project ids this user can see."""
    if has_full_access(user):
        return None
    employee = employee_for_user(user, db)
    if not employee:
        return set()

    employee_role_text = ",".join(
        str(value or "")
        for value in (employee.position, employee.role, employee.business_roles)
    )
    employee_is_supervisor = any(role in employee_role_text for role in SUPERVISOR_ROLES)
    employee_is_maintainer = any(role in employee_role_text for role in MAINTAINER_ROLES)

    ids: set[int] = set()
    if is_supervisor(user) or employee_is_supervisor:
        supervised = db.scalars(
            select(Project.id).where(or_(Project.supervisor_id == employee.id, Project.customer_service_id == employee.id))
        ).all()
        ids.update(supervised)
    if is_maintainer(user) or employee_is_maintainer or not ids:
        maintained = db.scalars(
            select(ProjectMaintainer.project_id).where(
                ProjectMaintainer.employee_id == employee.id,
                ProjectMaintainer.status == "负责中",
            )
        ).all()
        ids.update(maintained)
    return ids


def can_access_project(user: User, project_id: int | None, db: Session) -> bool:
    if not project_id:
        return has_full_access(user)
    ids = accessible_project_ids(user, db)
    return ids is None or project_id in ids
