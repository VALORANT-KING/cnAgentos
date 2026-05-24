from app.models.db import init_db
from app.models.user import UserRepository

init_db()

print("创建普通用户:", UserRepository.create_user("testuser", "123456", "user"))
print("创建管理员:", UserRepository.create_user("admin", "admin888", "admin"))