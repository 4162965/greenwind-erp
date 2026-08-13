from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import (
    Contract,
    Customer,
    Employee,
    Product,
    ProductVariant,
    Project,
    ProjectContact,
    ProjectLocation,
    ProjectMaintainer,
    ProjectPlant,
    ProjectPlantChange,
    ProjectSalary,
    User,
)
from ..permissions import accessible_project_ids, can_access_project, require_module
from ..schemas import (
    ContractCreate,
    ContractRead,
    ContractUpdate,
    ProjectContactCreate,
    ProjectContactRead,
    ProjectCreate,
    ProjectLocationCreate,
    ProjectLocationRead,
    ProjectMaintainerCreate,
    ProjectMaintainerRead,
    ProjectPlantCreate,
    ProjectPlantChangeRead,
    ProjectPlantRead,
    ProjectPlantUpdate,
    ProjectRead,
    ProjectSalaryCreate,
    ProjectSalaryRead,
    ProjectSalaryUpdate,
    ProjectUpdate,
)


router = APIRouter(prefix="/api/v1", tags=["projects"])


def require(model, record_id: int, db: Session, detail: str):
    record = db.get(model, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=detail)
    return record


def validate_project_refs(customer_id: int, supervisor_id: int | None, customer_service_id: int | None, db: Session):
    require(Customer, customer_id, db, "客户不存在")
    if supervisor_id:
        require(Employee, supervisor_id, db, "主管不存在")
    if customer_service_id:
        require(Employee, customer_service_id, db, "客服不存在")


def project_payload(project: Project, db: Session):
    data = ProjectRead.model_validate(project).model_dump()
    customer = db.get(Customer, project.customer_id)
    supervisor = db.get(Employee, project.supervisor_id) if project.supervisor_id else None
    customer_service = db.get(Employee, project.customer_service_id) if project.customer_service_id else None
    data.update(
        customer_name=customer.name if customer else "",
        supervisor_name=supervisor.name if supervisor else "",
        customer_service_name=customer_service.name if customer_service else "",
    )
    return data


