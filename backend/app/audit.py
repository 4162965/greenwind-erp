from sqlalchemy.orm import Session

from .models import OperationLog, User


def add_operation_log(
    db: Session,
    user: User | None,
    module: str,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    target_name: str = "",
    detail: str = "",
    ip_address: str = "",
):
    db.add(
        OperationLog(
            user_id=user.id if user else None,
            username=user.username if user else "",
            display_name=user.display_name if user else "",
            module=module,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            detail=detail,
            ip_address=ip_address,
        )
    )
