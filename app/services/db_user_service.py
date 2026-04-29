"""基于数据库的用户服务"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import User
from app.utils.auth import verify_password, get_password_hash


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """通过用户名获取用户"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """通过邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, username: str, password: str, email: Optional[str] = None) -> Optional[User]:
    """创建新用户"""
    # 检查用户是否已存在
    if get_user_by_username(db, username):
        return None

    if email and get_user_by_email(db, email):
        return None

    # 创建新用户
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        disabled=False
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if user.disabled:
        return None
    return user


def update_user_password(db: Session, username: str, new_password: str) -> bool:
    """更新用户密码"""
    user = get_user_by_username(db, username)
    if not user:
        return False

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return True


def disable_user(db: Session, username: str) -> bool:
    """禁用用户"""
    user = get_user_by_username(db, username)
    if not user:
        return False

    user.disabled = True
    db.commit()
    return True


def enable_user(db: Session, username: str) -> bool:
    """启用用户"""
    user = get_user_by_username(db, username)
    if not user:
        return False

    user.disabled = False
    db.commit()
    return True
