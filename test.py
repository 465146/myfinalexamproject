"""测试配置文件是否正确加载"""
from app.core.config import get_settings

settings = get_settings()

print("=" * 50)
print("配置信息")
print("=" * 50)
print(f"DB_HOST: {settings.DB_HOST}")
print(f"DB_PORT: {settings.DB_PORT}")
print(f"DB_USER: {settings.DB_USER}")
print(f"DB_PASSWORD: {settings.DB_PASSWORD}")
print(f"DB_NAME: {settings.DB_NAME}")
print(f"DATABASE_URL: {settings.DATABASE_URL}")
print("=" * 50)

# 测试数据库连接
from app.db.session import engine
try:
    with engine.connect() as conn:
        print("✅ 数据库连接成功！")
except Exception as e:
    print(f"❌ 数据库连接失败: {e}")
