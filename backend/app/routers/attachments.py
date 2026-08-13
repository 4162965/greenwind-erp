from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..audit import add_operation_log
from ..database import get_db
from ..deps import current_user
from ..models import Attachment, User
from ..schemas import AttachmentCreate, AttachmentRead


router = APIRouter(prefix="/api/v1/attachments", tags=["attachments"])


@router.get("")
def list_attachments(
    keyword: str = Query(default="", max_length=100),
    target_type: str = Query(default="", max_length=64),
    target_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if target_type.strip():
        filters.append(Attachment.target_type == target_type.strip())
    if target_id is not None:
        filters.append(Attachment.target_id == target_id)
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                Attachment.target_type.like(pattern),
                Attachment.target_name.like(pattern),
                Attachment.file_name.like(pattern),
                Attachment.notes.like(pattern),
            )
        )
    items = db.scalars(select(Attachment).where(*filters).order_by(Attachment.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(Attachment).where(*filters)) or 0
    return {"items": [AttachmentRead.model_validate(item) for item in items], "total": total}


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def create_attachment(
    payload: AttachmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not payload.file_name.strip() or not payload.data_url.strip():
        raise HTTPException(status_code=400, detail="附件名称和文件内容不能为空")
    if payload.file_size > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="单个附件不能超过8MB")
    item = Attachment(
        **payload.model_dump(),
        uploader_id=user.id,
        uploader_name=user.display_name or user.username,
    )
    db.add(item)
    db.flush()
    add_operation_log(
        db,
        user,
        module="资料附件",
        action="上传附件",
        target_type=item.target_type,
        target_id=item.target_id,
        target_name=item.target_name or item.file_name,
        detail=item.file_name,
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    item = db.get(Attachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    add_operation_log(
        db,
        user,
        module="资料附件",
        action="删除附件",
        target_type=item.target_type,
        target_id=item.target_id,
        target_name=item.target_name or item.file_name,
        detail=item.file_name,
    )
    db.delete(item)
    db.commit()
