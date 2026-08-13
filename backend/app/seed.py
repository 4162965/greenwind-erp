from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import User
from .security import hash_password


def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.username == "admin")):
            db.add(User(username="admin", display_name="系统管理员", password_hash=hash_password("admin123")))
            db.commit()
            print("已创建本地开发账号：admin / admin123")
        else:
            print("开发账号已存在")


if __name__ == "__main__":
    seed()

