from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .migrations import upgrade_legacy_sqlite
from .routers import attachments, auth, customers, dashboard, employees, finance, inventory, maintenance, orders, products, projects, purchases, reports, schedules, system, workflows


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    upgrade_legacy_sqlite(engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


def cors_origins() -> list[str]:
    origins = {
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.31.154:5173",
        "http://175.178.106.253:5173",
    }
    for item in settings.frontend_origins.split(","):
        item = item.strip()
        if item:
            origins.add(item)
    return sorted(origin for origin in origins if origin)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=settings.frontend_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(attachments.router)
app.include_router(dashboard.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(finance.router)
app.include_router(purchases.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(reports.router)
app.include_router(maintenance.router)
app.include_router(schedules.vehicle_router)
app.include_router(schedules.schedule_router)
app.include_router(system.router)
app.include_router(workflows.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": settings.app_name}
