from app.models.db import init_db
from app.models.user import UserRepository

init_db()

print("创建管理员账号: admin / admin888")
ok = UserRepository.create_user("admin", "admin888", "admin")
if ok:
    print("管理员创建成功！")
else:
    print("管理员已存在，尝试更新...")
    user = UserRepository.get_user_by_username("admin")
    if user:
        UserRepository.update_user(user['id'], password="admin888", role="admin", status=1)
        print("管理员更新成功！")

print("创建测试用户: testuser / 123456")
UserRepository.create_user("testuser", "123456", "user")
print("初始化完成！")
