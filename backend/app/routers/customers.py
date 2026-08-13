from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Customer, CustomerAreaSetting, User
from ..schemas import (
    CustomerAreaSettingCreate,
    CustomerAreaSettingRead,
    CustomerAreaSettingUpdate,
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
)


router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


def get_customer(customer_id: int, db: Session) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


def get_area_setting(setting_id: int, db: Session) -> CustomerAreaSetting:
    item = db.get(CustomerAreaSetting, setting_id)
    if not item:
        raise HTTPException(status_code=404, detail="区域设置不存在")
    return item


@router.get("")
def list_customers(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(
            Customer.name.like(pattern),
            Customer.project_name.like(pattern),
            Customer.area.like(pattern),
            Customer.supervisor_name.like(pattern),
            Customer.supervisor_phone.like(pattern),
            Customer.contact_person.like(pattern),
            Customer.phone.like(pattern),
            Customer.maintainer_name.like(pattern),
            Customer.maintainer_phone.like(pattern),
        ))
    items = db.scalars(select(Customer).where(*filters).order_by(Customer.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(Customer).where(*filters)) or 0
    return {"items": [CustomerRead.model_validate(item) for item in items], "total": total}


@router.get("/area-settings")
def list_area_settings(
    keyword: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    filters = []
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(
            CustomerAreaSetting.area.like(pattern),
            CustomerAreaSetting.supervisor_name.like(pattern),
            CustomerAreaSetting.supervisor_phone.like(pattern),
        ))
    items = db.scalars(select(CustomerAreaSetting).where(*filters).order_by(CustomerAreaSetting.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(CustomerAreaSetting).where(*filters)) or 0
    return {"items": [CustomerAreaSettingRead.model_validate(item) for item in items], "total": total}


@router.post("/area-settings", response_model=CustomerAreaSettingRead, status_code=status.HTTP_201_CREATED)
def create_area_setting(
    payload: CustomerAreaSettingCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    area = payload.area.strip()
    if db.scalar(select(CustomerAreaSetting).where(CustomerAreaSetting.area == area)):
        raise HTTPException(status_code=409, detail="这个区域已经存在")
    item = CustomerAreaSetting(**payload.model_dump())
    item.area = area
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/area-settings/{setting_id}", response_model=CustomerAreaSettingRead)
def update_area_setting(
    setting_id: int,
    payload: CustomerAreaSettingUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    item = get_area_setting(setting_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "area" in values and values["area"]:
        area = values["area"].strip()
        exists = db.scalar(select(CustomerAreaSetting).where(CustomerAreaSetting.area == area, CustomerAreaSetting.id != setting_id))
        if exists:
            raise HTTPException(status_code=409, detail="这个区域已经存在")
        values["area"] = area
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/area-settings/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_area_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    db.delete(get_area_setting(setting_id, db))
    db.commit()


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    customer = get_customer(customer_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    db.delete(get_customer(customer_id, db))
    db.commit()
