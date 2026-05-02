"""认证工具函数"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings
import time

settings = get_settings()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 内存中的令牌黑名单（生产环境建议使用 Redis）
token_blacklist = {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 检查令牌是否在黑名单中
        if is_token_blacklisted(token):
            return None

        return payload
    except JWTError:
        return None


def blacklist_token(token: str) -> bool:
    """将令牌加入黑名单"""
    try:
        # 解码令牌以获取过期时间
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")

        if exp_timestamp:
            # 计算剩余有效时间
            now = time.time()
            remaining_time = exp_timestamp - now

            if remaining_time > 0:
                # 将令牌加入黑名单，设置过期时间为令牌的剩余有效期
                token_blacklist[token] = time.time() + remaining_time

                # 清理过期的黑名单令牌
                cleanup_expired_tokens()

        return True
    except Exception as e:
        print(f"添加令牌到黑名单失败: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """检查令牌是否在黑名单中"""
    try:
        # 清理过期的黑名单令牌
        cleanup_expired_tokens()

        return token in token_blacklist
    except Exception as e:
        print(f"检查令牌黑名单失败: {e}")
        return False


def cleanup_expired_tokens():
    """清理过期的黑名单令牌"""
    now = time.time()
    expired_tokens = [token for token, expiry in token_blacklist.items() if expiry < now]
    for token in expired_tokens:
        del token_blacklist[token]
