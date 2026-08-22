import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Product, ProductCategory, ProductVariant, User
from ..permissions import has_full_access, product_category_permissions
from ..schemas import ProductCreate, ProductRead, ProductUpdate, ProductVariantCreate, ProductVariantRead, ProductVariantUpdate


router = APIRouter(prefix="/api/v1/products", tags=["products"])

DEFAULT_CATEGORIES = ["植物", "花盆", "农药", "肥料", "工具", "组合盆景", "其他"]


def visible_category_filters(user: User):
    if has_full_access(user):
        return []
    allowed = product_category_permissions(user)
    if not allowed:
        return [Product.id == -1]
    return [Product.category.in_(allowed)]


def can_delete_product(user: User) -> bool:
    roles = {part.strip() for part in (user.role or "").replace("，", ",").split(",") if part.strip()}
    permissions = {part.strip() for part in (user.module_permissions or "").replace("，", ",").split(",") if part.strip()}
    return bool(roles & {"admin", "管理员", "经理", "老板"}) or "system" in permissions


def all_category_names(db: Session, user: User | None = None) -> list[str]:
    names = set(DEFAULT_CATEGORIES)
    names.update(db.scalars(select(Product.category).distinct()).all())
    names.update(db.scalars(select(ProductCategory.name).where(ProductCategory.status == "启用")).all())
    result = sorted({str(item).strip() for item in names if str(item or "").strip()})
    if user and not has_full_access(user):
        allowed = product_category_permissions(user)
        result = [item for item in result if item in allowed]
    return result


def get_product(product_id: int, db: Session) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


def next_product_code(db: Session) -> str:
    prefix = f"SP-{date.today().strftime('%Y%m%d')}"
    codes = db.scalars(select(Product.code).where(Product.code.like(f"{prefix}%"))).all()
    max_no = 0
    for code in codes:
        match = re.fullmatch(rf"{re.escape(prefix)}(\d+)", str(code or ""))
        if match:
            max_no = max(max_no, int(match.group(1)))
    return f"{prefix}{max_no + 1}"


def next_variant_code(product: Product, db: Session) -> str:
    prefix = f"{product.code}-"
    codes = db.scalars(select(ProductVariant.code).where(ProductVariant.product_id == product.id, ProductVariant.code.like(f"{prefix}%"))).all()
    max_no = 0
    for code in codes:
        match = re.fullmatch(rf"{re.escape(prefix)}(\d+)", str(code or ""))
        if match:
            max_no = max(max_no, int(match.group(1)))
    return f"{prefix}{max_no + 1}"


@router.get("/next-code")
def suggest_product_code(
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    return {"code": next_product_code(db)}


@router.get("")
def list_products(
    keyword: str = Query(default="", max_length=100),
    project_category: str = Query(default="", max_length=64),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = visible_category_filters(user)
    if keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(or_(Product.code.like(pattern), Product.name.like(pattern), Product.category.like(pattern)))
    if project_category.strip():
        category = project_category.strip()
        filters.append(or_(Product.project_categories == "", Product.project_categories.is_(None), Product.project_categories.like(f"%{category}%")))
    items = db.scalars(select(Product).where(*filters).order_by(Product.id.desc())).all()
    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    return {"items": [ProductRead.model_validate(item) for item in items], "total": total}


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return {"items": all_category_names(db, user), "total": len(all_category_names(db, user))}


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写分类名称")
    existing = db.scalar(select(ProductCategory).where(ProductCategory.name == name))
    if existing:
        existing.status = "启用"
        db.commit()
        return {"name": existing.name}
    item = ProductCategory(name=name, sort_order=int(payload.get("sort_order") or 100), status="启用")
    db.add(item)
    db.commit()
    return {"name": item.name}


@router.delete("/categories/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    name: str,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    if db.scalar(select(Product.id).where(Product.category == name)):
        raise HTTPException(status_code=409, detail="该分类下已有商品，不能删除")
    item = db.scalar(select(ProductCategory).where(ProductCategory.name == name))
    if item:
        db.delete(item)
        db.commit()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    if db.scalar(select(Product).where(Product.code == payload.code)):
        raise HTTPException(status_code=409, detail="商品编码已存在")
    product = Product(**payload.model_dump())
    db.add(product)
    category_name = (payload.category or "").strip()
    if category_name and not db.scalar(select(ProductCategory).where(ProductCategory.name == category_name)):
        db.add(ProductCategory(name=category_name, status="启用"))
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}/variants/next-code")
def suggest_variant_code(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    product = get_product(product_id, db)
    return {"code": next_variant_code(product, db)}


@router.get("/{product_id}/variants")
def list_variants(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    get_product(product_id, db)
    items = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product_id).order_by(ProductVariant.sort_order, ProductVariant.id)).all()
    return {"items": [ProductVariantRead.model_validate(item) for item in items], "total": len(items)}


@router.post("/{product_id}/variants", response_model=ProductVariantRead, status_code=status.HTTP_201_CREATED)
def create_variant(
    product_id: int,
    payload: ProductVariantCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    get_product(product_id, db)
    if db.scalar(select(ProductVariant).where(ProductVariant.code == payload.code)):
        raise HTTPException(status_code=409, detail="规格编码已存在")
    variant = ProductVariant(product_id=product_id, **payload.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.put("/{product_id}/variants/{variant_id}", response_model=ProductVariantRead)
def update_variant(
    product_id: int,
    variant_id: int,
    payload: ProductVariantUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    variant = db.get(ProductVariant, variant_id)
    if not variant or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="商品规格不存在")
    values = payload.model_dump(exclude_unset=True)
    if "code" in values and db.scalar(select(ProductVariant).where(ProductVariant.code == values["code"], ProductVariant.id != variant_id)):
        raise HTTPException(status_code=409, detail="规格编码已存在")
    for key, value in values.items():
        setattr(variant, key, value)
    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/{product_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    product_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    variant = db.get(ProductVariant, variant_id)
    if not variant or variant.product_id != product_id:
        raise HTTPException(status_code=404, detail="商品规格不存在")
    db.delete(variant)
    db.commit()


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    product = get_product(product_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "code" in values:
        duplicate = db.scalar(select(Product).where(Product.code == values["code"], Product.id != product_id))
        if duplicate:
            raise HTTPException(status_code=409, detail="商品编码已存在")
    for key, value in values.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not can_delete_product(user):
        raise HTTPException(status_code=403, detail="无权删除商品，请联系管理员")
    product = get_product(product_id, db)
    for variant in db.scalars(select(ProductVariant).where(ProductVariant.product_id == product_id)).all():
        db.delete(variant)
    db.delete(product)
    db.commit()