@router.get("/projects")
def list_projects(
    keyword: str = Query(default="", max_length=100),
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "projects")
    filters = []
    project_ids = accessible_project_ids(user, db)
    if project_ids is not None:
        if not project_ids:
            return {"items": [], "total": 0}
        filters.append(Project.id.in_(project_ids))
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Project.code.like(pattern), Project.name.like(pattern), Project.address.like(pattern)))
    if customer_id:
        filters.append(Project.customer_id == customer_id)
    projects = db.scalars(select(Project).where(*filters).order_by(Project.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(Project).where(*filters)) or 0
    return {"items": [project_payload(item, db) for item in projects], "total": total}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if db.scalar(select(Project).where(Project.code == payload.code)):
        raise HTTPException(status_code=409, detail="项目编码已存在")
    validate_project_refs(payload.customer_id, payload.supervisor_id, payload.customer_service_id, db)
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_payload(project, db)


@router.put("/projects/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该项目")
    project = require(Project, project_id, db, "项目不存在")
    values = payload.model_dump(exclude_unset=True)
    if "code" in values and db.scalar(select(Project).where(Project.code == values["code"], Project.id != project_id)):
        raise HTTPException(status_code=409, detail="项目编码已存在")
    validate_project_refs(
        values.get("customer_id", project.customer_id),
        values.get("supervisor_id", project.supervisor_id),
        values.get("customer_service_id", project.customer_service_id),
        db,
    )
    for key, value in values.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project_payload(project, db)


@router.get("/projects/{project_id}/contacts")
def list_contacts(project_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权查看该项目")
    require(Project, project_id, db, "项目不存在")
    items = db.scalars(select(ProjectContact).where(ProjectContact.project_id == project_id).order_by(ProjectContact.priority, ProjectContact.id)).all()
    return {"items": [ProjectContactRead.model_validate(item) for item in items], "total": len(items)}


@router.post("/projects/{project_id}/contacts", response_model=ProjectContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(project_id: int, payload: ProjectContactCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该项目")
    require(Project, project_id, db, "项目不存在")
    item = ProjectContact(project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/project-contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    db.delete(require(ProjectContact, contact_id, db, "联系人不存在"))
    db.commit()


@router.get("/projects/{project_id}/locations")
def list_locations(project_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权查看该项目")
    require(Project, project_id, db, "项目不存在")
    items = db.scalars(select(ProjectLocation).where(ProjectLocation.project_id == project_id).order_by(ProjectLocation.sort_order, ProjectLocation.id)).all()
    return {"items": [ProjectLocationRead.model_validate(item) for item in items], "total": len(items)}


@router.post("/projects/{project_id}/locations", response_model=ProjectLocationRead, status_code=status.HTTP_201_CREATED)
def create_location(project_id: int, payload: ProjectLocationCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该项目")
    require(Project, project_id, db, "项目不存在")
    if payload.location_type not in {"楼层", "区域"}:
        raise HTTPException(status_code=400, detail="位置类型只支持楼层和区域")
    if payload.location_type == "楼层" and payload.parent_id:
        raise HTTPException(status_code=400, detail="楼层不能设置上级位置")
    if payload.location_type == "区域" and not payload.parent_id:
        raise HTTPException(status_code=400, detail="区域必须选择所属楼层")
    if payload.parent_id:
        parent = require(ProjectLocation, payload.parent_id, db, "上级位置不存在")
        if parent.project_id != project_id:
            raise HTTPException(status_code=400, detail="上级位置不属于当前项目")
        if parent.location_type != "楼层":
            raise HTTPException(status_code=400, detail="区域的上级位置必须是楼层")
    item = ProjectLocation(project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/project-locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    item = require(ProjectLocation, location_id, db, "位置不存在")
    has_children = db.scalar(select(func.count()).select_from(ProjectLocation).where(ProjectLocation.parent_id == location_id))
    has_plants = db.scalar(select(func.count()).select_from(ProjectPlant).where(ProjectPlant.location_id == location_id))
    if has_children or has_plants:
        raise HTTPException(status_code=409, detail="该位置存在下级位置或植物，不能删除")
    db.delete(item)
    db.commit()


@router.get("/projects/{project_id}/maintainers")
def list_maintainers(project_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权查看该项目")
    require(Project, project_id, db, "项目不存在")
    items = db.scalars(select(ProjectMaintainer).where(ProjectMaintainer.project_id == project_id).order_by(ProjectMaintainer.is_primary.desc(), ProjectMaintainer.id)).all()
    result = []
    for item in items:
        data = ProjectMaintainerRead.model_validate(item).model_dump()
        employee = db.get(Employee, item.employee_id)
        data.update(employee_name=employee.name if employee else "", employee_phone=employee.phone if employee else "")
        result.append(data)
    return {"items": result, "total": len(result)}


@router.post("/projects/{project_id}/maintainers", status_code=status.HTTP_201_CREATED)
def create_maintainer(project_id: int, payload: ProjectMaintainerCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该项目")
    require(Project, project_id, db, "项目不存在")
    employee = require(Employee, payload.employee_id, db, "员工不存在")
    duplicate = db.scalar(select(ProjectMaintainer).where(ProjectMaintainer.project_id == project_id, ProjectMaintainer.employee_id == payload.employee_id, ProjectMaintainer.status == "负责中"))
    if duplicate:
        raise HTTPException(status_code=409, detail="该养护员已经在当前项目负责")
    item = ProjectMaintainer(project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    data = ProjectMaintainerRead.model_validate(item).model_dump()
    data.update(employee_name=employee.name, employee_phone=employee.phone)
    return data


@router.delete("/project-maintainers/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintainer(assignment_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    item = require(ProjectMaintainer, assignment_id, db, "养护员分配不存在")
    item.status = "已结束"
    db.commit()


def contract_payload(item: Contract, db: Session):
    data = ContractRead.model_validate(item).model_dump()
    project = db.get(Project, item.project_id)
    data["project_name"] = project.name if project else ""
    return data


@router.get("/contracts")
def list_contracts(project_id: int | None = None, keyword: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "finance")
    filters = []
    if project_id:
        if not can_access_project(user, project_id, db):
            raise HTTPException(status_code=403, detail="无权查看该项目合同")
        filters.append(Contract.project_id == project_id)
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Contract.contract_no.like(pattern), Contract.name.like(pattern)))
    items = db.scalars(select(Contract).where(*filters).order_by(Contract.id.desc())).all()
    return {"items": [contract_payload(item, db) for item in items], "total": len(items)}


@router.post("/contracts", status_code=status.HTTP_201_CREATED)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "finance")
    if not can_access_project(user, payload.project_id, db):
        raise HTTPException(status_code=403, detail="无权为该项目建立合同")
    require(Project, payload.project_id, db, "项目不存在")
    if payload.end_date < payload.effective_date:
        raise HTTPException(status_code=400, detail="合同结束日期不能早于生效日期")
    if db.scalar(select(Contract).where(Contract.contract_no == payload.contract_no)):
        raise HTTPException(status_code=409, detail="合同编号已存在")
    values = payload.model_dump()
    values["billing_start_date"] = values["billing_start_date"] or values["effective_date"]
    item = Contract(**values)
    db.add(item)
    db.commit()
    db.refresh(item)
    return contract_payload(item, db)


@router.put("/contracts/{contract_id}")
def update_contract(contract_id: int, payload: ContractUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "finance")
    item = require(Contract, contract_id, db, "合同不存在")
    if not can_access_project(user, item.project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该合同")
    values = payload.model_dump(exclude_unset=True)
    if "project_id" in values:
        require(Project, values["project_id"], db, "项目不存在")
    if "contract_no" in values and db.scalar(select(Contract).where(Contract.contract_no == values["contract_no"], Contract.id != contract_id)):
        raise HTTPException(status_code=409, detail="合同编号已存在")
    effective = values.get("effective_date", item.effective_date)
    end = values.get("end_date", item.end_date)
    if end < effective:
        raise HTTPException(status_code=400, detail="合同结束日期不能早于生效日期")
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return contract_payload(item, db)


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    item = require(Contract, contract_id, db, "合同不存在")
    db.delete(item)
    db.commit()


def plant_payload(item: ProjectPlant, db: Session):
    data = ProjectPlantRead.model_validate(item).model_dump()
    project = db.get(Project, item.project_id)
    location = db.get(ProjectLocation, item.location_id)
    product = db.get(Product, item.product_id)
    variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.product_id == item.product_id,
            ProductVariant.specification == item.specification,
        )
    ) if item.product_id and item.specification else None
    employee = db.get(Employee, item.maintainer_id) if item.maintainer_id else None
    data.update(
        project_name=project.name if project else "",
        location_name=location.name if location else "",
        product_name=product.name if product else "",
        product_image_url=product.image_url if product else "",
        variant_image_url=variant.image_url if variant else "",
        unit_price=float(product.monthly_rental_price or product.sale_price or 0) if product else 0,
        maintainer_name=employee.name if employee else "",
    )
    return data


def plant_change_payload(item: ProjectPlantChange, db: Session):
    data = ProjectPlantChangeRead.model_validate(item).model_dump()
    project = db.get(Project, item.project_id)
    location = db.get(ProjectLocation, item.location_id) if item.location_id else None
    product = db.get(Product, item.product_id) if item.product_id else None
    data.update(
        project_name=project.name if project else "",
        location_name=location.name if location else "",
        product_name=product.name if product else "",
    )
    return data


def add_plant_change(
    db: Session,
    plant: ProjectPlant,
    change_type: str,
    quantity_before: float,
    quantity_after: float,
    pot_before: str = "",
    pot_after: str = "",
    source_type: str = "",
    source_no: str = "",
    operator: str = "",
    notes: str = "",
):
    db.add(
        ProjectPlantChange(
            project_id=plant.project_id,
            plant_id=plant.id,
            location_id=plant.location_id,
            product_id=plant.product_id,
            change_type=change_type,
            source_type=source_type,
            source_no=source_no,
            quantity_before=float(quantity_before or 0),
            quantity_after=float(quantity_after or 0),
            quantity_delta=float(quantity_after or 0) - float(quantity_before or 0),
            unit=plant.unit,
            pot_before=pot_before,
            pot_after=pot_after,
            operator=operator,
            notes=notes,
        )
    )


@router.get("/project-plants")
def list_project_plants(project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    filters = [ProjectPlant.project_id == project_id] if project_id else []
    if project_id and not can_access_project(user, project_id, db):
        raise HTTPException(status_code=403, detail="无权查看该项目植物")
    if not project_id:
        project_ids = accessible_project_ids(user, db)
        if project_ids is not None:
            if not project_ids:
                return {"items": [], "total": 0}
            filters.append(ProjectPlant.project_id.in_(project_ids))
    items = db.scalars(select(ProjectPlant).where(*filters).order_by(ProjectPlant.id.desc())).all()
    return {"items": [plant_payload(item, db) for item in items], "total": len(items)}


@router.get("/project-plant-changes")
def list_project_plant_changes(
    project_id: int | None = None,
    plant_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_module(user, "projects")
    filters = []
    if project_id:
        if not can_access_project(user, project_id, db):
            raise HTTPException(status_code=403, detail="无权查看该项目植物流水")
        filters.append(ProjectPlantChange.project_id == project_id)
    if plant_id:
        plant = require(ProjectPlant, plant_id, db, "项目植物不存在")
        if not can_access_project(user, plant.project_id, db):
            raise HTTPException(status_code=403, detail="无权查看该项目植物流水")
        filters.append(ProjectPlantChange.plant_id == plant_id)
    if not project_id and not plant_id:
        project_ids = accessible_project_ids(user, db)
        if project_ids is not None:
            if not project_ids:
                return {"items": [], "total": 0}
            filters.append(ProjectPlantChange.project_id.in_(project_ids))
    items = db.scalars(select(ProjectPlantChange).where(*filters).order_by(ProjectPlantChange.id.desc())).all()
    return {"items": [plant_change_payload(item, db) for item in items], "total": len(items)}


def validate_plant_refs(project_id: int, location_id: int, product_id: int, maintainer_id: int | None, db: Session):
    require(Project, project_id, db, "项目不存在")
    location = require(ProjectLocation, location_id, db, "项目位置不存在")
    if location.project_id != project_id:
        raise HTTPException(status_code=400, detail="项目位置不属于当前项目")
    require(Product, product_id, db, "商品不存在")
    if maintainer_id:
        require(Employee, maintainer_id, db, "养护员不存在")


@router.post("/project-plants", status_code=status.HTTP_201_CREATED)
def create_project_plant(payload: ProjectPlantCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    if not can_access_project(user, payload.project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该项目植物")
    validate_plant_refs(payload.project_id, payload.location_id, payload.product_id, payload.maintainer_id, db)
    project = require(Project, payload.project_id, db, "项目不存在")
    values = payload.model_dump()
    values["source"] = project.plant_source
    item = ProjectPlant(**values)
    db.add(item)
    db.flush()
    add_plant_change(
        db,
        item,
        "手工新增",
        0,
        float(item.quantity or 0),
        "",
        item.decorative_pot,
        "项目植物",
        "",
        user.display_name or user.username,
        "手工录入项目植物清单",
    )
    db.commit()
    db.refresh(item)
    return plant_payload(item, db)


@router.put("/project-plants/{plant_id}")
def update_project_plant(plant_id: int, payload: ProjectPlantUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "projects")
    item = require(ProjectPlant, plant_id, db, "项目植物不存在")
    if not can_access_project(user, item.project_id, db):
        raise HTTPException(status_code=403, detail="无权修改该项目植物")
    values = payload.model_dump(exclude_unset=True)
    validate_plant_refs(
        item.project_id,
        values.get("location_id", item.location_id),
        values.get("product_id", item.product_id),
        values.get("maintainer_id", item.maintainer_id),
        db,
    )
    quantity_before = float(item.quantity or 0)
    pot_before = item.decorative_pot or ""
    for key, value in values.items():
        setattr(item, key, value)
    quantity_after = float(item.quantity or 0)
    pot_after = item.decorative_pot or ""
    changed_fields = "、".join(values.keys())
    add_plant_change(
        db,
        item,
        "手工编辑",
        quantity_before,
        quantity_after,
        pot_before,
        pot_after,
        "项目植物",
        "",
        user.display_name or user.username,
        f"手工修改字段：{changed_fields}" if changed_fields else "手工编辑项目植物",
    )
    db.commit()
    db.refresh(item)
    return plant_payload(item, db)


def salary_payload(item: ProjectSalary, db: Session):
    data = ProjectSalaryRead.model_validate(item).model_dump()
    project = db.get(Project, item.project_id)
    employee = db.get(Employee, item.employee_id)
    data.update(project_name=project.name if project else "", employee_name=employee.name if employee else "")
    return data


@router.get("/project-salaries")
def list_project_salaries(project_id: int | None = None, salary_month: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "finance")
    filters = []
    if project_id:
        filters.append(ProjectSalary.project_id == project_id)
    if salary_month:
        filters.append(ProjectSalary.salary_month == salary_month)
    items = db.scalars(select(ProjectSalary).where(*filters).order_by(ProjectSalary.salary_month.desc(), ProjectSalary.id.desc())).all()
    return {"items": [salary_payload(item, db) for item in items], "total": len(items)}


@router.post("/project-salaries", status_code=status.HTTP_201_CREATED)
def create_project_salary(payload: ProjectSalaryCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "finance")
    require(Project, payload.project_id, db, "项目不存在")
    require(Employee, payload.employee_id, db, "员工不存在")
    duplicate = db.scalar(select(ProjectSalary).where(ProjectSalary.project_id == payload.project_id, ProjectSalary.employee_id == payload.employee_id, ProjectSalary.salary_month == payload.salary_month))
    if duplicate:
        raise HTTPException(status_code=409, detail="该养护员本月项目工资已存在")
    item = ProjectSalary(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return salary_payload(item, db)


@router.put("/project-salaries/{salary_id}")
def update_project_salary(salary_id: int, payload: ProjectSalaryUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_module(user, "finance")
    item = require(ProjectSalary, salary_id, db, "项目工资记录不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return salary_payload(item, db)
