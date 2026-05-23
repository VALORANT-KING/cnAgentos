from app.models.db import init_db
from app.models.user import UserRepository

init_db()
print("新增", UserRepository.create_user("admin", "123456"))